# Cloud API & Realtime (Deepgram / OpenAI / Gemini)

## Realtime (khuyến nghị): Deepgram

**Gemini/OpenAI batch** gửi từng đoạn âm → chậm, dễ **429** (Gemini ~5 RPM).  
**Deepgram** dùng **WebSocket streaming** — chữ cập nhật liên tục (partial/final).

```bash
source .venv/bin/activate
pip install -r requirements.txt   # gồm deepgram-sdk
./start_mac.sh
```

| Bước | Tab | Việc cần làm |
|------|-----|----------------|
| 1 | **Nhận giọng** | Engine = **`deepgram`** |
| 2 | **Cloud API** | Dán key [console.deepgram.com](https://console.deepgram.com) |
| 3 | | Model `nova-3`, ngôn ngữ `en` / `en-IN` (accent Ấn/Singapore) |
| 4 | | **Lưu cấu hình** → **Kiểm tra Deepgram** → OK |
| 5 | **Trang chủ** | **▶ Bắt đầu** + BlackHole (xem [BLACKHOLE_SETUP.md](./BLACKHOLE_SETUP.md)) |

Trong `config.ini`:

```ini
[transcription]
backend = deepgram
realtime_mode = true

[api]
deepgram_api_key = YOUR_KEY
deepgram_model = nova-3
deepgram_language = en
```

Hoặc biến môi trường: `export DEEPGRAM_API_KEY=...`

---

## Batch cloud: OpenAI / Gemini

Dùng khi không có Deepgram. Whisper local vẫn chạy được với `realtime_mode=true` (cắt câu ngắn hơn).

```bash
pip install openai google-genai
```

| Bước | Tab | Việc |
|------|-----|------|
| 1 | **Nhận giọng** | Engine = `openai` hoặc `gemini` |
| 2 | **Cloud API** | Key tương ứng |
| 3 | | Lưu → Kiểm tra → **Trang chủ** → Bắt đầu |

### Gemini 429 «limit: 5» (RPM)

- `cloud_min_request_interval = 13` — chờ giữa các lần gọi API
- `max_phrase_duration = 10` — ít cắt câu
- Model **`gemini-2.5-flash-lite`** (thường 10 RPM) hoặc bật billing

### Gemini 429 «limit: 0»

Đổi model sang **`gemini-2.5-flash`** / **`gemini-2.5-flash-lite`** (free tier).

---

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|-------------|-------------|------------|
| App tắt khi Lưu config | Reloader cũ restart trên `.ini` | `./start_mac.sh` (không `--reload`) |
| Bắt đầu vẫn Whisper | `backend=whisper` trong config | Engine = deepgram + Lưu |
| Không có chữ | Chưa route âm qua BlackHole | [BLACKHOLE_SETUP.md](./BLACKHOLE_SETUP.md) |
| Deepgram import error | Chưa cài SDK | `pip install 'deepgram-sdk>=3.5,<4'` |

**Không** commit `config.ini` có API key lên git.
