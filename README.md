# live-speech-captions

Nhận giọng nói (Whisper) và hiển thị chữ lớn trên màn hình — macOS và Windows. **Không dịch, không API, không cần LLVM.**

## Cài nhanh (macOS)

```bash
git clone <URL-repository>/live-speech-captions.git
cd live-speech-captions
chmod +x install_mac.sh start_mac.sh
./install_mac.sh
cp config/mac/macbook-air.ini.example config.ini   # Intel: macbook-air-intel.ini.example
./start_mac.sh
```

Bấm **▶ Bắt đầu** trên bảng điều khiển.

## Có bắt buộc cài LLVM không?

**Không.** LLVM chỉ xuất hiện nếu trước đây cài bộ nặng (`funasr`, `modelscope`, `openai`) hoặc `brew install llvm`. Project hiện chỉ dùng:

| Gói | Việc |
|-----|------|
| PyQt6 | Giao diện |
| faster-whisper | Nhận giọng (Intel / Windows) |
| mlx-whisper | Nhận giọng (Apple Silicon, tự cài trên arm64) |
| sounddevice | Bắt âm thanh |

## Cấu hình

| Máy | `config.ini` | `backend` |
|-----|--------------|-----------|
| Mac M1/M2/M3/M4 | `config/mac/macbook-air.ini.example` | `mlx` |
| Mac Intel 2018+ | `config/mac/macbook-air-intel.ini.example` | `whisper` |

```ini
[transcription]
whisper_model = small.en
source_language = en
```

## Âm thanh hệ thống (YouTube, Zoom)

1. Cài [BlackHole](https://existential.audio/blackhole/) (macOS).  
2. **Đầu ra** macOS = **Multi-Output Device** (loa + BlackHole).  
3. Trong app: thiết bị vào = **BlackHole 2ch**.

Chỉ dùng mic laptop thì chọn mic trong tab **Âm thanh**.

## Windows

```cmd
install_windows.bat
copy config.ini.example config.ini
start_windows.bat
```

Đặt `backend = whisper`, `device = cpu` trong `config.ini`.

## License

MIT — [LICENSE](./LICENSE)
