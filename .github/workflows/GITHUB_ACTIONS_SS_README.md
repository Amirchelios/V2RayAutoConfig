# 🔗 GitHub Actions - Shadowsocks Tester

## 📋 **توضیحات**

این دایرکتوری شامل workflow های GitHub Actions برای اجرای خودکار و دستی **Shadowsocks Tester** است.

## 🚀 **Workflow های موجود**

### **1. 🔄 `ss-tester-weekly.yml` - اجرای هفتگی خودکار**

#### **📅 زمان‌بندی**
- **اجرای خودکار**: هر هفته یکشنبه ساعت 2 صبح (UTC)
- **Cron**: `0 2 * * 0`

#### **🎯 ویژگی‌ها**
- اجرای خودکار بدون نیاز به دخالت کاربر
- تست کامل کانفیگ‌های Shadowsocks
- آپلود نتایج به عنوان artifact
- ثبت و ارسال خودکار نتایج به repository

#### **📊 خروجی**
- کانفیگ‌های سالم در `trustlink/trustlink_ss.txt`
- متادیتا در `trustlink/.trustlink_ss_metadata.json`
- فایل پشتیبان در `trustlink/trustlink_ss_backup.txt`
- لاگ‌ها در `logs/ss_tester.log`

### **2. 🎮 `ss-tester-manual.yml` - اجرای دستی**

#### **🔧 پارامترهای ورودی**
- **`test_mode`**: حالت تست (`single` یا `auto`)
- **`max_configs`**: حداکثر تعداد کانفیگ‌های تست شده
- **`batch_size`**: اندازه batch برای تست
- **`force_update`**: به‌روزرسانی اجباری
- **`test_specific_protocols`**: پروتکل‌های خاص برای تست
- **`log_level`**: سطح لاگ

#### **🎯 ویژگی‌ها**
- اجرای دستی با پارامترهای قابل تنظیم
- بررسی کامل محیط اجرا
- تحلیل دقیق نتایج
- آپلود artifact با retention 90 روزه

## 🔧 **نحوه استفاده**

### **🔄 اجرای هفتگی خودکار**
```yaml
# این workflow به صورت خودکار اجرا می‌شود
# نیازی به تنظیم دستی ندارد
```

### **🎮 اجرای دستی**
1. به بخش **Actions** در GitHub repository بروید
2. workflow **"🔗 Shadowsocks Tester - Manual Execution"** را انتخاب کنید
3. روی **"Run workflow"** کلیک کنید
4. پارامترهای مورد نظر را تنظیم کنید
5. روی **"Run workflow"** کلیک کنید

#### **📝 مثال پارامترها**
```yaml
test_mode: single           # تست یکباره
max_configs: 5000          # حداکثر 5000 کانفیگ
batch_size: 100            # batch 100 تایی
force_update: false         # بدون به‌روزرسانی اجباری
test_specific_protocols: all  # تست همه پروتکل‌ها
log_level: INFO            # سطح لاگ INFO
```

## 📊 **مراحل اجرا**

### **مرحله 1: 📥 Checkout repository**
- دریافت کامل repository
- تنظیم Git برای commit/push

### **مرحله 2: 🐍 Setup Python**
- نصب Python 3.9
- فعال‌سازی cache برای pip

### **مرحله 3: 🔧 Install dependencies**
- نصب وابستگی‌های Python
- نمایش لیست پکیج‌های نصب شده

### **مرحله 4: 📁 Environment validation**
- بررسی فایل‌های Xray
- بررسی فایل‌های منبع
- ایجاد دایرکتوری‌های خروجی

### **مرحله 5: 🚀 Run Shadowsocks Tester**
- اجرای برنامه اصلی
- اعمال پارامترهای ورودی
- مدیریت timeout برای حالت خودکار

### **مرحله 6: 📊 Analyze results**
- بررسی فایل‌های خروجی
- تحلیل متادیتا
- نمایش خلاصه نتایج

### **مرحله 7: 📤 Upload artifacts**
- آپلود نتایج به GitHub
- تنظیم retention period
- نام‌گذاری artifact

### **مرحله 8: 📝 Commit and push results**
- ثبت تغییرات در Git
- ارسال نتایج به repository
- پیام commit توصیفی

### **مرحله 9: 📈 Summary**
- نمایش خلاصه نهایی
- آمار تست
- اطلاعات artifact

## 📁 **فایل‌های خروجی**

### **کانفیگ‌های سالم**
- **مسیر**: `trustlink/trustlink_ss.txt`
- **محتوای**: کانفیگ‌های Shadowsocks سالم
- **فرمت**: یک کانفیگ در هر خط

### **متادیتا**
- **مسیر**: `trustlink/.trustlink_ss_metadata.json`
- **محتوای**: آمار و اطلاعات تست
- **فرمت**: JSON

### **فایل پشتیبان**
- **مسیر**: `trustlink/trustlink_ss_backup.txt`
- **محتوای**: نسخه پشتیبان از کانفیگ‌های سالم
- **فرمت**: مشابه فایل اصلی

### **لاگ‌ها**
- **مسیر**: `logs/ss_tester.log`
- **محتوای**: لاگ کامل اجرای برنامه
- **فرمت**: متن ساده

## ⚙️ **تنظیمات پیشرفته**

### **Cron Schedule**
```yaml
# هر هفته یکشنبه ساعت 2 صبح
cron: '0 2 * * 0'

# هر روز ساعت 3 صبح
cron: '0 3 * * *'

# هر 6 ساعت
cron: '0 */6 * * *'
```

### **Retention Period**
```yaml
# Artifact هفتگی: 30 روز
retention-days: 30

# Artifact دستی: 90 روز
retention-days: 90
```

### **Timeout Settings**
```yaml
# حالت خودکار: 1 ساعت
timeout 3600 python ss_tester.py --auto

# حالت یکباره: بدون timeout
python ss_tester.py
```

## 🚨 **مدیریت خطا**

### **خطاهای رایج**
- **فایل Xray یافت نشد**: بررسی مسیر `Files/xray-bin/`
- **فایل منبع یافت نشد**: بررسی وجود `configs/raw/ShadowSocks.txt`
- **خطای نصب وابستگی‌ها**: بررسی `requirements.txt`

### **راه‌حل‌ها**
1. بررسی وجود فایل‌های مورد نیاز
2. بررسی دسترسی‌های repository
3. بررسی تنظیمات secrets

## 📈 **مانیتورینگ**

### **GitHub Actions Dashboard**
- مشاهده وضعیت workflow ها
- بررسی لاگ‌های اجرا
- دانلود artifacts

### **Repository Insights**
- تاریخچه commits
- تغییرات فایل‌ها
- آمار فعالیت

## 🔄 **به‌روزرسانی**

### **تنظیمات جدید**
- اضافه کردن پارامترهای ورودی
- تغییر زمان‌بندی cron
- تنظیم retention periods

### **بهبود عملکرد**
- بهینه‌سازی مراحل اجرا
- کاهش زمان اجرا
- بهبود مدیریت خطا

## 📞 **پشتیبانی**

برای گزارش مشکلات یا پیشنهادات:
1. بررسی لاگ‌های GitHub Actions
2. بررسی فایل‌های workflow
3. ایجاد issue در repository

---

**🔗 TrustLink Shadowsocks Tester - GitHub Actions v1.0.0**
