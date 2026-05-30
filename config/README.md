# Cấu hình — một file cho mỗi loại máy

App chỉ đọc **`config.ini`** ở thư mục gốc.

Mỗi file mẫu gồm **Whisper/MLX (local)**, **Deepgram (realtime)**, **OpenAI/Gemini (batch)**. Đổi engine trong app — không cần copy file khác.

## Chọn file (4 loại)

| Máy | Lệnh copy |
|-----|-----------|
| **macOS Intel** (CPU) | `cp config/mac-cpu.ini.example config.ini` |
| **macOS M1/M2/M3/M4** (GPU/MLX) | `cp config/mac-gpu.ini.example config.ini` |
| **Windows CPU** | `copy config\windows-cpu.ini.example config.ini` |
| **Windows GPU NVIDIA** | `copy config\windows-gpu.ini.example config.ini` |

## Engine (`backend`)

| Giá trị | Ý nghĩa |
|--------|---------|
| `whisper` | Local — Intel / Windows |
| `mlx` | Local — chỉ Mac Apple Silicon |
| `deepgram` | **Realtime** WebSocket — `deepgram_api_key` |
| `openai` | Cloud batch — `openai_api_key` |
| `gemini` | Cloud batch — `gemini_api_key` |

Đổi trong app hoặc `[transcription] backend = ...` trong `config.ini`.

## Section trong config.ini

| Section | Nội dung |
|---------|----------|
| `[transcription]` | Engine, model Whisper, CPU/GPU, ngôn ngữ |
| `[api]` | Key Deepgram / OpenAI / Gemini |
| `[audio]` | BlackHole/VB-CABLE, VAD, partial |
| `[display]` | Cỡ chữ overlay |

**Không** commit `config.ini` có API key lên git.

## Âm thanh hệ thống

- macOS: [BLACKHOLE_SETUP.md](../BLACKHOLE_SETUP.md)  
- Windows: [WINDOWS.md](../WINDOWS.md)  
- Cloud khi Whisper chậm: [CLOUD_API_HUONG_DAN.md](../CLOUD_API_HUONG_DAN.md)  
- Intel tối ưu: [INTEL_MAC.md](../INTEL_MAC.md)
