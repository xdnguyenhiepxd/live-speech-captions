# live-speech-captions

Nhận giọng nói (Whisper) và hiển thị chữ lớn trên màn hình — macOS và Windows. **Không dịch, không API, không cần LLVM.**

## Cài nhanh (macOS)

```bash
git clone <URL-repository>/live-speech-captions.git
cd live-speech-captions
chmod +x install_mac.sh start_mac.sh
./install_mac.sh
cp config/mac/macbook-air-intel.ini.example config.ini 
./start_mac.sh
```

Bấm **▶ Bắt đầu** trên bảng điều khiển.

## Có bắt buộc cài LLVM không?

**Không.** LLVM chỉ xuất hiện nếu trước đây cài bộ nặng (`funasr`, `modelscope`, `openai`) hoặc `brew install llvm`. Project hiện chỉ dùng:

| Gói | Việc |
|-----|------|
| PyQt6 6.5.4 (+ sip 13.6.0) | Giao diện (ghim cho macOS 11 / Intel) |
| faster-whisper | Nhận giọng (Intel / Windows) |
| mlx-whisper | Nhận giọng (Apple Silicon, tự cài trên arm64) |
| sounddevice | Bắt âm thanh |

## Cấu hình

| Máy | `config.ini` | `backend` |
|-----|--------------|-----------|
| Mac M1/M2/M3/M4 | `config/mac/macbook-air.ini.example` | `mlx` |
| Mac Intel 2018+ | `config/mac/macbook-air-intel.ini.example` | `whisper` + **`distil-small.en`** |

Chi tiết tối ưu Intel: **[INTEL_MAC.md](./INTEL_MAC.md)**

```ini
[transcription]
whisper_model = small.en
source_language = en
```

## Âm thanh hệ thống (YouTube, Zoom)

Để **nghe video YouTube / Zoom qua loa** mà app vẫn hiện chữ, cần **BlackHole** + **Multi-Output** trên macOS.

**Hướng dẫn chi tiết từng bước (có ảnh):** [BLACKHOLE_SETUP.md](./BLACKHOLE_SETUP.md)

Tóm tắt:

1. `brew install blackhole-2ch` (hoặc tải từ [existential.audio/blackhole](https://existential.audio/blackhole/))  
2. **Audio MIDI Setup** → tạo **Multi-Output** (tick **Loa** + **BlackHole 2ch**)  
3. **Cài đặt hệ thống → Âm thanh → Đầu ra** = Multi-Output  
4. Trong app: tab **Âm thanh** → thiết bị vào = **BlackHole 2ch** (hoặc `device_index = auto`)

Chỉ dùng **mic laptop** thì không cần BlackHole — chọn mic trong tab **Âm thanh**.

## Windows

```cmd
install_windows.bat
copy config.ini.example config.ini
start_windows.bat
```

Đặt `backend = whisper`, `device = cpu` trong `config.ini`.

## License

MIT — [LICENSE](./LICENSE)
