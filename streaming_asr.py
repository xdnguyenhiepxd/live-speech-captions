"""
Realtime streaming ASR (WebSocket) — Deepgram live API.
"""

from __future__ import annotations

import queue
import threading
import time

import numpy as np


def float32_to_linear16_bytes(audio: np.ndarray) -> bytes:
    audio = np.asarray(audio, dtype=np.float32).flatten()
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    return pcm.tobytes()


class DeepgramStreamASR:
    """Gửi audio liên tục qua WebSocket; nhận partial + final transcript."""

    def __init__(
        self,
        api_key: str,
        on_transcript,
        sample_rate: int = 16000,
        model: str = "nova-3",
        language: str = "en",
        log_latency: bool = True,
    ):
        self.api_key = (api_key or "").strip()
        self.on_transcript = on_transcript
        self.sample_rate = sample_rate
        self.model = model
        self.language = language or "en"
        self.log_latency = log_latency
        self._audio_q: queue.Queue[bytes | None] = queue.Queue(maxsize=200)
        self._thread = None
        self._running = False

    def start(self):
        if not self.api_key:
            raise ValueError("Thiếu deepgram_api_key (tab Cloud API hoặc DEEPGRAM_API_KEY)")
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(
            f"[Deepgram] Streaming | model={self.model} | lang={self.language} | "
            f"{self.sample_rate} Hz"
        )

    def stop(self):
        self._running = False
        try:
            self._audio_q.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None

    def send_audio(self, audio_chunk):
        if not self._running:
            return
        data = float32_to_linear16_bytes(audio_chunk)
        try:
            self._audio_q.put_nowait(data)
        except queue.Full:
            try:
                self._audio_q.get_nowait()
            except queue.Empty:
                pass
            self._audio_q.put_nowait(data)

    def _run(self):
        try:
            from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
        except ImportError as e:
            print("[Deepgram] Cần: pip install 'deepgram-sdk>=3.5,<4'")
            self._running = False
            raise ImportError("pip install 'deepgram-sdk>=3.5,<4'") from e

        client = DeepgramClient(self.api_key)
        connection = client.listen.live.v("1")

        def on_transcript_handler(_self, result, **kwargs):
            try:
                alt = result.channel.alternatives[0]
                text = (alt.transcript or "").strip()
                if not text:
                    return
                is_final = bool(getattr(result, "is_final", False))
                if self.log_latency:
                    tag = "final" if is_final else "partial"
                    print(f'[Deepgram] {tag}: {text[:60]}{"…" if len(text) > 60 else ""}')
                self.on_transcript(text, is_final)
            except Exception as e:
                print(f"[Deepgram] Parse transcript: {e}")

        def on_error(_self, error, **kwargs):
            print(f"[Deepgram] Lỗi: {error}")

        connection.on(LiveTranscriptionEvents.Transcript, on_transcript_handler)
        connection.on(LiveTranscriptionEvents.Error, on_error)

        options = LiveOptions(
            model=self.model,
            language=self.language,
            encoding="linear16",
            sample_rate=self.sample_rate,
            channels=1,
            interim_results=True,
            punctuate=True,
            smart_format=True,
            endpointing=280,
            utterance_end_ms=900,
        )

        if not connection.start(options):
            print("[Deepgram] Không mở được WebSocket")
            self._running = False
            return

        try:
            while self._running:
                try:
                    item = self._audio_q.get(timeout=0.15)
                except queue.Empty:
                    continue
                if item is None:
                    break
                connection.send(item)
        finally:
            try:
                connection.finish()
            except Exception:
                pass
            print("[Deepgram] Streaming đã dừng")

    def warmup(self):
        print("[Deepgram] Streaming sẵn sàng (không warmup).")


def create_streaming_transcriber(backend: str, on_transcript, **kwargs):
    if backend == "deepgram":
        return DeepgramStreamASR(on_transcript=on_transcript, **kwargs)
    raise ValueError(f"Streaming ASR chưa hỗ trợ: {backend}")


def test_deepgram_connection(api_key: str, model: str = "nova-3") -> tuple[bool, str]:
    """Mở WebSocket rồi đóng — kiểm tra key + model."""
    key = (api_key or "").strip()
    if not key:
        return False, "Thiếu Deepgram API key"
    try:
        from deepgram import DeepgramClient, LiveOptions
    except ImportError:
        return False, "Cần: pip install 'deepgram-sdk>=3.5,<4'"
    try:
        client = DeepgramClient(key)
        connection = client.listen.live.v("1")
        options = LiveOptions(
            model=model or "nova-3",
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            interim_results=True,
        )
        if connection.start(options):
            connection.finish()
            return True, f"Deepgram OK — model={model}, sẵn sàng streaming realtime."
        return False, "Không mở được WebSocket (kiểm tra key hoặc model)."
    except Exception as e:
        return False, str(e)
