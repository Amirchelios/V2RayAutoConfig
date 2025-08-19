# ⏰ راهنمای برنامه زمانبندی خودکار V2Ray AutoConfig

## 📋 خلاصه تغییرات

### قبل از تغییرات:
- **V2Ray AutoConfig:** هر ساعت اجرا می‌شد
- **VLESS Tester:** هر ساعت اجرا می‌شد
- **Daily TrustLink Tester:** روزانه اجرا می‌شد

### بعد از تغییرات:
- **V2Ray AutoConfig:** 6 بار در روز (هر 4 ساعت)
- **VLESS Tester:** هفته‌ای یکبار (یکشنبه‌ها)
- **Daily TrustLink Tester:** روزانه (بدون تغییر)

## 🕐 برنامه زمانبندی جدید

### 1. V2Ray AutoConfig - Scheduled (6x Daily)
**فایل:** `.github/workflows/v2ray-autoconfig-scheduled.yml`

| زمان UTC | زمان تهران | توضیحات |
|----------|------------|---------|
| 02:00 | 05:30 | صبح زود |
| 06:00 | 09:30 | صبح |
| 10:00 | 13:30 | ظهر |
| 14:00 | 17:30 | عصر |
| 18:00 | 21:30 | شب |
| 22:00 | 01:30 | نیمه شب |

**مزایا:**
- کاهش فشار روی منابع GitHub Actions
- توزیع بهتر بار در طول روز
- حفظ به‌روزرسانی منظم کانفیگ‌ها

### 2. VLESS Tester - Weekly Execution
**فایل:** `.github/workflows/vless-tester-weekly.yml`

| زمان UTC | زمان تهران | روز |
|----------|------------|-----|
| 03:00 | 06:30 | یکشنبه |

**مزایا:**
- تست عمیق و کامل VLESS کانفیگ‌ها
- کاهش مصرف منابع
- نتایج با کیفیت بالاتر

### 3. Daily TrustLink Optimizer
**فایل:** `.github/workflows/daily_trustlink_optimizer.yml`

| زمان UTC | زمان تهران | روز |
|----------|------------|-----|
| 23:30 | 03:00 (روز بعد) | هر روز |

**تغییر:** از 00:00 UTC به 23:30 UTC تغییر یافت تا در ساعت 3 صبح تهران اجرا شود.

### 4. Daily TrustLink Tester
**فایل:** `.github/workflows/daily_trustlink_tester.yml`

| زمان UTC | زمان تهران | روز |
|----------|------------|-----|
| 00:00 | 03:30 | هر روز |

**بدون تغییر** - همچنان روزانه اجرا می‌شود.

## 🔧 Workflow های غیرفعال شده

### 1. V2Ray AutoConfig (ساعتانه)
**فایل:** `.github/workflows/scrip.yml`
- **وضعیت:** غیرفعال شده
- **دلیل:** جایگزین با نسخه 6 بار در روز

### 2. VLESS Tester (ساعتانه)
**فایل:** `.github/workflows/vless-tester-hourly.yml`
- **وضعیت:** غیرفعال شده
- **دلیل:** جایگزین با نسخه هفتگی

### 3. Health Check
**فایل:** `.github/workflows/health.yml`
- **وضعیت:** کاملاً حذف شده
- **دلیل:** درخواست کاربر برای حذف کامل

### 4. TrustLink Updater
**فایل:** `.github/workflows/trustlink.yml`
- **وضعیت:** حذف شده از منو
- **دلیل:** به صورت هوشمند بعد از V2Ray AutoConfig اجرا می‌شود

## 📊 مقایسه مصرف منابع

### قبل از تغییرات:
```
V2Ray AutoConfig: 24 بار در روز
VLESS Tester: 24 بار در روز
Daily TrustLink: 1 بار در روز
مجموع: 49 اجرا در روز
```

### بعد از تغییرات:
```
V2Ray AutoConfig: 6 بار در روز
VLESS Tester: 1 بار در هفته (0.14 بار در روز)
Daily TrustLink: 1 بار در روز
مجموع: 7.14 اجرا در روز
```

**صرفه‌جویی:** 85% کاهش در تعداد اجراها

## 🚀 نحوه فعال‌سازی

### 1. فعال‌سازی خودکار
Workflow های جدید به صورت خودکار فعال هستند و نیازی به تنظیم اضافی ندارند.

### 2. اجرای دستی
می‌توانید از طریق GitHub Actions هر workflow را به صورت دستی اجرا کنید:

1. به بخش **Actions** در GitHub بروید
2. Workflow مورد نظر را انتخاب کنید
3. روی **Run workflow** کلیک کنید

### 3. تست محلی
برای تست محلی:

```bash
# V2Ray AutoConfig
python Files/scrip.py

# VLESS Tester
cd vless
python vless_tester.py

# Daily TrustLink Tester
cd daily-tester
python daily_trustlink_tester.py
```

## 📈 نظارت و مانیتورینگ

### 1. GitHub Actions
- تمام اجراها در بخش Actions قابل مشاهده هستند
- لاگ‌های کامل برای هر اجرا موجود است
- وضعیت موفقیت/شکست قابل پیگیری است

### 2. فایل‌های خروجی
- **V2Ray AutoConfig:** فایل‌های کانفیگ در `configs/`
- **VLESS Tester:** فایل در `trustlink/trustlink_vless.txt`
- **Daily TrustLink:** فایل در `daily-tester/output/`

### 3. متادیتا
هر workflow متادیتای خود را ذخیره می‌کند:
- زمان آخرین اجرا
- تعداد کانفیگ‌های تولید شده
- آمار موفقیت/شکست

## 🔄 بازگشت به حالت قبلی

اگر نیاز به بازگشت به حالت قبلی داشتید:

### 1. فعال‌سازی مجدد workflow های قدیمی
```yaml
# در .github/workflows/scrip.yml
on:
  workflow_dispatch:
  schedule:
    - cron: "0 * * * *"  # هر ساعت

# در .github/workflows/vless-tester-hourly.yml  
on:
  schedule:
    - cron: "0 * * * *"  # هر ساعت
```

### 2. غیرفعال‌سازی workflow های جدید
فایل‌های جدید را حذف کنید یا schedule را کامنت کنید.

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌های GitHub Actions را بررسی کنید
2. فایل‌های خروجی را چک کنید
3. از اجرای دستی برای تست استفاده کنید

## 🎯 اهداف آینده

- [ ] اضافه کردن مانیتورینگ پیشرفته
- [ ] بهینه‌سازی بیشتر مصرف منابع
- [ ] اضافه کردن اعلان‌های خودکار
- [ ] بهبود مدیریت خطاها
