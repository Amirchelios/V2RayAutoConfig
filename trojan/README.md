# 🔗 Trojan Tester - TrustLink

## 📋 توضیحات
برنامه تست کانفیگ‌های Trojan مانند VLESS/VMESS/SS با 4 مرحله تست: اتصال → دسترسی ایران → شبکه‌های اجتماعی → سرعت دانلود.

## 🚀 نحوه اجرا
```bash
cd trojan
pip install -r requirements.txt
python trojan_tester.py
```

برای حالت خودکار (هر ساعت):
```bash
python trojan_tester.py --auto
```

## 📁 خروجی‌ها
- `../trustlink/trustlink_trojan.txt`
- `../trustlink/.trustlink_trojan_metadata.json`
- `../logs/trojan_tester.log`

## ⚙️ پیش‌نیاز Xray
فایل‌های Xray در `../Files/xray-bin/` موجود باشند (Windows: xray.exe، Linux/Mac: xray).

## 🧪 مراحل تست
- اتصال اولیه با Xray (SOCKS proxy)
- دسترسی ایران (batch 50)
- دسترسی به YouTube/Instagram/Telegram (batch 50)
- سرعت دانلود (batch 50)
