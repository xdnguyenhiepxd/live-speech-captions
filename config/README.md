# Cấu hình

App chỉ đọc **`config.ini`** ở thư mục gốc.

## macOS

```bash
# Apple Silicon (M1/M2/M3/M4)
cp config/mac/macbook-air.ini.example config.ini

# Intel Mac (2018–2020) — distil-small.en, CPU int8
cp config/mac/macbook-air-intel.ini.example config.ini
```

Xem **[INTEL_MAC.md](../INTEL_MAC.md)** (model nhẹ, chỉ tiếng Anh).

## Tham số chính

| Section | Tham số | Ghi chú |
|---------|---------|---------|
| `[transcription]` | `backend` | `mlx` (M-chip) hoặc `whisper` (Intel) |
| `[transcription]` | `whisper_model` | Tiếng Anh: `small.en`, `base.en`, … |
| `[transcription]` | `source_language` | `en` nếu chỉ nói tiếng Anh |
| `[display]` | `reader_font_size` | Cỡ chữ overlay |
| `[audio]` | `device_index` | `auto` = tự tìm BlackHole |

YouTube / tiếng hệ thống: cài BlackHole + Multi-Output — **[BLACKHOLE_SETUP.md](../BLACKHOLE_SETUP.md)**.

## Cài thư viện

```bash
./install_mac.sh
```

Chỉ cần `requirements.txt` (PyQt6, faster-whisper, sounddevice) — **không** cần LLVM, không API key.
