# Thử Moonshine Streaming Small

## Tên package đúng

Trên PyPI **không** có gói tên `moonshine` hay `moonshine-ai`. Cần cài:

```bash
pip install moonshine-voice
```

Import trong Python:

```python
import moonshine_voice   # dấu gạch dưới, không phải moonshine-voice
```

---

## Python 3.10.11 — cài đúng môi trường

Lỗi thường gặp: cài bằng `pip` của Python khác (3.11/3.14) nhưng chạy bằng `python3.10`.

```bash
# Tạo venv bằng đúng 3.10
python3.10 -m venv .venv-moonshine
source .venv-moonshine/bin/activate

python --version          # phải hiện 3.10.11
python -m pip install --upgrade pip
python -m pip install -r requirements-moonshine.txt

python -c "import moonshine_voice; print('OK')"
python test_moonshine_streaming.py
```

**Không** trộn với `.venv` của app chính nếu `.venv` dùng Python 3.14.

---

## macOS 11 + MacBook Air Intel 2018 — quan trọng

Bản có sẵn trên PyPI cho Mac:

| Phiên bản | Wheel Mac |
|-----------|-----------|
| **0.0.59** | `macosx_15_0_universal2` → cần **macOS 15+** |
| **0.0.61** | **Không** có wheel macOS (chỉ Linux ARM + Windows) |

Trên **macOS 11 Big Sur**, `pip install moonshine-voice` thường báo:

```text
ERROR: No matching distribution found for moonshine-voice
```

Đó **không phải** do Python 3.10.11 sai — **không có bản build** cho macOS 11 / Intel qua pip.

### Bạn có thể làm gì?

1. **Tiếp tục Whisper** (khuyến nghị trên máy này): `config/mac/macbook-air-intel.ini.example` + `distil-small.en` / `tiny.en`.
2. Thử máy **macOS 15+** (Apple Silicon hoặc Mac mới) nếu muốn Moonshine.
3. Theo dõi [moonshine-ai/moonshine](https://github.com/moonshine-ai/moonshine) — có thể sau này có wheel macOS cũ hơn.

---

## Chạy thử (khi pip cài được)

```bash
python test_moonshine_streaming.py --arch small_streaming
```

---

## So với app chính

App `live-speech-captions` dùng **faster-whisper** — tương thích macOS 11 + Python 3.10. Moonshine chưa tích hợp vào Dashboard.
