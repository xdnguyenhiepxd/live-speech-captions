# Thử Moonshine Streaming Small (Intel / live caption)

[Moonshine Voice](https://github.com/moonshine-ai/moonshine) có bản **streaming** tối ưu cho **nhận giọng real-time trên CPU** (không cần GPU). Model **`SMALL_STREAMING`** (~123M tham số) cân bằng tốc độ / độ chính xác tiếng Anh.

## So với Whisper (faster-whisper) trong app hiện tại

| | Whisper `distil-small.en` | Moonshine `SMALL_STREAMING` |
|--|---------------------------|-----------------------------|
| Tích hợp app | Có (`backend=whisper`) | **Chưa** — script thử riêng |
| Streaming thật | Cắt câu + chạy lại model | Encoder cache, partial theo dòng |
| Tiếng Anh | Có | Có (streaming EN) |
| Intel CPU | ~0.9–2s E2E (tùy cấu hình) | Benchmark team ~**165ms**/chunk (Linux x86) |
| Cài thêm | `faster-whisper` | `moonshine-voice` + tải model |

## Cài và chạy thử (độc lập)

```bash
source .venv/bin/activate
pip install -r requirements-moonshine.txt
python test_moonshine_streaming.py
```

Lần đầu sẽ **tải model** Moonshine (vài trăm MB) về cache.

Tùy chọn:

```bash
python test_moonshine_streaming.py --arch tiny_streaming   # nhẹ hơn, kém chính xác hơn
python test_moonshine_streaming.py --arch small_streaming  # mặc định
```

## Tích hợp vào live-speech-captions

Cần thêm `backend = moonshine` trong `transcriber.py` + nối `AudioCapture` → `moonshine_voice.Transcriber.create_stream().add_audio()`.

Ưu điểm: partial text theo dòng, latency thấp hơn khi đã streaming.  
Nhược: dependency mới, model English streaming, chưa gắn overlay PyQt6 trong repo này.

Nếu thử script ổn và muốn gắn vào **▶ Bắt đầu** / Chữ to, bật Agent mode và nhắn «tích hợp moonshine».

## Tham khảo

- Model card: [UsefulSensors/moonshine-streaming-small](https://huggingface.co/UsefulSensors/moonshine-streaming-small)
- Python: `ModelArch.SMALL_STREAMING` + `get_model_for_language("en", ...)`
