#!/bin/bash
set -e

echo "==================================================="
echo "  live-speech-captions — cài đặt macOS"
echo "==================================================="

if ! command -v python3 &> /dev/null; then
    echo "[LỖI] Chưa có python3. Cài từ https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/3] Tạo .venv..."
    python3 -m venv .venv
else
    echo "[1/3] .venv đã có."
fi

echo "[2/3] Cài thư viện (requirements.txt)..."
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt

ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "  → Apple Silicon:"
    echo "     cp config/mac-gpu.ini.example config.ini"
else
    echo "  → Intel Mac:"
    echo "     cp config/mac-cpu.ini.example config.ini"
fi
echo "  (Whisper + OpenAI + Gemini trong cùng file — xem config/README.md)"

echo "[3/3] Kiểm tra ffmpeg / BlackHole..."
if ! command -v ffmpeg &> /dev/null; then
    echo "  [CẢNH BÁO] Thiếu ffmpeg — brew install ffmpeg hoặc https://evermeet.cx/ffmpeg/"
fi
if [ ! -d "/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver" ]; then
    echo "  [GỢI Ý] BlackHole: brew install blackhole-2ch"
    echo "           Hướng dẫn: BLACKHOLE_SETUP.md"
fi

echo ""
echo "  Xong. Chạy: ./start_mac.sh"
echo "==================================================="
