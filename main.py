import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from audio_capture import AudioCapture
from transcriber import Transcriber
from config import config

class WorkerSignals(QObject):
    update_text = pyqtSignal(int, str, str)  # (chunk_id, original, unused)

class Pipeline(QObject):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.running = True

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
            raise ValueError(
                "backend=funasr không còn hỗ trợ. Đặt backend = mlx (M-chip) hoặc whisper (Intel)."
            )

        import platform
        if platform.system() == "Darwin" and platform.machine() != "arm64":
            if config.asr_backend == "mlx":
                raise ValueError(
                    "Mac Intel không hỗ trợ backend=mlx. "
                    "cp config/mac/macbook-air-intel.ini.example config.ini"
                )
            if config.whisper_device in ("mps", "auto"):
                print("[Pipeline] Mac Intel → dùng device=cpu trong config.ini")

        print(
            f"[Pipeline] ASR backend={config.asr_backend}, model={config.whisper_model}, "
            f"lang={config.source_language}"
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
        )

        self.partial_updates = config.reader_partial_updates
        self.min_phrase_duration = config.min_phrase_duration
        self.standard_cut_duration = config.standard_cut_duration
        self.soft_cut_at_duration = config.soft_cut_at_duration
        self.update_interval = config.reader_update_interval
        self.partial_window_seconds = config.partial_window_seconds
        self._asr_busy = False
        self._pending_partial = None
        print(
            f"[Pipeline] partial={self.partial_updates}, interval={self.update_interval}s, "
            f"window={self.partial_window_seconds}s"
        )

        self.transcriber.warmup()

    def start(self):
        self.thread = threading.Thread(target=self.processing_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        print("\n[Pipeline] Stopping...")
        self.running = False
        self.audio.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=2)
        print("[Pipeline] Stopped.")

    def processing_loop(self):
        import numpy as np

        print("[Pipeline] processing loop started.")
        is_mlx = config.asr_backend == "mlx"
        num_workers = 1 if is_mlx else config.transcription_workers

        transcribe_executor = ThreadPoolExecutor(max_workers=1)
        self._transcribe_executor = transcribe_executor

        buffer = np.array([], dtype=np.float32)
        chunk_id = 1
        last_update_time = time.time()
        self.last_final_text = ""
        audio_gen = self.audio.generator()

        try:
            for audio_chunk in audio_gen:
                if not self.running:
                    break
                buffer = np.concatenate([buffer, audio_chunk])
                now = time.time()
                buffer_duration = len(buffer) / self.audio.sample_rate

                is_silence = False
                min_silence_dur = config.silence_duration
                if buffer_duration > min_silence_dur:
                    tail = buffer[-int(self.audio.sample_rate * min_silence_dur):]
                    rms = np.sqrt(np.mean(tail**2))
                    if rms < self.audio.silence_threshold:
                        is_silence = True

                standard_cut = is_silence and buffer_duration >= self.standard_cut_duration
                soft_limit_cut = False
                if buffer_duration >= self.soft_cut_at_duration:
                    short_tail_samps = int(self.audio.sample_rate * 0.4)
                    if len(buffer) > short_tail_samps:
                        t_rms = np.sqrt(np.mean(buffer[-short_tail_samps:]**2))
                        if t_rms < self.audio.silence_threshold:
                            soft_limit_cut = True

                hard_limit_cut = buffer_duration > self.audio.max_phrase_duration
                should_finalize = standard_cut or soft_limit_cut or hard_limit_cut

                if should_finalize and buffer_duration >= self.min_phrase_duration:
                    final_buffer = buffer.copy()
                    cid = chunk_id
                    prompt = self.last_final_text
                    overall_rms = np.sqrt(np.mean(final_buffer**2))
                    if overall_rms >= self.audio.silence_threshold:
                        t_cap = time.perf_counter()
                        dur = len(final_buffer) / self.audio.sample_rate
                        if config.log_latency:
                            print(
                                f"[AUDIO] chunk={cid} final | {dur:.2f}s audio | "
                                f"→ gửi ASR @ {time.strftime('%H:%M:%S')}"
                            )
                        transcribe_executor.submit(
                            self._process_final_chunk, final_buffer, cid, prompt, t_cap
                        )
                    buffer = np.array([], dtype=np.float32)
                    chunk_id += 1
                    last_update_time = now

                elif (
                    self.partial_updates
                    and now - last_update_time > self.update_interval
                    and buffer_duration >= self.min_phrase_duration
                ):
                    tail_samps = int(self.audio.sample_rate * self.partial_window_seconds)
                    partial_buffer = (
                        buffer[-tail_samps:].copy() if len(buffer) > tail_samps else buffer.copy()
                    )
                    prompt = self.last_final_text
                    rms = np.sqrt(np.mean(partial_buffer**2))
                    if rms > self.audio.silence_threshold:
                        if self._asr_busy:
                            self._pending_partial = (
                                partial_buffer.copy(),
                                chunk_id,
                                prompt,
                                t_cap,
                            )
                        else:
                            t_cap = time.perf_counter()
                            if config.log_latency:
                                pdur = len(partial_buffer) / self.audio.sample_rate
                                print(
                                    f"[AUDIO] chunk={chunk_id} partial | {pdur:.2f}s | → ASR"
                                )
                            transcribe_executor.submit(
                                self._process_partial_chunk,
                                partial_buffer,
                                chunk_id,
                                prompt,
                                t_cap,
                            )
                    last_update_time = now

        except Exception as e:
            print(f"[Pipeline] Error in loop: {e}")
        finally:
            transcribe_executor.shutdown(wait=False)

    def _latency_meta(self, chunk_id, kind, t_captured):
        return {
            "chunk_id": chunk_id,
            "kind": kind,
            "t_captured": t_captured,
            "sample_rate": self.audio.sample_rate,
        }

    def _emit_text(self, chunk_id, text, t_captured, kind):
        t_emit = time.perf_counter()
        self.signals.update_text.emit(chunk_id, text, "")
        if config.log_latency and t_captured is not None:
            e2e_ms = (t_emit - t_captured) * 1000
            print(
                f"[LATENCY] {kind} chunk={chunk_id} | E2E={e2e_ms:.0f}ms "
                f"(âm thanh → chữ trên màn hình)"
            )

    def _process_partial_chunk(self, audio_data, chunk_id, prompt="", t_captured=None):
        self._asr_busy = True
        try:
            meta = self._latency_meta(chunk_id, "partial", t_captured)
            text = self.transcriber.transcribe(audio_data, prompt=prompt, latency_meta=meta)
            if text:
                self._emit_text(chunk_id, text, t_captured, "partial")
        except Exception as e:
            print(f"[Partial {chunk_id}] Error: {e}")
        finally:
            self._asr_busy = False
            self._flush_pending_partial()

    def _flush_pending_partial(self):
        executor = getattr(self, "_transcribe_executor", None)
        if not executor:
            return
        pending = self._pending_partial
        if pending and not self._asr_busy:
            self._pending_partial = None
            buf, cid, prompt, t_cap = pending
            executor.submit(self._process_partial_chunk, buf, cid, prompt, t_cap)

    def _process_final_chunk(self, audio_data, chunk_id, prompt="", t_captured=None):
        self._asr_busy = True
        try:
            meta = self._latency_meta(chunk_id, "final", t_captured)
            text = self.transcriber.transcribe(audio_data, prompt=prompt, latency_meta=meta)
            if text:
                if len(text.split()) > 2:
                    self.last_final_text = text
                self._emit_text(chunk_id, text, t_captured, "final")
        except Exception as e:
            print(f"[Final {chunk_id}] Error: {e}")
        finally:
            self._asr_busy = False
            self._flush_pending_partial()


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
