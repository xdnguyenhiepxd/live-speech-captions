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
- **queue**: thời gian chờ trước khi ASR chạy (mục tiêu **&lt;50ms** sau bản queue 1 slot)  
- **E2E**: từ lúc cắt âm → hiện chữ  

Nếu **queue &gt; 200ms**: thường do nhiều job cũ — app giờ **chỉ giữ 1 job**, job mới thay job cũ (`[ASR] Bỏ job …`).

## Thử Moonshine Streaming Small

Model khác (streaming native, CPU): xem **[MOONSHINE.md](./MOONSHINE.md)** và `python test_moonshine_streaming.py`. Chưa gắn vào Dashboard — chỉ thử độc lập trước.

## Ba chế độ cấu hình

| File | Model | Khi nào dùng |
|------|-------|----------------|
| **`macbook-air-intel.ini.example`** ⭐ | `distil-small.en` | Cân bằng — **khuyến nghị** (đủ câu, ít sai từ) |
| `macbook-air-intel-fast.ini.example` | `tiny.en` | Rất nhanh — dễ **sai / cụt câu** |
| `macbook-air-intel-accurate.ini.example` | `small.en` | Chính xác nhất — chậm trên CPU |

**Sai từ / không hết câu** thường do bản **fast** (`max_phrase_duration` 2s, `tiny.en`). Dùng bản **cân bằng** ở trên.
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
whisper_model = distil-small.en
max_transcribe_seconds = 8.0
max_phrase_duration = 6.0
silence_duration = 0.55
use_context_prompt = true
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
