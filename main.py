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
                    "Mac Intel: cp config/mac/macbook-air-intel.ini.example config.ini"
                )

        print(
            f"[Pipeline] ASR={config.asr_backend} model={config.whisper_model} "
            f"max_audio={config.max_transcribe_seconds}s"
        )
        self.transcriber = Transcriber(
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

        self.partial_updates = config.reader_partial_updates
        self.min_phrase_duration = config.min_phrase_duration
        self.standard_cut_duration = config.standard_cut_duration
        self.soft_cut_at_duration = config.soft_cut_at_duration
        self.update_interval = config.reader_update_interval
        self.partial_window_seconds = config.partial_window_seconds

        self._asr_queue = AsrQueue(self._handle_asr_job)
        self.transcriber.warmup()
        print("[Pipeline] ASR queue: 1 slot (job mới thay job cũ — không xếp hàng dài)")

    def start(self):
        self.thread = threading.Thread(target=self.processing_loop, daemon=True)
        self.thread.start()

    def stop(self):
        print("\n[Pipeline] Stopping...")
        self.running = False
        self.audio.stop()
        if hasattr(self, "_asr_queue"):
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

    def _handle_asr_job(self, job):
        kind = job["kind"]
        chunk_id = job["chunk_id"]
        t_captured = job["t_captured"]
        prompt = job.get("prompt")
        if kind == "final" and config.use_context_prompt:
            prompt = self.last_final_text
        meta = {
            "chunk_id": chunk_id,
            "kind": kind,
            "t_captured": t_captured,
            "sample_rate": self.audio.sample_rate,
        }
        text = self.transcriber.transcribe(job["audio"], prompt=prompt, latency_meta=meta)
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
