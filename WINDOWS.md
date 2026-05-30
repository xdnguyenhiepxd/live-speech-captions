# Windows — cài đặt (CPU & GPU NVIDIA)

App dùng **faster-whisper** + model **`distil-small.en`** (tiếng Anh, nhẹ, cân bằng tốc độ/chính xác). **Không** cần API key hay LLVM.

## Yêu cầu

| Thành phần | Ghi chú |
|------------|---------|
| **Windows 10/11** | 64-bit |
| **Python 3.10–3.12** | [python.org](https://www.python.org/downloads/) — bật **Add python.exe to PATH** |
| **FFmpeg** | Thêm vào PATH — [ffmpeg.org](https://ffmpeg.org/download.html) (hoặc `winget install Gyan.FFmpeg`) |

## Cài app

Mở **Command Prompt** hoặc **PowerShell** trong thư mục project:

```cmd
install_windows.bat
```

Sau đó chọn **một** file cấu hình:

### CPU (máy không có GPU NVIDIA, hoặc không cài CUDA)

```cmd
copy config\windows-cpu.ini.example config.ini
start_windows.bat
```

Trong `config.ini`:

```ini
[transcription]
whisper_model = distil-small.en
device = cpu
compute_type = int8
```

### GPU NVIDIA (nhanh hơn rõ)

1. Cài **driver NVIDIA** mới nhất ([nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx)).
2. Kiểm tra GPU: `nvidia-smi` (phải hiện tên card, không lỗi).
3. `faster-whisper` dùng **CTranslate2**; bản wheel thường đã hỗ trợ CUDA. Nếu log báo không có CUDA, thử trong `.venv`:

   ```cmd
   call .venv\Scripts\activate.bat
   pip install --upgrade faster-whisper ctranslate2
   ```

4. Copy cấu hình GPU:

   ```cmd
   copy config\windows-gpu.ini.example config.ini
   start_windows.bat
   ```

Trong `config.ini`:

```ini
[transcription]
whisper_model = distil-small.en
device = cuda
compute_type = float16
```

Nếu GPU báo lỗi bộ nhớ, đổi `compute_type = int8_float16` hoặc quay lại bản **CPU**.

## Model `distil-small.en`

- Trong app chỉ gõ **`distil-small.en`** (tên ngắn).
- **Không** dùng `distil-whisper/distil-small.en` — đó là bản PyTorch, sẽ lỗi `Unable to open model.bin`.
- Lần chạy đầu tải model qua Hugging Face (~vài trăm MB).

Xóa cache nếu tải nhầm bản cũ:

```cmd
rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--distil-whisper--distil-small.en"
```

## Âm thanh hệ thống (YouTube, Zoom, trình duyệt)

Windows không có BlackHole; dùng **VB-Audio Virtual Cable** (VB-CABLE):

1. Tải và cài: [vb-audio.com/Cable](https://vb-audio.com/Cable/)
2. **Cài đặt → Hệ thống → Âm thanh → Đầu ra**: chọn **CABLE Input (VB-Audio Virtual Cable)** khi xem video/họp (hoặc dùng Voicemeeter để vừa nghe loa vừa gửi vào cable).
3. Trong app: tab **Âm thanh** → thiết bị vào = **CABLE Output** (hoặc `device_index = auto` trong `config.ini` — app tự tìm thiết bị có chữ *cable* / *vb-audio*).

Chỉ dùng **mic** thì chọn mic trong tab **Âm thanh**, không cần VB-CABLE.

## Chạy & giao diện

```cmd
start_windows.bat
```

Bấm **▶ Bắt đầu** trên bảng điều khiển.

## Log thời gian

Với `log_latency = true`, terminal hiện:

```
[LATENCY] final chunk=1 | audio=1.2s | queue=5ms | asr=180ms | text="..."
```

- **GPU**: `asr` thường thấp hơn nhiều so với CPU.
- **queue** cao (&gt;200ms): máy đang xử lý chậm — giảm `reader_partial_updates` hoặc tăng `reader_update_interval`.

## So sánh nhanh

| | CPU | GPU (CUDA) |
|--|-----|------------|
| File mẫu | `config/windows-cpu.ini.example` | `config/windows-gpu.ini.example` |
| `device` | `cpu` | `cuda` |
| `compute_type` | `int8` | `float16` |
| Phần cứng | Mọi PC | NVIDIA + driver |

## Whisper quá chậm → OpenAI / Gemini

1. Dùng `windows-cpu.ini.example` (hoặc gpu), trong app đặt `backend = openai`
2. Mở app → tab **☁️ Cloud API** → nhập OpenAI API key → **Lưu cấu hình**
3. Engine **openai** hoặc **gemini** ở tab **Nhận giọng**

Cần `pip install openai google-genai` (đã có trong `requirements.txt`).

## Sự cố thường gặp

| Triệu chứng | Gợi ý |
|-------------|--------|
| `Python is not found` | Cài Python, tick **Add to PATH**, mở lại CMD |
| `FFmpeg is not found` | Cài FFmpeg, thêm vào PATH |
| `Unable to open model.bin` | Dùng `distil-small.en`, xóa cache (mục trên) |
| CUDA / GPU không dùng được | `nvidia-smi`; thử `device = cpu`; cập nhật driver |
| Không có chữ khi phát YouTube | Cài VB-CABLE, đặt đầu ra = CABLE Input, app chọn CABLE Output |
