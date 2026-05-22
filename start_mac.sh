#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[LỖI] Chưa có môi trường ảo .venv."
    echo "Chạy './install_mac.sh' trước."
    exit 1
fi

echo "[Khởi động] Kích hoạt môi trường..."
source .venv/bin/activate

echo "[Khởi động] Chạy ứng dụng (hot reload)..."
python reloader.py
