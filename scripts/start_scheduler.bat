@echo off
chcp 65001 >nul
echo 🚀 راه‌اندازی اجراکننده محلی برنامه‌های زمانبندی شده V2Ray AutoConfig
echo.

REM بررسی وجود Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python یافت نشد. لطفاً Python را نصب کنید.
    pause
    exit /b 1
)

REM نصب dependencies
echo 📦 نصب dependencies...
pip install -r requirements.txt

REM اجرای scheduler
echo 🕐 راه‌اندازی scheduler...
python run_scheduled_tasks.py schedule

pause
