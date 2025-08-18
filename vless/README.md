# 🔗 VLESS Tester - تستر هوشمند کانفیگ‌های VLESS

## 📋 توضیحات
این برنامه یک تستر هوشمند برای کانفیگ‌های VLESS است که:
- کانفیگ‌های VLESS را از فایل `../configs/raw/Vless.txt` می‌خواند
- آن‌ها را تست می‌کند تا سالم بودنشان را بررسی کند
- کانفیگ‌های سالم را در فایل `../trustlink/trustlink_vless.txt` ذخیره می‌کند
- به صورت خودکار هر ساعت اجرا می‌شود

## 🚀 نصب و راه‌اندازی

### 1. نصب وابستگی‌ها
```bash
cd vless
pip install -r requirements.txt
```

### 2. اجرای یکباره
```bash
cd vless
python vless_tester.py
```

### 3. اجرای خودکار هر ساعت
```bash
cd vless
python vless_tester.py --auto
```

## 📁 ساختار فایل‌ها

- `vless_tester.py` - فایل اصلی برنامه
- `requirements.txt` - وابستگی‌های مورد نیاز
- `README.md` - این فایل راهنما
- `../trustlink/trustlink_vless.txt` - کانفیگ‌های VLESS سالم
- `../trustlink/.trustlink_vless_metadata.json` - متادیتای برنامه
- `../trustlink/trustlink_vless_backup.txt` - فایل پشتیبان
- `../logs/vless_tester.log` - فایل لاگ

## ⚙️ تنظیمات

### تنظیمات تست
- `TEST_TIMEOUT`: 15 ثانیه (timeout برای تست)
- `CONCURRENT_TESTS`: 10 (تعداد تست‌های همزمان)
- `KEEP_BEST_COUNT`: 50 (تعداد کانفیگ‌های سالم نگه‌داری شده)

### تنظیمات فایل‌ها
- `VLESS_SOURCE_FILE`: `../configs/raw/Vless.txt` (فایل منبع)
- `TRUSTLINK_VLESS_FILE`: `../trustlink/trustlink_vless.txt` (فایل خروجی)

## 🔧 نحوه کارکرد

### 1. بارگذاری کانفیگ‌ها
برنامه کانفیگ‌های VLESS را از فایل منبع بارگذاری می‌کند

### 2. تست اتصال
هر کانفیگ VLESS را تست می‌کند تا سالم بودنش را بررسی کند

### 3. انتخاب بهترین‌ها
بهترین کانفیگ‌ها را بر اساس latency انتخاب می‌کند

### 4. ذخیره‌سازی
کانفیگ‌های سالم را در فایل خروجی ذخیره می‌کند

### 5. اجرای خودکار
هر ساعت به صورت خودکار اجرا می‌شود

## 📊 خروجی

### فایل trustlink_vless.txt
```
# فایل کانفیگ‌های VLESS سالم - TrustLink VLESS
# آخرین به‌روزرسانی: 2024-01-01 12:00:00
# تعداد کل کانفیگ‌ها: 45
# ==================================================

vless://uuid@server:port?params...
vless://uuid@server:port?params...
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
  "last_vless_source": "../configs/raw/Vless.txt",
  "version": "1.0.0"
}
```

## 🚨 عیب‌یابی

### خطای "فایل منبع VLESS یافت نشد"
- اطمینان حاصل کنید که فایل `../configs/raw/Vless.txt` وجود دارد

### خطای "timeout"
- برنامه بیش از 5 دقیقه طول کشیده است
- اینترنت خود را بررسی کنید

### خطای "Session"
- مشکل در اتصال شبکه
- firewall را بررسی کنید

## 📝 لاگ‌ها

تمام فعالیت‌های برنامه در فایل `../logs/vless_tester.log` ثبت می‌شود:

```
2024-01-01 12:00:00 - INFO - 🚀 راه‌اندازی TrustLink VLESS Tester
2024-01-01 12:00:01 - INFO - 6684 کانفیگ VLESS معتبر از فایل منبع بارگذاری شد
2024-01-01 12:00:02 - INFO - شروع تست 6684 کانفیگ VLESS...
2024-01-01 12:01:00 - INFO - تست VLESS کامل شد: 45 کانفیگ موفق از 6684
2024-01-01 12:01:01 - INFO - ✅ به‌روزرسانی VLESS با موفقیت انجام شد
```

## 🔄 اجرای خودکار

برای اجرای خودکار هر ساعت:

```bash
# در Windows
cd vless
python vless_tester.py --auto

# در Linux/Mac (background)
cd vless
nohup python vless_tester.py --auto > /dev/null 2>&1 &
```

## 📈 نظارت

برای نظارت بر عملکرد برنامه:

```bash
# مشاهده لاگ‌ها
cd vless
tail -f ../logs/vless_tester.log

# بررسی وضعیت
cd vless
python -c "
import json
with open('../trustlink/.trustlink_vless_metadata.json', 'r') as f:
    data = json.load(f)
    print(f'آخرین به‌روزرسانی: {data.get(\"last_update\")}')
    print(f'تعداد کل تست‌ها: {data.get(\"total_tests\")}')
    print(f'کانفیگ‌های سالم: {data.get(\"working_configs\")}')
"
```

## 🚀 GitHub Actions

برای اجرای خودکار در GitHub Actions، فایل‌های workflow در `.github/workflows/` قرار دارند:

- `vless-tester-hourly.yml` - اجرای ساعتی
- `vless-tester-daily.yml` - اجرای روزانه

## 🤝 مشارکت

برای بهبود برنامه:
1. Issues را گزارش دهید
2. Pull Request ارسال کنید
3. پیشنهادات خود را مطرح کنید

## 📄 مجوز

این برنامه تحت مجوز MIT منتشر شده است.
