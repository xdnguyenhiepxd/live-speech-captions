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

## Model khuyến nghị

| `whisper_model` | Kích thước | Tốc độ (Intel) | Độ chính xác EN |
|-----------------|----------|----------------|-----------------|
| **`distil-small.en`** ⭐ | ~166M | Nhanh | Tốt hơn `base.en` (mặc định) |
| `tiny.en` | ~39M | Nhanh nhất | Thấp hơn |
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
backend = whisper
whisper_model = distil-small.en
device = cpu
compute_type = int8
source_language = en
beam_size = 1
cpu_threads = 2

[audio]
reader_partial_updates = false
```

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
