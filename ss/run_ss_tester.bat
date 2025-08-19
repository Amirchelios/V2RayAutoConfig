@echo off
chcp 65001 >nul
title TrustLink Shadowsocks Tester

echo.
echo ========================================
echo    🔗 TrustLink Shadowsocks Tester
echo ========================================
echo.

echo 📋 بررسی محیط...
if not exist "..\Files\xray-bin\xray.exe" (
    echo ❌ فایل Xray یافت نشد!
    echo 📁 مسیر مورد انتظار: ..\Files\xray-bin\xray.exe
    echo.
    pause
    exit /b 1
)

if not exist "..\configs\raw\ShadowSocks.txt" (
    echo ❌ فایل منبع Shadowsocks یافت نشد!
    echo 📁 مسیر مورد انتظار: ..\configs\raw\ShadowSocks.txt
    echo.
    pause
    exit /b 1
)

echo ✅ محیط آماده است
echo.

echo 🔧 نصب وابستگی‌ها...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ خطا در نصب وابستگی‌ها
    pause
    exit /b 1
)

echo ✅ وابستگی‌ها نصب شدند
echo.

echo 🚀 شروع تست کانفیگ‌های Shadowsocks...
echo 📊 حالت: تست یکباره
echo.

python ss_tester.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ تست با موفقیت تکمیل شد!
    echo 📁 نتایج در: ..\trustlink\trustlink_ss.txt
    echo 📊 متادیتا در: ..\trustlink\.trustlink_ss_metadata.json
    echo 📝 لاگ‌ها در: ..\logs\ss_tester.log
) else (
    echo.
    echo ❌ خطا در اجرای تست
    echo 📝 لطفاً لاگ‌ها را بررسی کنید
)

echo.
pause
