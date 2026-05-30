import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import signal
import threading
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from audio_capture import AudioCapture
from transcriber import Transcriber
from config import config
from asr_queue import AsrQueue

class WorkerSignals(QObject):
    update_text = pyqtSignal(int, str, str)

class Pipeline(QObject):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.running = True
        self.last_final_text = ""
        self._chunk_buffers = []
        self._stream_transcriber = None
        self._stream_chunk_id = 1

        config.print_config()

        self.audio = AudioCapture(
            device_index=config.device_index,
            sample_rate=config.sample_rate,
            silence_threshold=config.silence_threshold,
            silence_duration=config.silence_duration,
            chunk_duration=config.chunk_duration,
            max_phrase_duration=config.max_phrase_duration,
            streaming_mode=config.streaming_mode,
            streaming_interval=config.streaming_interval,
            streaming_step_size=config.streaming_step_size,
            streaming_overlap=config.streaming_overlap,
        )

        if config.asr_backend == "funasr":
            raise ValueError("backend=funasr không còn hỗ trợ.")

        import platform
        if platform.system() == "Darwin" and platform.machine() != "arm64":
            if config.asr_backend == "mlx":
                raise ValueError(
                    "Mac Intel: cp config/mac-cpu.ini.example config.ini"
                )

        self._use_streaming = config.is_streaming_asr()
        self.partial_updates = config.reader_partial_updates
        self.min_phrase_duration = config.min_phrase_duration
        self.standard_cut_duration = config.standard_cut_duration
        self.soft_cut_at_duration = config.soft_cut_at_duration
        self.update_interval = config.reader_update_interval
        self.partial_window_seconds = config.partial_window_seconds
        self._apply_realtime_tuning()

        if self._use_streaming:
            self.transcriber = self._create_streaming_transcriber()
            self._asr_queue = None
            print("[Pipeline] Chế độ REALTIME — Deepgram WebSocket streaming")
        else:
            self.transcriber = self._create_transcriber()
            if config.is_batch_cloud_asr() and not config.cloud_partial:
                self.partial_updates = False
                print("[Pipeline] Cloud batch: tắt partial (tiết kiệm API)")
            self._cloud_asr_lock = threading.Lock()
            self._last_cloud_asr_end = 0.0
            if config.is_batch_cloud_asr():
                interval = config.cloud_min_request_interval
                print(
                    f"[Pipeline] Cloud batch: chờ tối thiểu {interval:.0f}s giữa các lần gọi API"
                )
            self._asr_queue = AsrQueue(self._handle_asr_job)
            self.transcriber.warmup()
            print("[Pipeline] ASR queue: 1 slot (job mới thay job cũ)")

        print(
            f"[Pipeline] ASR={config.asr_backend} | "
            f"max_audio={config.max_transcribe_seconds}s"
        )

    def _apply_realtime_tuning(self):
        if not config.realtime_mode:
            return
        if not self._use_streaming:
            self.partial_updates = True
            self.update_interval = min(self.update_interval, 0.55)
            self.standard_cut_duration = min(self.standard_cut_duration, 0.75)
            self.min_phrase_duration = min(self.min_phrase_duration, 0.45)
            self.soft_cut_at_duration = min(self.soft_cut_at_duration, 3.5)
            if config.asr_backend == "openai":
                self.partial_updates = config.cloud_partial or True
            elif config.asr_backend == "gemini":
                self.partial_updates = False
        print("[Pipeline] Realtime: cắt câu ngắn + partial (trừ Gemini batch)")

    def _create_streaming_transcriber(self):
        from streaming_asr import create_streaming_transcriber

        lang = config.deepgram_language
        if config.source_language and config.source_language != "auto":
            lang = config.source_language

        return create_streaming_transcriber(
            backend="deepgram",
            on_transcript=self._on_stream_transcript,
            api_key=config.deepgram_api_key,
            sample_rate=config.sample_rate,
            model=config.deepgram_model,
            language=lang,
            log_latency=config.log_latency,
        )

    def _on_stream_transcript(self, text: str, is_final: bool):
        if not text:
            return
        t_cap = time.perf_counter()
        cid = self._stream_chunk_id
        if is_final:
            self.last_final_text = text
            self._stream_chunk_id += 1
        self._emit_text(cid, text, t_cap, "final" if is_final else "partial")

    def _create_transcriber(self):
        if config.is_batch_cloud_asr():
            from cloud_asr import create_cloud_transcriber

            provider = config.asr_backend
            api_key = (
                config.openai_api_key
                if provider == "openai"
                else config.gemini_api_key
            )
            return create_cloud_transcriber(
                provider=provider,
                api_key=api_key,
                language=config.source_language,
                openai_base_url=config.openai_base_url,
                openai_model=config.openai_stt_model,
                gemini_model=config.gemini_model,
                max_transcribe_seconds=config.max_transcribe_seconds,
                log_latency=config.log_latency,
                sample_rate=config.sample_rate,
                use_context_prompt=config.use_context_prompt,
            )

        print(
            f"[Pipeline] Local model={config.whisper_model} "
            f"device={config.whisper_device}"
        )
        return Transcriber(
            backend=config.asr_backend,
            model_size=config.whisper_model,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
            language=config.source_language,
            beam_size=config.whisper_beam_size,
            cpu_threads=config.cpu_threads,
            vad_filter=config.vad_filter,
            max_transcribe_seconds=config.max_transcribe_seconds,
            log_latency=config.log_latency,
            sample_rate=config.sample_rate,
            use_context_prompt=config.use_context_prompt,
        )

    def start(self):
        if self._use_streaming:
            self.transcriber.start()
        target = (
            self._streaming_audio_loop
            if self._use_streaming
            else self.processing_loop
        )
        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()

    def stop(self):
        print("\n[Pipeline] Stopping...")
        self.running = False
        self.audio.stop()
        if self._use_streaming and self.transcriber:
            self.transcriber.stop()
        if self._asr_queue:
            self._asr_queue.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=2)
        print("[Pipeline] Stopped.")

    def _submit_asr(self, kind, audio_data, chunk_id, prompt, t_captured):
        self._asr_queue.submit({
            "kind": kind,
            "audio": audio_data,
            "chunk_id": chunk_id,
            "prompt": prompt if config.use_context_prompt else None,
            "t_captured": t_captured,
            "log_drop": config.log_latency,
        })

    def _wait_cloud_rate_limit(self):
        if not config.is_batch_cloud_asr():
            return
        interval = max(1.0, config.cloud_min_request_interval)
        with self._cloud_asr_lock:
            elapsed = time.perf_counter() - self._last_cloud_asr_end
            if elapsed < interval:
                wait = interval - elapsed
                print(f"[CloudASR] Chờ {wait:.0f}s (giới hạn RPM free tier)…")
                time.sleep(wait)

    def _mark_cloud_request_done(self):
        if config.is_batch_cloud_asr():
            with self._cloud_asr_lock:
                self._last_cloud_asr_end = time.perf_counter()

    def _handle_asr_job(self, job):
        kind = job["kind"]
        chunk_id = job["chunk_id"]
        t_captured = job["t_captured"]
        prompt = job.get("prompt")
        if kind == "final" and config.use_context_prompt:
            prompt = self.last_final_text

        self._wait_cloud_rate_limit()
        meta = {
            "chunk_id": chunk_id,
            "kind": kind,
            "t_captured": t_captured,
            "sample_rate": self.audio.sample_rate,
        }
        try:
            text = self.transcriber.transcribe(
                job["audio"], prompt=prompt, latency_meta=meta
            )
        finally:
            self._mark_cloud_request_done()
        if text:
            if kind == "final" and len(text.split()) > 2:
                self.last_final_text = text
            self._emit_text(chunk_id, text, t_captured, kind)

    def _emit_text(self, chunk_id, text, t_captured, kind):
        t_emit = time.perf_counter()
        self.signals.update_text.emit(chunk_id, text, "")
        if config.log_latency and t_captured is not None:
            e2e_ms = (t_emit - t_captured) * 1000
            print(
                f"[LATENCY] {kind} chunk={chunk_id} | E2E={e2e_ms:.0f}ms "
                f"(âm thanh → màn hình)"
            )

    def _streaming_audio_loop(self):
        print("[Pipeline] Streaming audio → Deepgram…")
        audio_gen = self.audio.generator()
        try:
            for audio_chunk in audio_gen:
                if not self.running:
                    break
                self.transcriber.send_audio(audio_chunk)
        except Exception as e:
            print(f"[Pipeline] Streaming error: {e}")
            import traceback
            traceback.print_exc()

    def processing_loop(self):
        import numpy as np

        print("[Pipeline] processing loop started.")
        chunk_id = 1
        last_update_time = time.time()
        sr = self.audio.sample_rate
        audio_gen = self.audio.generator()

        try:
            for audio_chunk in audio_gen:
                if not self.running:
                    break
                self._chunk_buffers.append(audio_chunk)
                buffer = np.concatenate(self._chunk_buffers)
                now = time.time()
                buffer_duration = len(buffer) / sr

                is_silence = False
                if buffer_duration > config.silence_duration:
                    tail = buffer[-int(sr * config.silence_duration):]
                    if np.sqrt(np.mean(tail**2)) < self.audio.silence_threshold:
                        is_silence = True

                standard_cut = is_silence and buffer_duration >= self.standard_cut_duration
                soft_limit_cut = False
                if buffer_duration >= self.soft_cut_at_duration:
                    st = int(sr * 0.3)
                    if len(buffer) > st:
                        if np.sqrt(np.mean(buffer[-st:]**2)) < self.audio.silence_threshold:
                            soft_limit_cut = True

                hard_limit_cut = buffer_duration > self.audio.max_phrase_duration
                should_finalize = standard_cut or soft_limit_cut or hard_limit_cut

                if should_finalize and buffer_duration >= self.min_phrase_duration:
                    if np.sqrt(np.mean(buffer**2)) >= self.audio.silence_threshold:
                        t_cap = time.perf_counter()
                        if config.log_latency:
                            print(
                                f"[AUDIO] chunk={chunk_id} final | {buffer_duration:.2f}s → ASR"
                            )
                        self._submit_asr(
                            "final", buffer.copy(), chunk_id, self.last_final_text, t_cap
                        )
                    self._chunk_buffers = []
                    chunk_id += 1
                    last_update_time = now

                elif (
                    self.partial_updates
                    and now - last_update_time > self.update_interval
                    and buffer_duration >= self.min_phrase_duration
                ):
                    tail_samps = int(sr * self.partial_window_seconds)
                    partial = buffer[-tail_samps:].copy() if len(buffer) > tail_samps else buffer.copy()
                    if np.sqrt(np.mean(partial**2)) > self.audio.silence_threshold:
                        t_cap = time.perf_counter()
                        self._submit_asr(
                            "partial", partial, chunk_id, self.last_final_text, t_cap
                        )
                    last_update_time = now

        except Exception as e:
            print(f"[Pipeline] Error in loop: {e}")
            import traceback
            traceback.print_exc()


_pipeline = None
_app = None


def signal_handler(sig, frame):
    print("\n[Main] Ctrl-C received, force killing...")
    os._exit(0)


def start_reader_session():
    global _pipeline, _app
    from large_text_window import LargeTextOverlayWindow

    window = LargeTextOverlayWindow(
        window_width=config.reader_window_width,
        font_size=config.reader_font_size,
        keep_lines=config.reader_keep_lines,
    )
    window.show()
    _pipeline = Pipeline()
    _pipeline.signals.update_text.connect(window.update_text)
    _pipeline.start()
    return window, _pipeline


def main():
    global _pipeline, _app

    signal.signal(signal.SIGINT, signal_handler)
    _app = QApplication.instance() or QApplication(sys.argv)
    win, pipe = start_reader_session()

    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    try:
        sys.exit(_app.exec())
    except SystemExit:
        pass
    finally:
        if _pipeline:
            _pipeline.stop()


if __name__ == "__main__":
    main()
