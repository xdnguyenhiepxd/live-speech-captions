# Mẫu cấu hình (`config/`)

App chỉ đọc **`config.ini`** ở thư mục gốc project. Các file trong `config/mac/` và `config/windows/` là **mẫu** — copy một file phù hợp rồi đổi tên.

## macOS

```bash
cd /path/to/live-speech-captions

# MacBook Air mới (Apple Silicon) — Chữ to, tiếng Anh, MLX (khuyến nghị):
cp config/mac/macbook-air.ini.example config.ini

# Chọn nhà cung cấp API khi dùng «Phụ đề + dịch»:
cp config/mac/deepseek.ini.example config.ini

# Hoặc ChatGPT, Gemini, Ollama local, …
cp config/mac/chatgpt.ini.example config.ini
cp config/mac/gemini.ini.example config.ini
cp config/mac/ollama.ini.example config.ini
```

Sửa `api_key` trong `config.ini` (hoặc export `OPENAI_API_KEY` / `OPENAI_BASE_URL`).

## Ngôn ngữ — phụ đề tiếng Anh / nhận giọng tiếng Anh

App tách **hai thứ** trong `config.ini`:

| Mục đích | Section | Tham số | Ghi như thế nào |
|----------|---------|---------|----------------|
| **Phụ đề dịch ra tiếng Anh** (ví dụ họp Trung → hiện English) | `[translation]` | `target_lang` | `target_lang = English` |
| **Phụ đề tiếng Việt** | `[translation]` | `target_lang` | `target_lang = Vietnamese` |
| **Phụ đề tiếng Trung** | `[translation]` | `target_lang` | `target_lang = Chinese` |
| **Bạn đang nói tiếng Anh** (Whisper/MLX nhận giọng) | `[transcription]` | `source_language` | `source_language = en` |
| **Tự đoán ngôn ngữ nói** | `[transcription]` | `source_language` | `source_language = auto` |

Ví dụ **họp tiếng Anh → phụ đề tiếng Anh** (chỉ transcript, không dịch sang ngôn ngữ khác vẫn cần API nếu bật pipeline dịch — thường đặt cùng ngôn ngữ):

```ini
[translation]
target_lang = English

[transcription]
source_language = en
```

Ví dụ **nói tiếng Việt → phụ đề tiếng Anh**:

```ini
[translation]
target_lang = English

[transcription]
source_language = vi
```

Có thể gõ tên đầy đủ trong Dashboard (**Target Language** có sẵn English; **Source Language**: `en`, `vi`, `zh`, `ja`, …). Giá trị `target_lang` được đưa thẳng vào prompt dịch (`Translate … into English`), nên dùng **`English`** (chữ E hoa) giống mặc định trong Dashboard.

## Windows

```cmd
cd C:\path\to\live-speech-captions
copy config\windows\deepseek.ini.example config.ini
copy config\windows\chatgpt.ini.example config.ini
```

## Danh sách mẫu theo API

| File (mac / windows) | Dịch vụ | `base_url` |
|----------------------|---------|------------|
| `macbook-air.ini.example` | **MacBook Air** — MLX + Chữ to EN (không bắt buộc API) | Tùy chọn / dummy |
| `chatgpt.ini.example` | OpenAI (ChatGPT) | `https://api.openai.com/v1` |
| `deepseek.ini.example` | DeepSeek | `https://api.deepseek.com` |
| `gemini.ini.example` | Google Gemini (OpenAI-compatible) | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `ollama.ini.example` | Ollama (local) | `http://localhost:11434/v1` |
| `groq.ini.example` | Groq | `https://api.groq.com/openai/v1` |
| `mistral.ini.example` | Mistral AI | `https://api.mistral.ai/v1` |
| `openrouter.ini.example` | OpenRouter (nhiều model) | `https://openrouter.ai/api/v1` |
| `azure-openai.ini.example` | Azure OpenAI | URL deployment của bạn |

Tất cả dùng SDK **OpenAI-compatible** (`openai` package). Lấy API key tại trang nhà cung cấp tương ứng.

## Khác biệt mac vs windows

| | macOS (`config/mac/`) | Windows (`config/windows/`) |
|--|------------------------|-----------------------------|
| ASR | `backend = mlx` (Apple Silicon) | `backend = whisper` |
| Thiết bị âm | Tự tìm BlackHole (`device_index = auto`) | Chọn VB-CABLE / mic trong Dashboard |
| GPU dịch âm | Metal (`device = auto`) | `device = cuda` hoặc `cpu` |
| Mẫu MacBook Air | `config/mac/macbook-air.ini.example` | — |
