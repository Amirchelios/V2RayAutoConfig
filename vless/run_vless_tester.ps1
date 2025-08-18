# VLESS Tester - TrustLink PowerShell Script
# Set console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    🔗 VLESS Tester - TrustLink" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "انتخاب کنید:" -ForegroundColor Green
Write-Host "1. اجرای یکباره" -ForegroundColor White
Write-Host "2. اجرای خودکار هر ساعت" -ForegroundColor White
Write-Host "3. خروج" -ForegroundColor White
Write-Host ""

$choice = Read-Host "انتخاب شما (1-3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 اجرای یکباره VLESS Tester..." -ForegroundColor Green
        python vless_tester.py
        Read-Host "برای ادامه Enter را فشار دهید"
    }
    "2" {
        Write-Host ""
        Write-Host "⏰ اجرای خودکار هر ساعت..." -ForegroundColor Green
        Write-Host "برای توقف برنامه Ctrl+C را فشار دهید" -ForegroundColor Yellow
        python vless_tester.py --auto
    }
    "3" {
        Write-Host ""
        Write-Host "خروج از برنامه..." -ForegroundColor Red
        exit
    }
    default {
        Write-Host ""
        Write-Host "❌ انتخاب نامعتبر!" -ForegroundColor Red
        Read-Host "برای ادامه Enter را فشار دهید"
    }
}
