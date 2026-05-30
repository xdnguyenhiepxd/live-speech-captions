"""Hàng đợi ASR 1 slot — ưu tiên final, không bỏ câu đang chờ."""

import threading


class AsrQueue:
    """
    Một worker, một job chờ. Partial không ghi đè final đang chờ.
    """

    def __init__(self, handler):
        self._handler = handler
        self._lock = threading.Lock()
        self._slot = None
        self._wake = threading.Event()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="asr-worker", daemon=True)
        self._thread.start()

    def submit(self, job):
        with self._lock:
            old = self._slot
            if old is None:
                self._slot = job
            else:
                old_kind = old.get("kind")
                new_kind = job.get("kind")
                if old_kind == "final" and new_kind == "partial":
                    return
                if job.get("log_drop") and old_kind != new_kind:
                    print(
                        f"[ASR] Thay {old_kind} chunk={old.get('chunk_id')} "
                        f"→ {new_kind} chunk={job.get('chunk_id')}"
                    )
                self._slot = job
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
