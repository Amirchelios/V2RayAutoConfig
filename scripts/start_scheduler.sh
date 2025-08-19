#!/bin/bash

echo "🚀 راه‌اندازی اجراکننده محلی برنامه‌های زمانبندی شده V2Ray AutoConfig"
echo ""

# بررسی وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 یافت نشد. لطفاً Python3 را نصب کنید."
    exit 1
fi

# نصب dependencies
echo "📦 نصب dependencies..."
pip3 install -r requirements.txt

# اجرای scheduler
echo "🕐 راه‌اندازی scheduler..."
python3 run_scheduled_tasks.py schedule
