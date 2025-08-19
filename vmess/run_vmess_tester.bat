@echo off
chcp 65001 >nul
title VMESS Tester - تستر کانفیگ‌های VMESS

echo.
echo ========================================
echo    🔗 VMESS Tester - تستر هوشمند
echo ========================================
echo.

cd /d "%~dp0"

echo در حال بررسی Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python یافت نشد! لطفاً Python را نصب کنید.
    pause
    exit /b 1
)

echo ✅ Python یافت شد
echo.

echo در حال نصب وابستگی‌ها...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ خطا در نصب وابستگی‌ها
    pause
    exit /b 1
)

echo ✅ وابستگی‌ها نصب شدند
echo.

echo انتخاب نوع اجرا:
echo 1. اجرای یکباره
echo 2. اجرای خودکار هر ساعت
echo 3. اجرای پیشرفته
echo.
set /p choice="انتخاب شما (1-3): "

if "%choice%"=="1" (
    echo.
    echo 🚀 شروع اجرای یکباره...
    python vmess_tester.py
) else if "%choice%"=="2" (
    echo.
    echo 🔄 شروع اجرای خودکار...
    python vmess_tester.py --auto
) else if "%choice%"=="3" (
    echo.
    echo ⚡ شروع اجرای پیشرفته...
    python run_vmess_tester_enhanced.py
) else (
    echo.
    echo ❌ انتخاب نامعتبر
)

echo.
echo ✅ اجرا تکمیل شد
pause
