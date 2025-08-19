@echo off
chcp 65001 >nul
title TrustLink Trojan Tester

echo ========================================
echo    🔗 TrustLink Trojan Tester
echo ========================================

if not exist "..\Files\xray-bin\xray.exe" (
  echo ❌ Xray not found at ..\Files\xray-bin\xray.exe
  pause
  exit /b 1
)

cd /d "%~dp0"

pip install -r requirements.txt || goto :pipfail
python trojan_tester.py
if %errorlevel% neq 0 goto :runfail

echo ✅ Done. Results in ..\trustlink\trustlink_trojan.txt
pause
exit /b 0

:pipfail
echo ❌ Failed to install requirements
pause
exit /b 1

:runfail
echo ❌ Tester failed. Check ..\logs\trojan_tester.log
pause
exit /b 1
