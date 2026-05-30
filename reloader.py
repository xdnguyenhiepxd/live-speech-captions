import sys
import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RestartHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_reload = time.time()

    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Chỉ reload khi sửa code .py — KHÔNG theo dõi config.ini (Lưu/API key sẽ kill app)
        if event.src_path.endswith('.py'):
            # Debounce: avoid double restarts for single save
            if time.time() - self.last_reload > 1.0:
                print(f"\n[Reloader] Phát hiện thay đổi: {event.src_path}")
                self.callback()
                self.last_reload = time.time()

def run_app():
    # Run main.py as a subprocess
    return subprocess.Popen([sys.executable, "launcher.py"])

def main():
    print("[Reloader] Đang theo dõi thay đổi (hot reload)...")
    
    # Try to import watchdog, if not present, warn user
    try:
        import watchdog
    except ImportError:
        print("[Reloader] Lỗi: chưa cài thư viện watchdog.")
        print("Chạy: pip install watchdog")
        return

    process = run_app()
    
    def restart_process():
        nonlocal process
        print("[Reloader] Đang khởi động lại ứng dụng...")
        if process:
            # Graceful termination first
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        
        process = run_app()

    event_handler = RestartHandler(restart_process)
    observer = Observer()
    # Watch current directory
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
            # Check if process died
            if process.poll() is not None:
                # If clean exit (0), we quit the reloader too
                if process.returncode == 0:
                    print("[Reloader] Ứng dụng đã thoát.")
                    observer.stop()
                    break
                # If crash (non-zero), we wait for file change
                else:
                    pass
    except KeyboardInterrupt:
        observer.stop()
        if process:
            process.terminate()
    
    observer.join()

if __name__ == "__main__":
    main()
