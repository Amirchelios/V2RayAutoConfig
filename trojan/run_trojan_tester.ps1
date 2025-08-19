# TrustLink Trojan Tester - PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    🔗 TrustLink Trojan Tester" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path "..\Files\xray-bin\xray.exe")) {
  Write-Host "❌ Xray not found at ..\\Files\\xray-bin\\xray.exe" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

Push-Location $PSScriptRoot

pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Failed to install requirements" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

python trojan_tester.py
if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Tester failed. Check ..\\logs\\trojan_tester.log" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

Write-Host "✅ Done. Results in ..\\trustlink\\trustlink_trojan.txt" -ForegroundColor Green
Read-Host "Press Enter to exit"

Pop-Location
