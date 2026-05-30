#!/usr/bin/env python3
"""
Thử Moonshine Streaming trên âm thanh máy (BlackHole) — độc lập với app chính.

Cần Multi-Output: Loa + BlackHole 2ch, đầu ra hệ thống = Multi-Output.

  pip install -r requirements-moonshine.txt
  python test_moonshine_streaming.py
  python test_moonshine_streaming.py --list-devices
  python test_moonshine_streaming.py --device 3
"""

import argparse
import sys
import time

import numpy as np
import sounddevice as sd


def find_blackhole_device():
    """Ưu tiên BlackHole; không có thì None (thiết bị vào mặc định)."""
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and "blackhole" in d["name"].lower():
            return i
    return None


def resolve_device_index(device_arg):
    if device_arg in ("auto", ""):
        idx = find_blackhole_device()
        if idx is not None:
            return idx
        print("[Audio] Không thấy BlackHole — dùng thiết bị vào mặc định.")
        print("        Cài: brew install blackhole-2ch — xem BLACKHOLE_SETUP.md")
        return None
    if device_arg == "default":
        return None
    return int(device_arg)


def input_channels_for(device_index):
    try:
        if device_index is None:
            info = sd.query_devices(kind="input")
        else:
            info = sd.query_devices(device_index)
        ch = int(info.get("max_input_channels", 1) or 1)
        return min(2, ch) if ch >= 2 else 1
    except Exception:
        return 1


def to_mono(samples):
    if samples.ndim == 1:
        return samples
    if samples.ndim == 2:
        return samples.mean(axis=1) if samples.shape[1] >= 2 else samples[:, 0]
    return samples.flatten()


def list_input_devices():
    print("Thiết bị vào (input):")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            tag = ""
            if "blackhole" in d["name"].lower():
                tag = "  ← BlackHole"
            print(f"  [{i}] {d['name']} ({d['max_input_channels']} ch){tag}")


def main():
    parser = argparse.ArgumentParser(
        description="Thử Moonshine streaming (âm thanh máy / BlackHole)"
    )
    parser.add_argument(
        "--arch",
        choices=("tiny_streaming", "small_streaming", "medium_streaming"),
        default="small_streaming",
        help="tiny=nhanh nhất, small=cân bằng, medium=chính xác nhất",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="auto=BlackHole, default=mic/đầu vào hệ thống, hoặc số index",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Tần số lấy mẫu (Moonshine chấp nhận nhiều rate)",
    )
    parser.add_argument(
        "--chunk",
        type=float,
        default=0.1,
        help="Độ dài mỗi khối audio (giây)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Liệt kê thiết bị vào rồi thoát",
    )
    args = parser.parse_args()

    if args.list_devices:
        list_input_devices()
        return

    try:
        from moonshine_voice import (
            ModelArch,
            Transcriber,
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

    device_index = resolve_device_index(args.device)
    channels = input_channels_for(device_index)
    block_size = int(args.sample_rate * args.chunk)

    if device_index is None:
        dev = sd.query_devices(kind="input")
        dev_label = f"mặc định: {dev['name']}"
    else:
        dev = sd.query_devices(device_index)
        dev_label = f"[{device_index}] {dev['name']}"

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
    print(f"[Audio] Vào: {dev_label} ({channels} ch → mono, {args.sample_rate} Hz)")
    print("Phát YouTube/Zoom qua Multi-Output — Ctrl+C dừng\n")

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

    transcriber = Transcriber(model_path=model_path, model_arch=model_arch)
    transcriber.add_listener(LatencyListener())
    transcriber.start()

    chunk_count = 0
    max_rms = 0.0

    try:
        with sd.InputStream(
            device=device_index,
            channels=channels,
            samplerate=args.sample_rate,
            blocksize=block_size,
            dtype="float32",
        ) as stream:
            while True:
                data, overflow = stream.read(block_size)
                if overflow:
                    print("[Audio] overflow")
                mono = to_mono(data)
                rms = float(np.sqrt(np.mean(mono**2)))
                max_rms = max(max_rms, rms)
                chunk_count += 1
                if chunk_count == 25 and max_rms < 0.0001:
                    print("\n[Audio] ⚠️ Không có tín hiệu (RMS≈0).")
                    print("    → Đầu ra hệ thống = Multi-Output (Loa + BlackHole)")
                    print("    → Phát YouTube rồi thử lại\n")
                transcriber.add_audio(mono.tolist(), args.sample_rate)
    except KeyboardInterrupt:
        print("\n[Dừng]")
    finally:
        transcriber.stop()
        transcriber.close()


if __name__ == "__main__":
    main()
