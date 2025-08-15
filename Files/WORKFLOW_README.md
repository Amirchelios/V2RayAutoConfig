# 🔄 GitHub Actions Workflows - راهنمای زمان‌بندی

## 📋 خلاصه تغییرات

سیستم workflow های GitHub Actions بهینه شده تا به صورت برنامه‌ریزی شده و منظم اجرا شوند.

## 🕐 زمان‌بندی جدید

### 1. **V2Ray AutoConfig (Workflow اصلی)**
- **فایل**: `.github/workflows/scrip.yml`
- **زمان اجرا**: هر 2 ساعت در دقیقه 0 (UTC)
- **cron**: `0 */2 * * *`
- **وظایف**:
  1. اجرای اسکریپت اصلی `Files/scrip.py`
  2. جمع‌آوری و تست کانفیگ‌ها
  3. به‌روزرسانی README.md
  4. **اجرای TrustLink** (بعد از اتمام مرحله 1)

### 2. **Scraper (جمع‌آوری کانفیگ‌های خام)**
- **فایل**: `.github/workflows/scraper.yml`
- **زمان اجرا**: هر 2 ساعت در دقیقه 0 (UTC)
- **cron**: `0 */2 * * *`
- **وظایف**:
  - جمع‌آوری کانفیگ‌های خام از منابع مختلف
  - تست سلامت کانفیگ‌ها
  - ذخیره در دایرکتوری `configs/`

### 3. **TrustLink (غیرفعال شده)**
- **فایل**: `.github/workflows/trustlink.yml`
- **وضعیت**: غیرفعال (DEPRECATED)
- **دلیل**: حالا در workflow اصلی ادغام شده
- **نکته**: فقط برای اجرای دستی قابل استفاده است

### 4. **Health Check**
- **فایل**: `.github/workflows/health.yml`
- **زمان اجرا**: هر ساعت
- **وضعیت**: فعال (برای تست‌های اضافی)

## 🔄 ترتیب اجرا

```
🕐 هر 2 ساعت:
├── 1. V2Ray AutoConfig (scrip.yml)
│   ├── اجرای اسکریپت اصلی
│   ├── جمع‌آوری کانفیگ‌ها
│   ├── تست سلامت
│   └── 2. TrustLink (در همان workflow)
│       ├── دانلود از Healthy.txt
│       ├── ذخیره در trustlink.txt
│       └── commit و push
└── 3. Scraper (scraper.yml)
    ├── جمع‌آوری کانفیگ‌های خام
    └── commit و push
```

## 📊 مزایای سیستم جدید

### ✅ **هماهنگی زمانی**
- همه workflow ها در زمان‌های مشخص اجرا می‌شوند
- جلوگیری از تداخل و کانفلیکت

### ✅ **وابستگی منطقی**
- TrustLink فقط بعد از اتمام V2Ray AutoConfig اجرا می‌شود
- اطمینان از وجود فایل‌های مورد نیاز

### ✅ **بهینه‌سازی منابع**
- کاهش تعداد اجراهای همزمان
- استفاده بهتر از GitHub Actions minutes

### ✅ **نگهداری آسان**
- یک workflow اصلی برای مدیریت
- کاهش پیچیدگی

## 🛠️ تنظیمات پیشرفته

### Environment Variables
```bash
# در workflow اصلی
ENABLE_HEALTH_CHECK: '1'
DISABLE_CONFIG_FILTERS: '1'
HEALTH_CHECK_ALL: '1'
KEEP_UNTESTED_ON_HEALTH: '1'
```

### Concurrency Control
```yaml
concurrency:
  group: v2ray-autoconfig-${{ github.ref }}
  cancel-in-progress: false
```

## 📝 نکات مهم

1. **زمان UTC**: همه زمان‌ها بر اساس UTC هستند
2. **Dependency**: TrustLink وابسته به V2Ray AutoConfig است
3. **Error Handling**: در صورت خطا در مرحله اول، مرحله دوم اجرا نمی‌شود
4. **Manual Trigger**: همه workflow ها قابل اجرای دستی هستند

## 🔍 عیب‌یابی

### اگر workflow اجرا نمی‌شود:
1. بررسی کنید که cron syntax صحیح باشد
2. اطمینان حاصل کنید که workflow در branch اصلی فعال است
3. بررسی کنید که permissions صحیح تنظیم شده باشند

### اگر TrustLink کار نمی‌کند:
1. بررسی کنید که V2Ray AutoConfig موفقیت‌آمیز اجرا شده باشد
2. فایل `Files/trustlink.py` موجود باشد
3. وابستگی‌های Python نصب شده باشند

## 📞 پشتیبانی

برای گزارش مشکلات یا پیشنهادات:
- از بخش Issues در GitHub استفاده کنید
- workflow ها را به صورت دستی تست کنید
- لاگ‌های GitHub Actions را بررسی کنید

---

**آخرین به‌روزرسانی**: 2025-08-16
**وضعیت**: فعال و بهینه شده ✅
