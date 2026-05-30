"""Hàng đợi ASR tối đa 1 job — job mới thay job cũ (giảm queue 1s+)."""

import queue
import threading
import time


class AsrQueue:
    """
    Một worker, một slot. Submit khi đang bận → ghi đè job cũ (ưu tiên final).
    """

    PRIORITY = {"partial": 0, "final": 1}

    def __init__(self, handler):
        self._handler = handler
        self._lock = threading.Lock()
        self._slot = None
        self._wake = threading.Event()
        self._dropped = 0
        self._running = True
        self._thread = threading.Thread(target=self._run, name="asr-worker", daemon=True)
        self._thread.start()

    def submit(self, job):
        """job: dict kind, audio, chunk_id, prompt, t_captured."""
        with self._lock:
            old = self._slot
            if old is None:
                self._slot = job
            else:
                old_p = self.PRIORITY.get(old.get("kind"), 0)
                new_p = self.PRIORITY.get(job.get("kind"), 0)
                if new_p >= old_p:
                    self._slot = job
                    self._dropped += 1
                    if job.get("log_drop"):
                        print(
                            f"[ASR] Bỏ job {old.get('kind')} chunk={old.get('chunk_id')} "
                            f"(thay bằng {job.get('kind')} — tránh queue)"
                        )
                else:
                    self._dropped += 1
        self._wake.set()

    def _run(self):
        while self._running:
            self._wake.wait(timeout=0.25)
            self._wake.clear()
            while True:
                with self._lock:
                    job = self._slot
                    self._slot = None
                if job is None:
                    break
                try:
                    self._handler(job)
                except Exception as e:
                    print(f"[ASR] Lỗi worker: {e}")

    def stop(self):
        self._running = False
        self._wake.set()
        self._thread.join(timeout=2)
