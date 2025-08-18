@echo off
chcp 65001 >nul
title VLESS Tester - TrustLink

echo.
echo ========================================
echo    🔗 VLESS Tester - TrustLink
echo ========================================
echo.

echo انتخاب کنید:
echo 1. اجرای یکباره
echo 2. اجرای خودکار هر ساعت
echo 3. خروج
echo.

set /p choice="انتخاب شما (1-3): "

if "%choice%"=="1" (
    echo.
    echo 🚀 اجرای یکباره VLESS Tester...
    python vless_tester.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo ⏰ اجرای خودکار هر ساعت...
    echo برای توقف برنامه Ctrl+C را فشار دهید
    python vless_tester.py --auto
) else if "%choice%"=="3" (
    echo.
    echo خروج از برنامه...
    exit
) else (
    echo.
    echo ❌ انتخاب نامعتبر!
    pause
)
