# live-speech-captions

Ứng dụng phụ đề thời gian thực: nhận giọng nói (ASR) và dịch sang ngôn ngữ đích, hiển thị trên overlay trong suốt cho macOS và Windows.

**GitHub:** https://github.com/xdnguyenhiepxd/live-speech-captions  
**Tác giả:** [Nguyễn Văn Hiệp (@xdnguyenhiepxd)](https://github.com/xdnguyenhiepxd)

## Tính năng

- **Nhận giọng thời gian thực**: `faster-whisper`, `mlx-whisper`, hoặc FunASR
- **Dịch bất đồng bộ** qua API tương thích OpenAI (DeepSeek, ChatGPT, Ollama, …)
- **Overlay**: cửa sổ phụ đề luôn nổi trên cùng, nền trong suốt
- **Hot reload** khi sửa code hoặc `config.ini`
- **Lưu transcript** để làm phụ đề hoặc phân tích sau

![Dashboard](./demo/main_dashboard.png)

---

## Hướng dẫn cài đặt và chạy

Ứng dụng gồm hai phần: **Bảng điều khiển** (cấu hình, chọn mic, API) và **Overlay** (cửa sổ phụ đề trong suốt, luôn nổi trên cùng). Lần đầu cần cài môi trường; các lần sau chỉ cần chạy script `start_*`.

### Yêu cầu chung

| Thành phần | Mô tả |
|------------|--------|
| Python | 3.10 trở lên |
| API dịch | OpenAI-compatible (`OpenAI`, `DeepSeek`, Ollama local, …) — cần `api_key` và `base_url` hợp lệ |
| ASR (nhận giọng) | Chạy **trên máy bạn** (Whisper / MLX / FunASR); lần đầu có thể tải model từ internet |
| FFmpeg | Bắt buộc cho xử lý âm thanh |
| Âm thanh hệ thống | Driver ảo: **BlackHole** (macOS) hoặc **VB-CABLE** (Windows) — nếu muốn bắt tiếng từ Zoom, YouTube, game, … chứ không chỉ mic vật lý |

---

### macOS — cài đặt từ đầu

#### Bước 1: Chuẩn bị hệ thống

Cài [Homebrew](https://brew.sh) nếu chưa có, rồi cài các gói cần thiết:

```bash
brew install python ffmpeg blackhole-2ch
```

- **python** — Python 3 cho virtualenv  
- **ffmpeg** — xử lý audio cho Whisper  
- **blackhole-2ch** — driver ảo 2 kênh; macOS sẽ hỏi mật khẩu khi cài  

(Tùy chọn, tiện khi đổi thiết bị âm thanh trong Bảng điều khiển: `brew install switchaudio-osx`)

#### Bước 2: Lấy mã nguồn

```bash
git clone git@github.com:xdnguyenhiepxd/live-speech-captions.git
cd live-speech-captions
```

Hoặc mở thư mục bạn đã clone sẵn.

#### Bước 3: Cài dependency Python

```bash
chmod +x install_mac.sh start_mac.sh
./install_mac.sh
```

Script sẽ:

1. Kiểm tra `python3`  
2. Tạo `.venv` (môi trường ảo)  
3. Cài `requirements.txt` (trên **Apple Silicon** tự cài thêm `mlx-whisper`)  
4. Cảnh báo nếu thiếu `ffmpeg` hoặc BlackHole  

**Bật MLX sau khi cài** — trong `config.ini` hoặc tab Nhận giọng trên Bảng điều khiển:

```ini
[transcription]
backend = mlx
whisper_model = base
```

#### Bước 4: Tạo và chỉnh `config.ini`

Chọn mẫu theo **hệ điều hành** và **nhà cung cấp API** trong thư mục `config/` (xem `config/README.md`):

```bash
# macOS — ví dụ DeepSeek + MLX
cp config/mac/deepseek.ini.example config.ini
```

Sửa `api_key = YOUR_...` thành key thật. Biến môi trường (nếu đặt) **ghi đè** file: `OPENAI_API_KEY`, `OPENAI_BASE_URL`.

#### Bước 5: Cấu hình âm thanh (BlackHole)

Để bắt **âm thanh phát ra từ máy** (họp online, video, game) đồng thời vẫn **nghe được loa**:

1. Mở **Audio MIDI Setup** (Cài đặt âm thanh MIDI).  
2. Nhấn **+** → **Create Multi-Output Device**.  
3. Tick **BlackHole 2ch** và **loa/thiết bị ra** bạn muốn nghe.  
4. Trong **System Settings → Sound**, chọn **Output** là Multi-Output vừa tạo.  

Minh họa: `demo/how_to_set_blackhole.png`, `demo/Audio_MIDI_Setup.png`, `demo/Audio_configuraiton.png`.

Nếu chỉ cần **micro thật**, có thể bỏ qua BlackHole và chọn mic trong Bảng điều khiển.

#### Bước 6: Chạy ứng dụng

```bash
./start_mac.sh
```

Script kích hoạt `.venv` và chạy `reloader.py` (hot reload: sửa file `.py` / `config.ini` sẽ tự khởi động lại app).

**Quyền macOS:** Lần đầu có thể cần cho phép **Microphone** (và đôi khi **Accessibility**) cho Terminal hoặc Python trong **System Settings → Privacy & Security**.

#### Bước 7: Dùng Bảng điều khiển và Overlay

1. Cửa sổ **Trung tâm điều khiển Phụ đề thời gian thực** mở ra.  
2. Tab **Âm thanh** — chọn thiết bị vào; chỉnh ngưỡng im lặng nếu không nhận tiếng hoặc nhận quá nhạy.  
3. Tab **Nhận giọng** — backend (`whisper` / `mlx` / `funasr`), kích thước model.  
4. Tab **Dịch** — API key, ngôn ngữ đích.  
5. Bấm **Lưu cấu hình** để ghi vào `config.ini`.  
6. Tab **Trang chủ**:
   - **▶ Phụ đề + dịch** — nhận giọng + dịch (cần API)
   - **🔤 Chữ to — chỉ nhận giọng** — chỉ chuyển giọng → chữ lớn, **không cần API**

**Trên overlay:**

- Kéo chữ để di chuyển cửa sổ  
- Kéo góc **◢** để đổi kích thước  
- **⏹** dừng phiên dịch  
- **💾 Lưu** xuất transcript  

Dừng hẳn app: đóng Bảng điều khiển hoặc `Ctrl+C` trong terminal.

#### macOS — chạy lại (đã cài xong)

```bash
cd live-speech-captions
./start_mac.sh
```

Chỉ cần `./install_mac.sh` lại khi đổi Python, xóa `.venv`, hoặc cập nhật `requirements.txt`.

#### macOS — xử lý sự cố

| Triệu chứng | Gợi ý |
|-------------|--------|
| Không có tiếng / không transcript | Kiểm tra thiết bị trong Bảng điều khiển; xem log terminal; thử giảm `silence_threshold` trong `config.ini` |
| **Cài BlackHole rồi không thấy trong Audio MIDI Setup** | Xem [BlackHole không hiện](#blackhole-cài-rồi-không-thấy-trong-thiết-bị-âm-thanh) bên dưới |
| Không bắt được âm hệ thống | BlackHole phải hiện trong sidebar → tạo Multi-Output tick BlackHole + loa |
| Lỗi thiếu `.venv` | Chạy lại `./install_mac.sh` |
| Dịch lỗi 401/403 | Kiểm tra `api_key`, `base_url`, tên model (ví dụ `deepseek-chat`) |
| Model Whisper tải chậm | Lần đầu tải model — đợi hoặc dùng `tiny` / `base` |
| App thoát sau khi sửa `config.ini` | Bình thường do hot reload — chạy lại `./start_mac.sh` |

#### BlackHole: cài rồi không thấy trong Thiết bị Âm thanh

1. **Chạy lại bộ cài .pkg**:
   ```bash
   open /opt/homebrew/Caskroom/blackhole-2ch/0.6.1/BlackHole2ch-0.6.1.pkg
   ```
   Nhập mật khẩu Mac → cài xong → **khởi động lại máy**.

2. **Khởi động lại dịch vụ âm thanh** (nếu chưa reboot):
   ```bash
   sudo killall coreaudiod
   ```
   Đóng **Thiết bị Âm thanh** rồi mở lại.

3. **Kiểm tra đã nhận driver:**
   ```bash
   system_profiler SPAudioDataType | grep -i blackhole
   ```

4. **macOS 15 (Sequoia):** **Cài đặt hệ thống → Quyền riêng tư & Bảo mật** — cho phép phần mềm hệ thống nếu bị chặn.

5. **Sau khi BlackHole hiện** — tạo **Thiết bị Nhiều Đầu ra**, tick **BlackHole 2ch** + loa, đặt Output hệ thống = Multi-Output. Trong app chọn input **BlackHole 2ch**.

**Tạm thời không cần BlackHole:** chỉ dùng **Micrô MacBook** — app vẫn chạy, không bắt tiếng từ video/Zoom phát ra loa.

---

### Windows — cài đặt từ đầu

#### Bước 1: Chuẩn bị hệ thống

1. **Python 3.10+** — [python.org](https://www.python.org/downloads/), bật “Add python.exe to PATH”.  
2. **FFmpeg** — [ffmpeg.org/download.html](https://ffmpeg.org/download.html) hoặc `winget install ffmpeg`.  
3. **VB-CABLE** (khuyến nghị) — [vb-audio.com/Cable](https://vb-audio.com/Cable/).

#### Bước 2–7

Tương tự macOS: `install_windows.bat` → copy `config\windows\*.ini.example` → `start_windows.bat` → cấu hình trên Bảng điều khiển → **Khởi chạy phụ đề**.

Mẫu Windows mặc định `device = cuda`; máy không có GPU NVIDIA → đổi `device = cpu` trong `config.ini`.

---

### Cấu hình `config.ini`

| Section | Tham số chính | Ghi chú |
|---------|----------------|---------|
| `[api]` | `base_url`, `api_key` | Endpoint OpenAI-compatible |
| `[translation]` | `model`, `target_lang`, `threads` | Model dịch, ngôn ngữ đích |
| `[transcription]` | `backend`, `whisper_model`, `device`, `compute_type` | `whisper` / `mlx` / `funasr` |
| `[audio]` | `device_index`, `streaming_mode`, `silence_threshold`, … | `device_index = auto` hoặc số index |
| `[display]` | `display_duration`, `window_width`, `window_height` | Giao diện overlay |

**Phụ đề tiếng Anh:**

```ini
[translation]
target_lang = English

[transcription]
source_language = en
```

- `target_lang` = ngôn ngữ **hiển thị trên overlay** (`English`, `Vietnamese`, `Chinese`, …)  
- `source_language` = ngôn ngữ **đang nói** (`en`, `vi`, `zh`, hoặc `auto`)  

Chi tiết: `config/README.md`. FunASR: `FUNASR_GUIDE.md`.

**Bảo mật:** Không commit `config.ini`. Chỉ dùng placeholder trong `config/**/*.ini.example`.

---

## License

MIT — Copyright 2025 Nguyễn Văn Hiệp
