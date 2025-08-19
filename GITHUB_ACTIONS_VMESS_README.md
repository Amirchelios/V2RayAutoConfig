# 🔗 GitHub Actions برای VMESS Tester

## 📋 توضیحات
این فایل راهنما نحوه استفاده از GitHub Actions برای اجرای خودکار VMESS Tester را توضیح می‌دهد.

## 🚀 Workflow های موجود

### 1. **VMESS Tester - Weekly Execution** (`vmess-tester-weekly.yml`)
- **زمان اجرا**: هر هفته در روز یکشنبه ساعت 2 صبح
- **نوع**: اجرای خودکار
- **هدف**: تست هفتگی کانفیگ‌های VMESS

### 2. **VMESS Tester - Manual Execution** (`vmess-tester-manual.yml`)
- **زمان اجرا**: فقط اجرای دستی
- **نوع**: اجرای دستی از طریق GitHub Actions
- **هدف**: تست درخواستی کانفیگ‌های VMESS

## ⚙️ نحوه استفاده

### اجرای خودکار هفتگی
```yaml
# در فایل vmess-tester-weekly.yml
schedule:
  - cron: "0 2 * * 0"  # هر یکشنبه ساعت 2 صبح
```

### اجرای دستی
1. به بخش **Actions** در GitHub repository بروید
2. روی **VMESS Tester - Manual Execution** کلیک کنید
3. روی **Run workflow** کلیک کنید
4. تنظیمات مورد نظر را انتخاب کنید:
   - **Test mode**: سریع یا کامل
   - **Force run**: اجرای اجباری

## 🔧 تنظیمات Workflow

### Python Version
```yaml
- name: "Setup Python"
  uses: actions/setup-python@v4
  with:
    python-version: "3.11"
```

### Dependencies
```yaml
- name: "Install Dependencies"
  run: |
    python -m pip install --upgrade pip
    cd vmess
    pip install -r requirements.txt
```

### Directories
```yaml
- name: "Create Required Directories"
  run: |
    mkdir -p logs
    mkdir -p trustlink
```

## 📊 خروجی Workflow

### فایل‌های تولید شده
- `trustlink/trustlink_vmess.txt` - کانفیگ‌های سالم
- `trustlink/.trustlink_vmess_metadata.json` - متادیتا
- `logs/vmess_tester.log` - فایل لاگ

### Artifacts
- **Weekly**: `vmess-tester-logs-weekly` (نگهداری 30 روز)
- **Manual**: `vmess-tester-logs-manual-{run_number}` (نگهداری 90 روز)

## 🔄 مراحل اجرا

1. **Checkout**: دریافت کد از repository
2. **Setup Python**: نصب Python 3.11
3. **Install Dependencies**: نصب وابستگی‌ها
4. **Create Directories**: ایجاد دایرکتوری‌های مورد نیاز
5. **Check Source File**: بررسی فایل منبع VMESS
6. **Run VMESS Tester**: اجرای تستر
7. **Check Results**: بررسی نتایج
8. **Upload Logs**: آپلود لاگ‌ها
9. **Commit Results**: ثبت تغییرات
10. **Push Changes**: ارسال تغییرات
11. **Final Status**: نمایش وضعیت نهایی

## 🚨 عیب‌یابی

### خطای "Source file not found"
- اطمینان حاصل کنید که فایل `configs/raw/Vmess.txt` وجود دارد
- بررسی کنید که فایل در repository commit شده باشد

### خطای "Python dependencies"
- بررسی کنید که `requirements.txt` در دایرکتوری `vmess` وجود دارد
- اطمینان حاصل کنید که وابستگی‌ها قابل نصب هستند

### خطای "Permission denied"
- بررسی کنید که workflow دسترسی لازم برای push به repository را دارد
- اطمینان حاصل کنید که branch protection rules اجازه push را می‌دهد

## 📅 زمان‌بندی Cron

### فرمت Cron
```
minute hour day month day-of-week
```

### مثال‌ها
- `"0 2 * * 0"` - هر یکشنبه ساعت 2 صبح
- `"0 12 * * 1"` - هر دوشنبه ساعت 12 ظهر
- `"30 3 * * *"` - هر روز ساعت 3:30 صبح

## 🔐 امنیت

### Secrets
- هیچ secret خاصی نیاز نیست
- Workflow از GitHub Actions runner استفاده می‌کند

### Permissions
- `contents: write` - برای commit و push
- `actions: read` - برای اجرای workflow

## 📈 مانیتورینگ

### GitHub Actions
- به بخش **Actions** بروید
- روی workflow مورد نظر کلیک کنید
- جزئیات اجرا را مشاهده کنید

### Logs
- لاگ‌ها در هر اجرا آپلود می‌شوند
- می‌توانید لاگ‌ها را دانلود و بررسی کنید

## 🤝 مشارکت

برای بهبود workflow ها:
1. کد را بررسی کنید
2. پیشنهادات خود را ارائه دهید
3. در صورت یافتن باگ، آن را گزارش دهید

## 📄 مجوز

این workflow ها تحت مجوز MIT منتشر شده‌اند.
