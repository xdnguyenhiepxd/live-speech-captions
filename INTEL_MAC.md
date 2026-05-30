# MacBook Air Intel — tối ưu nhận giọng tiếng Anh

Dành cho **Mac Intel** (không có MLX). Mục tiêu: **model nhẹ**, **chỉ tiếng Anh**, **chính xác tốt** trên CPU.

## Cài nhanh

```bash
./install_mac.sh
cp config/mac/macbook-air-intel.ini.example config.ini
./start_mac.sh
```

**PyQt6** trong `requirements.txt` được ghim **6.5.4** + **PyQt6-sip 13.6.0** (tương thích macOS 11 / Intel). Nếu `pip` báo xung đột Qt6, cài tay:

```bash
source .venv/bin/activate
pip install PyQt6==6.5.4 PyQt6-sip==13.6.0 PyQt6-Qt6==6.5.3
```

## Log thời gian (terminal)

Với `log_latency = true` (mặc định trên bản Intel):

```
[AUDIO] chunk=2 final | 1.10s audio | → gửi ASR @ 14:32:01
[LATENCY] final chunk=2 | audio=1.10s | queue=3ms | asr=420ms | text="hello world"
[LATENCY] final chunk=2 | E2E=425ms (âm thanh → chữ trên màn hình)
```

- **asr**: thời gian model chạy  
- **queue**: chờ thread ASR  
- **E2E**: từ lúc cắt âm → hiện chữ  

## Model khuyến nghị

| `whisper_model` | Kích thước | Tốc độ (Intel) | Độ chính xác EN |
|-----------------|----------|----------------|-----------------|
| **`tiny.en`** ⭐ (mặc định) | ~39M | Nhanh nhất | Đủ YouTube / họp EN |
| `distil-small.en` | ~166M | Chậm hơn ~3–5× | Tốt hơn tiny |
| `base.en` | ~74M | Nhanh | Ổn |
| `small.en` | ~244M | Chậm trên Air cũ | Cao |
| `distil-medium.en` | ~394M | Chậm | Cao hơn distil-small |

**Distil-Whisper** ([Hugging Face](https://huggingface.co/distil-whisper)): chỉ tiếng Anh, chạy qua **faster-whisper** + **int8**.

Trong `config.ini` dùng **`distil-small.en`** (tên ngắn). **Không** dùng `distil-whisper/distil-small.en` — đó là bản PyTorch, sẽ lỗi `Unable to open file 'model.bin'`.

Nếu đã lỗi cache:

```bash
rm -rf ~/.cache/huggingface/hub/models--distil-whisper--distil-small.en
./start_mac.sh
```

## Tham số `config.ini` quan trọng

```ini
[transcription]
whisper_model = tiny.en
vad_filter = false
max_transcribe_seconds = 3.0
log_latency = true
cpu_threads = 4

[audio]
max_phrase_duration = 3.0
reader_partial_updates = false
standard_cut_duration = 0.75
```

Bản **chính xác hơn**: `macbook-air-intel-accurate.ini.example` (`distil-small.en`).

- **`beam_size = 1`**: nhanh nhất, đủ cho phụ đề live.
- **`cpu_threads`**: 2–4 tùy số nhân (Air 2018 thường 2–4 nhân logic).
- **`reader_partial_updates = false`**: chữ cập nhật theo câu, **giảm tải CPU** rõ trên Intel.

Bật lại partial nếu muốn chữ chạy theo khi nói (máy sẽ nặng hơn):

```ini
reader_partial_updates = true
reader_update_interval = 1.3
```

## YouTube / âm hệ thống

Xem [BLACKHOLE_SETUP.md](./BLACKHOLE_SETUP.md).

## So sánh với Mac M-series

| | Intel Air | M-series Air |
|--|-----------|--------------|
| Backend | `whisper` | `mlx` |
| Model gợi ý | `distil-small.en` | `small.en` |
| GPU | Không | Metal (MLX) |
