# live-speech-captions

Nhận giọng nói và hiển thị chữ lớn trên màn hình — macOS và Windows.

**Một file config** cho Whisper + **Deepgram realtime** + OpenAI/Gemini — chọn loại máy (Mac/Win, CPU/GPU), đổi engine trong app.

## Cài nhanh

```bash
./install_mac.sh
# Intel Mac:
cp config/mac-cpu.ini.example config.ini
# Apple Silicon (M1/M2/…):
cp config/mac-gpu.ini.example config.ini
./start_mac.sh
```

Bấm **▶ Bắt đầu**. Cần **realtime** → Engine **deepgram** (tab Cloud API). Whisper chậm → OpenAI/Gemini: [CLOUD_API_HUONG_DAN.md](./CLOUD_API_HUONG_DAN.md).

## Chọn config (4 file)

| Máy | Copy |
|-----|------|
| macOS **Intel** (CPU) | `cp config/mac-cpu.ini.example config.ini` |
| macOS **M-series** (GPU/MLX) | `cp config/mac-gpu.ini.example config.ini` |
| Windows **CPU** | `copy config\windows-cpu.ini.example config.ini` |
| Windows **GPU** NVIDIA | `copy config\windows-gpu.ini.example config.ini` |

Chi tiết: [config/README.md](./config/README.md)

Trong app đổi **Engine**: `whisper` / `mlx` / **`deepgram`** / `openai` / `gemini`.

## Thư viện

| Gói | Việc |
|-----|------|
| faster-whisper | Local Intel / Windows |
| mlx-whisper | Local Apple Silicon |
| deepgram-sdk | Realtime streaming (khuyến nghị) |
| openai, google-genai | Cloud batch (tùy chọn) |
| sounddevice | Âm thanh |

Không cần LLVM.

## Âm thanh hệ thống (YouTube, Zoom)

macOS: [BLACKHOLE_SETUP.md](./BLACKHOLE_SETUP.md)  
Windows: [WINDOWS.md](./WINDOWS.md)

## Windows

```cmd
install_windows.bat
copy config\windows-cpu.ini.example config.ini
start_windows.bat
```

## License

MIT — [LICENSE](./LICENSE)
