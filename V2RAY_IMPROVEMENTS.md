# 🔧 بهبودهای سیستم V2Ray AutoConfig

## 📋 خلاصه تغییرات

این سند تمام بهبودهای اعمال شده بر روی سیستم V2Ray AutoConfig را توضیح می‌دهد.

## 🚀 مشکلات حل شده

### 1. مشکل Git Push در GitHub Actions
**مشکل:** خطای "Updates were rejected because the remote contains work that you do not have locally"

**راه‌حل:**
- ایجاد اسکریپت `scripts/fix_git_push.sh` برای حل مشکلات Git
- بهبود workflow در `.github/workflows/scraper.yml`
- استفاده از استراتژی‌های مختلف (rebase, merge, force push) برای حل conflicts

### 2. محدودیت تست VLESS
**مشکل:** فقط 200 کانفیگ VLESS تست می‌شد

**راه‌حل:**
- افزایش `MAX_CONFIGS_TO_TEST` به 10000 کانفیگ
- افزایش `CONCURRENT_TESTS` به 50
- افزایش `KEEP_BEST_COUNT` به 500 کانفیگ
- افزایش `batch_size` به 500

### 3. بهبود تست دسترسی از ایران
**مشکل:** تست ایران access کامل نبود

**راه‌حل:**
- اضافه کردن تست سایت‌های ایرانی (aparat.com, divar.ir, cafebazaar.ir, digikala.com)
- بهبود الگوریتم تست ایران access
- ذخیره آمار ایران access در متادیتا

### 4. دانلود از منابع مختلف
**مشکل:** فقط از فایل محلی دانلود می‌شد

**راه‌حل:**
- اضافه کردن دانلود از لینک‌های ساب مختلف:
  - V2RayRoot/V2RayConfig
  - Amirchelios/V2RayAutoConfig
  - miladtahanian/V2RayScrapeByCountry
  - 10ium/V2ray-Config

## 📁 فایل‌های جدید و تغییر یافته

### فایل‌های جدید:
1. `vless/run_vless_tester_enhanced.py` - تستر VLESS بهبود یافته
2. `scripts/fix_git_push.sh` - اسکریپت حل مشکل Git push
3. `V2RAY_IMPROVEMENTS.md` - این فایل مستندات

### فایل‌های تغییر یافته:
1. `vless/vless_tester.py` - بهبودهای مختلف
2. `.github/workflows/scraper.yml` - بهبود workflow
3. `Files/scrip.py` - بهبودهای جزئی

## 🔧 تنظیمات جدید

### تنظیمات VLESS Tester:
```python
TEST_TIMEOUT = 60  # ثانیه
CONCURRENT_TESTS = 50  # تعداد تست‌های همزمان
KEEP_BEST_COUNT = 500  # تعداد کانفیگ‌های نگه‌داری شده
MAX_CONFIGS_TO_TEST = 10000  # حداکثر کانفیگ‌های تست شده
```

### سایت‌های تست ایران:
```python
iran_test_urls = [
    "https://www.aparat.com",
    "https://divar.ir", 
    "https://www.cafebazaar.ir",
    "https://www.digikala.com",
    "https://www.sheypoor.com",
    "https://www.telewebion.com"
]
```

## 🚀 نحوه استفاده

### اجرای تستر VLESS بهبود یافته:
```bash
cd vless
python run_vless_tester_enhanced.py
```

### اجرای اسکریپت حل مشکل Git:
```bash
chmod +x scripts/fix_git_push.sh
./scripts/fix_git_push.sh
```

## 📊 آمار و گزارش‌گیری

### آمار ایران Access:
- کل کانفیگ‌های تست شده
- تعداد قابل دسترس از ایران
- تعداد سایر کانفیگ‌ها
- تعداد انتخاب شده از هر گروه

### لاگ‌های بهبود یافته:
- گزارش‌گیری دقیق‌تر از مراحل مختلف
- نمایش آمار در هر مرحله
- مدیریت خطاهای بهتر

## 🔄 Workflow بهبود یافته

### مراحل جدید:
1. اجرای scraper اصلی
2. اجرای Enhanced VLESS tester
3. حل مشکلات Git با اسکریپت اختصاصی

### بهبودهای workflow:
- مدیریت بهتر conflicts
- timeout طولانی‌تر برای تست‌ها
- گزارش‌گیری بهتر

## 🎯 نتایج مورد انتظار

### بهبودهای عملکرد:
- تست تعداد بیشتری از کانفیگ‌ها
- تشخیص بهتر کانفیگ‌های قابل دسترس از ایران
- کاهش خطاهای Git push
- افزایش پایداری سیستم

### بهبودهای کیفیت:
- کانفیگ‌های با کیفیت‌تر
- اولویت‌بندی کانفیگ‌های قابل دسترس از ایران
- مدیریت بهتر منابع

## 🔍 عیب‌یابی

### مشکلات احتمالی:
1. **Timeout در تست‌ها:** افزایش timeout در تنظیمات
2. **خطاهای دانلود:** بررسی دسترسی به لینک‌های ساب
3. **مشکلات Git:** استفاده از اسکریپت fix_git_push.sh

### لاگ‌های مفید:
- `logs/vless_tester.log` - لاگ‌های VLESS tester
- `logs/trustlink.log` - لاگ‌های trustlink
- GitHub Actions logs

## 📝 نکات مهم

1. **محدودیت‌های GitHub Actions:** تست‌ها ممکن است به دلیل محدودیت‌های GitHub Actions کند باشند
2. **مدیریت منابع:** افزایش concurrent tests ممکن است باعث overload شود
3. **پایداری:** سیستم اکنون پایدارتر است اما همچنان نیاز به نظارت دارد

## 🔮 بهبودهای آینده

1. **پشتیبانی از پروتکل‌های بیشتر**
2. **بهبود الگوریتم‌های تست**
3. **اضافه کردن API برای دسترسی به کانفیگ‌ها**
4. **بهبود UI/UX**
5. **اضافه کردن تست‌های خودکار**

---

**تاریخ آخرین به‌روزرسانی:** $(date)
**نسخه:** 2.0.0
**وضعیت:** فعال و پایدار
