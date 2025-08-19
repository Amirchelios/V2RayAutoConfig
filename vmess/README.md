# 🔗 VMESS Tester - تستر هوشمند کانفیگ‌های VMESS

## 📋 توضیحات
این برنامه یک تستر هوشمند برای کانفیگ‌های VMESS است که:
- کانفیگ‌های VMESS را از فایل `../configs/raw/Vmess.txt` می‌خواند
- آن‌ها را تست می‌کند تا سالم بودنشان را بررسی کند
- کانفیگ‌های سالم را در فایل `../trustlink/trustlink_vmess.txt` ذخیره می‌کند
- به صورت خودکار هر ساعت اجرا می‌شود

## 🚀 نصب و راه‌اندازی

### 1. نصب وابستگی‌ها
```bash
cd vmess
pip install -r requirements.txt
```

### 2. اجرای یکباره
```bash
cd vmess
python vmess_tester.py
```

### 3. اجرای خودکار هر ساعت
```bash
cd vmess
python vmess_tester.py --auto
```

### 4. اجرای پیشرفته
```bash
cd vmess
python run_vmess_tester_enhanced.py
```

## 📁 ساختار فایل‌ها

- `vmess_tester.py` - فایل اصلی برنامه
- `run_vmess_tester_enhanced.py` - اجراکننده پیشرفته
- `requirements.txt` - وابستگی‌های مورد نیاز
- `README.md` - این فایل راهنما
- `../trustlink/trustlink_vmess.txt` - کانفیگ‌های VMESS سالم
- `../trustlink/.trustlink_vmess_metadata.json` - متادیتای برنامه
- `../trustlink/trustlink_vmess_backup.txt` - فایل پشتیبان
- `../logs/vmess_tester.log` - فایل لاگ

## ⚙️ تنظیمات

### تنظیمات تست
- `TEST_TIMEOUT`: 60 ثانیه (timeout برای تست)
- `CONCURRENT_TESTS`: 50 (تعداد تست‌های همزمان)
- `KEEP_BEST_COUNT`: 500 (تعداد کانفیگ‌های سالم نگه‌داری شده)

### تنظیمات فایل‌ها
- `VMESS_SOURCE_FILE`: `../configs/raw/Vmess.txt` (فایل منبع)
- `TRUSTLINK_VMESS_FILE`: `../trustlink/trustlink_vmess.txt` (فایل خروجی)

## 🔧 نحوه کارکرد

### 1. بارگذاری کانفیگ‌ها
برنامه کانفیگ‌های VMESS را از فایل منبع بارگذاری می‌کند

### 2. تست اتصال
هر کانفیگ VMESS را تست می‌کند تا سالم بودنش را بررسی کند

### 3. انتخاب بهترین‌ها
بهترین کانفیگ‌ها را بر اساس latency انتخاب می‌کند

### 4. ذخیره‌سازی
کانفیگ‌های سالم را در فایل خروجی ذخیره می‌کند

### 5. اجرای خودکار
هر ساعت به صورت خودکار اجرا می‌شود

## 📊 خروجی

### فایل trustlink_vmess.txt
```
# فایل کانفیگ‌های VMESS سالم - TrustLink VMESS
# آخرین به‌روزرسانی: 2024-01-01 12:00:00
# تعداد کل کانفیگ‌ها: 45
# ==================================================

vmess://uuid@server:port?params...
vmess://uuid@server:port?params...
...
```

### متادیتا
```json
{
  "last_update": "2024-01-01T12:00:00",
  "total_tests": 15,
  "total_configs": 45,
  "working_configs": 45,
  "failed_configs": 0,
  "last_vmess_source": "../configs/raw/Vmess.txt",
  "version": "1.0.0"
}
```

## 🚨 عیب‌یابی

### خطای "فایل منبع VMESS یافت نشد"
- اطمینان حاصل کنید که فایل `../configs/raw/Vmess.txt` وجود دارد

### خطای "timeout"
- تنظیمات `TEST_TIMEOUT` را افزایش دهید
- تعداد `CONCURRENT_TESTS` را کاهش دهید

### خطای "Xray یافت نشد"
- اطمینان حاصل کنید که Xray در مسیر `../Files/xray-bin` نصب شده است

## 🔄 اجرای خودکار

### Windows
```batch
cd vmess
python vmess_tester.py --auto
```

### Linux/Mac
```bash
cd vmess
python3 vmess_tester.py --auto
```

## 📈 ویژگی‌های پیشرفته

- تست همزمان 50 کانفیگ
- پشتیبانی از Xray برای تست واقعی
- ذخیره خودکار نتایج
- ایجاد فایل پشتیبان
- لاگ کامل عملیات
- متادیتای برنامه

## 🤝 مشارکت

برای بهبود برنامه، لطفاً:
1. کد را بررسی کنید
2. پیشنهادات خود را ارائه دهید
3. در صورت یافتن باگ، آن را گزارش دهید

## 📄 مجوز

این برنامه تحت مجوز MIT منتشر شده است.
