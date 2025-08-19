# TrustLink Shadowsocks Tester - PowerShell Script
# Set console encoding for Persian text
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    🔗 TrustLink Shadowsocks Tester" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 بررسی محیط..." -ForegroundColor Green

# Check if Xray exists
if (-not (Test-Path "..\Files\xray-bin\xray.exe")) {
    Write-Host "❌ فایل Xray یافت نشد!" -ForegroundColor Red
    Write-Host "📁 مسیر مورد انتظار: ..\Files\xray-bin\xray.exe" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "برای ادامه Enter را فشار دهید"
    exit 1
}

# Check if source file exists
if (-not (Test-Path "..\configs\raw\ShadowSocks.txt")) {
    Write-Host "❌ فایل منبع Shadowsocks یافت نشد!" -ForegroundColor Red
    Write-Host "📁 مسیر مورد انتظار: ..\configs\raw\ShadowSocks.txt" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "برای ادامه Enter را فشار دهید"
    exit 1
}

Write-Host "✅ محیط آماده است" -ForegroundColor Green
Write-Host ""

Write-Host "🔧 نصب وابستگی‌ها..." -ForegroundColor Green
try {
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "خطا در نصب وابستگی‌ها"
    }
} catch {
    Write-Host "❌ خطا در نصب وابستگی‌ها" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "برای ادامه Enter را فشار دهید"
    exit 1
}

Write-Host "✅ وابستگی‌ها نصب شدند" -ForegroundColor Green
Write-Host ""

Write-Host "🚀 شروع تست کانفیگ‌های Shadowsocks..." -ForegroundColor Green
Write-Host "📊 حالت: تست یکباره" -ForegroundColor Yellow
Write-Host ""

try {
    python ss_tester.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ تست با موفقیت تکمیل شد!" -ForegroundColor Green
        Write-Host "📁 نتایج در: ..\trustlink\trustlink_ss.txt" -ForegroundColor Cyan
        Write-Host "📊 متادیتا در: ..\trustlink\.trustlink_ss_metadata.json" -ForegroundColor Cyan
        Write-Host "📝 لاگ‌ها در: ..\logs\ss_tester.log" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "❌ خطا در اجرای تست" -ForegroundColor Red
        Write-Host "📝 لطفاً لاگ‌ها را بررسی کنید" -ForegroundColor Yellow
    }
} catch {
    Write-Host ""
    Write-Host "❌ خطا در اجرای تست" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "📝 لطفاً لاگ‌ها را بررسی کنید" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "برای ادامه Enter را فشار دهید"
