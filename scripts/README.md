# 🛠️ Scripts - ابزارهای اجراکننده محلی

این دایرکتوری شامل ابزارهای اجراکننده محلی برای برنامه‌های زمانبندی شده V2Ray AutoConfig است.

## 📁 فایل‌های موجود

### اجراکننده اصلی
- **`run_scheduled_tasks.py`** - اجراکننده اصلی برنامه‌های زمانبندی شده
- **`requirements.txt`** - وابستگی‌های Python

### فایل‌های اجرا
- **`start_scheduler.bat`** - اجراکننده ویندوز
- **`start_scheduler.sh`** - اجراکننده لینوکس/مک

## 🚀 نحوه استفاده

### 1. اجرای scheduler (پیشنهادی)
```bash
# ویندوز
scripts\start_scheduler.bat

# لینوکس/مک
./scripts/start_scheduler.sh
```

### 2. اجرای دستی
```bash
# نصب dependencies
pip install -r scripts/requirements.txt

# اجرای scheduler
python scripts/run_scheduled_tasks.py schedule

# اجرای دستی برنامه‌ها
python scripts/run_scheduled_tasks.py v2ray    # V2Ray AutoConfig
python scripts/run_scheduled_tasks.py vless    # VLESS Tester
python scripts/run_scheduled_tasks.py daily    # Daily TrustLink
```

## ⏰ برنامه زمانبندی

### V2Ray AutoConfig
- **تعداد:** 6 بار در روز
- **ساعات:** 05:30, 09:30, 13:30, 17:30, 21:30, 01:30 (تهران)

### VLESS Tester
- **تعداد:** هفته‌ای یکبار
- **زمان:** یکشنبه‌ها ساعت 06:30 (تهران)

### Daily TrustLink Optimizer
- **تعداد:** روزانه
- **زمان:** هر روز ساعت 03:00 (تهران)

### Daily TrustLink Tester
- **تعداد:** روزانه
- **زمان:** هر روز ساعت 03:30 (تهران)

## 📊 نظارت

### لاگ‌ها
- **`scheduled_tasks.log`** - لاگ کامل اجراها
- **خروجی کنسول** - نمایش زنده وضعیت

### وضعیت
- ✅ موفقیت
- ❌ خطا
- ⏰ timeout
- 🕐 زمان‌بندی

## 🔧 تنظیمات

### تغییر زمان‌بندی
فایل `run_scheduled_tasks.py` را ویرایش کنید:

```python
# V2Ray AutoConfig - تغییر ساعات
schedule.every().day.at("05:30").do(self.run_v2ray_autoconfig)

# VLESS Tester - تغییر روز و ساعت
schedule.every().sunday.at("06:30").do(self.run_vless_tester)

# Daily TrustLink - تغییر ساعت
schedule.every().day.at("03:30").do(self.run_daily_trustlink_tester)
```

### تغییر timeout
```python
# V2Ray AutoConfig
timeout=1800  # 30 دقیقه

# VLESS Tester
timeout=3600  # 60 دقیقه

# Daily TrustLink
timeout=1800  # 30 دقیقه
```

## 🛠️ عیب‌یابی

### مشکل: Python یافت نشد
```bash
# بررسی نسخه Python
python --version
python3 --version

# نصب Python
# ویندوز: https://python.org
# لینوکس: sudo apt install python3
# مک: brew install python3
```

### مشکل: Dependencies نصب نشد
```bash
# نصب دستی
pip install schedule pathlib2

# یا
pip install -r requirements.txt
```

### مشکل: Permission denied (لینوکس/مک)
```bash
# دادن مجوز اجرا
chmod +x scripts/start_scheduler.sh
```

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌ها را بررسی کنید
2. اجرای دستی را تست کنید
3. تنظیمات را بررسی کنید
4. GitHub Issues را چک کنید
