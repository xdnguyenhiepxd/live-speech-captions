#!/usr/bin/env python3
"""
Thử Moonshine Streaming trên mic — độc lập với app chính.

  pip install -r requirements-moonshine.txt
  python test_moonshine_streaming.py
"""

import argparse
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Thử Moonshine streaming (mic)")
    parser.add_argument(
        "--arch",
        choices=("tiny_streaming", "small_streaming", "medium_streaming"),
        default="small_streaming",
        help="tiny=nhanh nhất, small=cân bằng, medium=chính xác nhất",
    )
    args = parser.parse_args()

    try:
        from moonshine_voice import (
            MicTranscriber,
            ModelArch,
            TranscriptEventListener,
            get_model_for_language,
        )
    except ImportError as e:
        print("Không import được moonshine_voice.")
        print(f"  Chi tiết: {e}")
        print()
        print("Kiểm tra:")
        print("  1. Tên package: pip install moonshine-voice  (không phải «moonshine»)")
        print("  2. Đúng Python:  python3.10 -m pip install -r requirements-moonshine.txt")
        print("  3. macOS 11 / Intel: PyPI có thể KHÔNG có wheel — xem MOONSHINE.md")
        sys.exit(1)

    arch_map = {
        "tiny_streaming": ModelArch.TINY_STREAMING,
        "small_streaming": ModelArch.SMALL_STREAMING,
        "medium_streaming": ModelArch.MEDIUM_STREAMING,
    }
    wanted = arch_map[args.arch]

    print(f"[Moonshine] Tải model EN + {args.arch} …")
    t0 = time.perf_counter()
    model_path, model_arch = get_model_for_language(
        "en", wanted_model_arch=wanted
    )
    print(f"[Moonshine] Sẵn sàng sau {(time.perf_counter() - t0):.1f}s")
    print(f"  path={model_path}")
    print(f"  arch={model_arch}")
    print("Nghe micro — Ctrl+C dừng\n")

    class LatencyListener(TranscriptEventListener):
        def __init__(self):
            self._line_t0 = {}

        def on_line_started(self, event):
            self._line_t0[id(event.line)] = time.perf_counter()
            print(f"\n▶ Bắt đầu dòng: {event.line.text!r}")

        def on_line_text_changed(self, event):
            t0 = self._line_t0.get(id(event.line))
            ms = (time.perf_counter() - t0) * 1000 if t0 else 0
            print(f"  … partial ({ms:.0f}ms): {event.line.text}")

        def on_line_completed(self, event):
            t0 = self._line_t0.get(id(event.line), time.perf_counter())
            ms = (time.perf_counter() - t0) * 1000
            dur = getattr(event.line, "duration", 0) or 0
            print(f"✓ Hoàn thành ({ms:.0f}ms, audio~{dur:.2f}s): {event.line.text}")
            self._line_t0.pop(id(event.line), None)

    mic = MicTranscriber(model_path=model_path, model_arch=model_arch)
    mic.add_listener(LatencyListener())
    mic.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[Dừng]")
    finally:
        mic.stop()
        mic.close()


if __name__ == "__main__":
    main()
