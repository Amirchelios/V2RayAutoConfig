#Requires -Version 5.1

<#
.SYNOPSIS
    🔗 VMESS Tester - تستر هوشمند کانفیگ‌های VMESS
    
.DESCRIPTION
    این اسکریپت PowerShell برای اجرای تستر کانفیگ‌های VMESS طراحی شده است.
    
.PARAMETER Mode
    نوع اجرا: single (یکباره), auto (خودکار), enhanced (پیشرفته)
    
.EXAMPLE
    .\run_vmess_tester.ps1 -Mode single
    
.EXAMPLE
    .\run_vmess_tester.ps1 -Mode auto
    
.EXAMPLE
    .\run_vmess_tester.ps1 -Mode enhanced
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("single", "auto", "enhanced")]
    [string]$Mode = "single"
)

# تنظیم encoding برای نمایش فارسی
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    🔗 VMESS Tester - تستر هوشمند" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# تغییر به دایرکتوری اسکریپت
Set-Location $PSScriptRoot

# بررسی Python
Write-Host "در حال بررسی Python..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python یافت شد: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python یافت نشد"
    }
} catch {
    Write-Host "❌ Python یافت نشد! لطفاً Python را نصب کنید." -ForegroundColor Red
    Read-Host "برای ادامه Enter را فشار دهید"
    exit 1
}

Write-Host ""

# نصب وابستگی‌ها
Write-Host "در حال نصب وابستگی‌ها..." -ForegroundColor Green
try {
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ وابستگی‌ها نصب شدند" -ForegroundColor Green
    } else {
        throw "خطا در نصب وابستگی‌ها"
    }
} catch {
    Write-Host "❌ خطا در نصب وابستگی‌ها" -ForegroundColor Red
    Read-Host "برای ادامه Enter را فشار دهید"
    exit 1
}

Write-Host ""

# انتخاب نوع اجرا اگر مشخص نشده باشد
if (-not $Mode) {
    Write-Host "انتخاب نوع اجرا:" -ForegroundColor Yellow
    Write-Host "1. اجرای یکباره" -ForegroundColor White
    Write-Host "2. اجرای خودکار هر ساعت" -ForegroundColor White
    Write-Host "3. اجرای پیشرفته" -ForegroundColor White
    Write-Host ""
    
    do {
        $choice = Read-Host "انتخاب شما (1-3)"
    } while ($choice -notin @("1", "2", "3"))
    
    switch ($choice) {
        "1" { $Mode = "single" }
        "2" { $Mode = "auto" }
        "3" { $Mode = "enhanced" }
    }
}

# اجرای برنامه
Write-Host ""
switch ($Mode) {
    "single" {
        Write-Host "🚀 شروع اجرای یکباره..." -ForegroundColor Green
        python vmess_tester.py
    }
    "auto" {
        Write-Host "🔄 شروع اجرای خودکار..." -ForegroundColor Green
        python vmess_tester.py --auto
    }
    "enhanced" {
        Write-Host "⚡ شروع اجرای پیشرفته..." -ForegroundColor Green
        python run_vmess_tester_enhanced.py
    }
}

Write-Host ""
Write-Host "✅ اجرا تکمیل شد" -ForegroundColor Green
Read-Host "برای خروج Enter را فشار دهید"
