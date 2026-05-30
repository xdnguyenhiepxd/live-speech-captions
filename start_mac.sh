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

if [ "$1" = "--reload" ]; then
    echo "[Khởi động] Chạy với hot reload (chỉ khi sửa code .py)..."
    python reloader.py
else
    echo "[Khởi động] Chạy ứng dụng..."
    echo "  (Thêm --reload nếu đang phát triển code)"
    python launcher.py
fi
