"""
Cloud speech-to-text (OpenAI / Gemini) when local Whisper is too slow.

Same interface as Transcriber: transcribe(), warmup().
"""

from __future__ import annotations

import io
import re
import time
import wave

import numpy as np


def _is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _parse_retry_seconds(exc: BaseException) -> float:
    msg = str(exc)
    for pattern in (
        r"retry in (\d+(?:\.\d+)?)s",
        r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)",
    ):
        m = re.search(pattern, msg, re.I)
        if m:
            return float(m.group(1))
    return 26.0


def float32_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    audio = np.asarray(audio, dtype=np.float32).flatten()
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


class CloudTranscriber:
    def __init__(
        self,
        provider: str,
        api_key: str,
        language=None,
        openai_base_url=None,
        openai_model="gpt-4o-mini-transcribe",
        gemini_model="gemini-2.5-flash",
        max_transcribe_seconds=25.0,
        log_latency=True,
        sample_rate=16000,
        use_context_prompt=False,
    ):
        self.provider = provider.lower()
        self.api_key = (api_key or "").strip()
        self.language = language
        self.openai_base_url = (openai_base_url or "").strip() or None
        self.openai_model = openai_model
        self.gemini_model = gemini_model
        self.max_transcribe_seconds = max(1.0, float(max_transcribe_seconds))
        self.log_latency = log_latency
        self.sample_rate = sample_rate
        self.use_context_prompt = use_context_prompt

        if not self.api_key:
            raise ValueError(
                f"Thiếu API key cho {self.provider}. "
                f"Điền trong tab «Cloud API» hoặc biến môi trường."
            )

        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "gemini":
            self._init_gemini()
        else:
            raise ValueError(f"Cloud provider không hỗ trợ: {provider}")

        print(
            f"[CloudASR] {self.provider} | model={self._model_label()} | "
            f"lang={self.language or 'auto'}"
        )

    def _model_label(self):
        if self.provider == "openai":
            return self.openai_model
        return self.gemini_model

    def _init_openai(self):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Cần gói openai: pip install openai") from e
        kwargs = {"api_key": self.api_key}
        if self.openai_base_url:
            kwargs["base_url"] = self.openai_base_url
        self._openai = OpenAI(**kwargs)

    def _init_gemini(self):
        try:
            from google import genai
        except ImportError as e:
            raise ImportError("Cần gói google-genai: pip install google-genai") from e
        self._gemini = genai.Client(api_key=self.api_key)

    def warmup(self):
        print(f"[CloudASR] Sẵn sàng ({self.provider}) — không warmup (tiết kiệm API).")

    def transcribe(self, audio_data, prompt=None, latency_meta=None):
        audio = np.asarray(audio_data, dtype=np.float32)
        sr = self.sample_rate
        if latency_meta and "sample_rate" in latency_meta:
            sr = latency_meta["sample_rate"]

        kind = (latency_meta or {}).get("kind", "final")
        max_sec = self.max_transcribe_seconds
        if kind == "partial":
            max_sec = min(max_sec, 8.0)
        max_samples = int(max_sec * sr)
        if len(audio) > max_samples:
            audio = audio[-max_samples:]

        if len(audio) < int(0.3 * sr):
            return ""

        t0 = time.perf_counter()
        text = ""
        last_err = None
        for attempt in range(2):
            try:
                if self.provider == "openai":
                    text = self._transcribe_openai(audio, sr, prompt)
                else:
                    text = self._transcribe_gemini(audio, sr, prompt)
                last_err = None
                break
            except Exception as e:
                last_err = e
                if attempt == 0 and _is_rate_limit_error(e):
                    delay = _parse_retry_seconds(e)
                    print(
                        f"[CloudASR] 429 hết RPM — chờ {delay:.0f}s rồi thử lại "
                        f"(free tier ~5 req/phút với gemini-2.5-flash)"
                    )
                    time.sleep(min(delay + 0.5, 90.0))
                    continue
                print(f"[CloudASR] Lỗi {self.provider}: {e}")
                return ""
        if last_err:
            return ""

        asr_ms = (time.perf_counter() - t0) * 1000
        if self.log_latency or latency_meta:
            audio_s = len(audio) / sr
            parts = [f"audio={audio_s:.2f}s", f"asr={asr_ms:.0f}ms", f"cloud={self.provider}"]
            if latency_meta:
                t_cap = latency_meta.get("t_captured")
                if t_cap is not None:
                    parts.append(f"queue={(t0 - t_cap) * 1000:.0f}ms")
            snippet = (text or "")[:50]
            parts.append(f'text="{snippet}{"…" if text and len(text) > 50 else ""}"')
            cid = latency_meta.get("chunk_id", "?") if latency_meta else "?"
            label = latency_meta.get("kind", "asr") if latency_meta else "asr"
            print(f"[LATENCY] {label} chunk={cid} | " + " | ".join(parts))

        return (text or "").strip()

    def _transcribe_openai(self, audio: np.ndarray, sample_rate: int, prompt=None):
        wav = float32_to_wav_bytes(audio, sample_rate)
        buf = io.BytesIO(wav)
        buf.name = "audio.wav"

        kwargs = {"model": self.openai_model, "file": buf}
        if self.language:
            kwargs["language"] = self.language
        if prompt and self.use_context_prompt:
            kwargs["prompt"] = prompt[:200]

        result = self._openai.audio.transcriptions.create(**kwargs)
        return getattr(result, "text", None) or str(result)

    def _extract_gemini_text(self, response) -> str:
        """Parse Gemini response; some replies have content.parts=None (blocked/empty)."""
        try:
            text = response.text
            if text:
                return str(text).strip()
        except (AttributeError, TypeError, ValueError):
            pass

        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None)
            if not parts:
                continue
            chunk = "".join(
                (getattr(p, "text", None) or "")
                for p in parts
                if getattr(p, "text", None)
            )
            if chunk.strip():
                return chunk.strip()

        feedback = getattr(response, "prompt_feedback", None)
        if feedback:
            block = getattr(feedback, "block_reason", None)
            if block:
                print(f"[CloudASR] Gemini blocked: {block}")
        return ""

    def _transcribe_gemini(self, audio: np.ndarray, sample_rate: int, prompt=None):
        from google.genai import types

        wav = float32_to_wav_bytes(audio, sample_rate)
        lang_hint = self.language or "the same language as spoken"
        instruction = (
            f"Transcribe all speech in this audio. "
            f"Output only the transcript in {lang_hint}, no labels or markdown."
        )
        if prompt and self.use_context_prompt:
            instruction += f" Previous line for context: {prompt[:200]}"

        response = self._gemini.models.generate_content(
            model=self.gemini_model,
            contents=[
                types.Part.from_bytes(data=wav, mime_type="audio/wav"),
                instruction,
            ],
        )
        return self._extract_gemini_text(response)


def create_cloud_transcriber(provider: str, **kwargs) -> CloudTranscriber:
    return CloudTranscriber(provider=provider, **kwargs)


def test_cloud_connection(
    provider: str,
    api_key: str,
    openai_base_url=None,
    openai_model=None,
    gemini_model=None,
) -> tuple[bool, str]:
    """Quick connectivity check. Returns (ok, message)."""
    try:
        t = create_cloud_transcriber(
            provider=provider,
            api_key=api_key,
            language="en",
            openai_base_url=openai_base_url,
            openai_model=openai_model or "gpt-4o-mini-transcribe",
            gemini_model=gemini_model or "gemini-2.5-flash",
            max_transcribe_seconds=1.0,
            log_latency=False,
        )
        out = t.transcribe(np.zeros(8000, dtype=np.float32))
        return True, f"Kết nối OK ({provider}). Phản hồi: {out!r}"
    except Exception as e:
        return False, str(e)
