# 🔗 TrustLink - سیستم هوشمند کانفیگ‌های قابل اعتماد

## 📋 Overview

**TrustLink** یک برنامه هوشمند و خودکار است که کانفیگ‌های سالم از فایل `Healthy.txt` را دانلود کرده و در فایل `trustlink.txt` ذخیره می‌کند. این سیستم به صورت خودکار هر ساعت اجرا می‌شود و از افزودن کانفیگ‌های تکراری جلوگیری می‌کند.

## 🎯 ویژگی‌های کلیدی

- ✅ **دانلود خودکار**: هر ساعت از فایل Healthy.txt
- ✅ **جلوگیری از تکرار**: کانفیگ‌های تکراری اضافه نمی‌شوند
- ✅ **اعتبارسنجی**: فقط کانفیگ‌های معتبر پذیرفته می‌شوند
- ✅ **Backup خودکار**: نسخه پشتیبان از فایل موجود
- ✅ **Logging کامل**: ثبت تمام عملیات
- ✅ **GitHub Actions**: اجرای خودکار در GitHub
- ✅ **متادیتای هوشمند**: ردیابی آمار و وضعیت

## 🚀 نحوه کار

### **1. دانلود خودکار**
```
https://raw.githubusercontent.com/Amirchelios/V2RayAutoConfig/refs/heads/main/configs/Healthy.txt
```
- برنامه هر ساعت این URL را بررسی می‌کند
- کانفیگ‌های جدید را دانلود می‌کند
- فقط کانفیگ‌های معتبر را پردازش می‌کند

### **2. پردازش هوشمند**
- **اعتبارسنجی**: بررسی پروتکل‌های پشتیبانی شده
- **حذف تکراری**: مقایسه با کانفیگ‌های موجود
- **ادغام**: اضافه کردن کانفیگ‌های جدید به موجود

### **3. ذخیره امن**
- **Backup**: ایجاد نسخه پشتیبان قبل از تغییر
- **نوشتن اتمیک**: استفاده از فایل موقت
- **Header**: اطلاعات کامل در ابتدای فایل

## 🔧 پروتکل‌های پشتیبانی شده

```python
SUPPORTED_PROTOCOLS = {
    "vmess://", "vless://", "trojan://", "ss://", "ssr://", 
    "hysteria://", "hysteria2://", "tuic://", "socks://"
}
```

## 📁 ساختار فایل‌ها

```
├── Files/
│   ├── trustlink.py              # برنامه اصلی TrustLink
│   └── TRUSTLINK_README.md       # این فایل
├── .github/workflows/
│   └── trustlink.yml             # ورک‌فلو GitHub Actions
├── configs/
│   ├── trustlink.txt             # فایل نهایی کانفیگ‌ها
│   ├── .trustlink_metadata.json  # متادیتای برنامه
│   └── trustlink_backup.txt      # نسخه پشتیبان
└── logs/
    └── trustlink.log             # فایل لاگ
```

## 🕐 زمان‌بندی اجرا

### **GitHub Actions**
- **هر ساعت**: `cron: "0 * * * *"`
- **هر نیم ساعت**: `cron: "*/30 * * * *"` (برای تست)
- **اجرای دستی**: از طریق `workflow_dispatch`

### **اجرای محلی**
```bash
# اجرای یک بار
python Files/trustlink.py

# اجرای مداوم (هر ساعت)
while true; do
    python Files/trustlink.py
    sleep 3600  # 1 ساعت
done
```

## 🧪 تست سیستم

### **تست 1: اجرای اولیه**
```bash
# اجرای برنامه
python Files/trustlink.py

# بررسی نتایج
ls -la configs/
cat configs/trustlink.txt
```

### **تست 2: بررسی متادیتا**
```bash
# مشاهده آمار
cat configs/.trustlink_metadata.json | python -m json.tool

# بررسی لاگ‌ها
tail -f logs/trustlink.log
```

### **تست 3: بررسی Backup**
```bash
# مقایسه فایل اصلی و پشتیبان
diff configs/trustlink.txt configs/trustlink_backup.txt
```

## 📊 آمار و گزارش‌گیری

### **متادیتای برنامه**
```json
{
  "last_update": "2024-01-01T12:00:00",
  "total_downloads": 24,
  "total_configs": 150,
  "duplicates_skipped": 45,
  "last_healthy_url": "https://raw.githubusercontent.com/...",
  "version": "1.0.0",
  "last_stats": {
    "new_added": 5,
    "duplicates_skipped": 12,
    "invalid_skipped": 2,
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

### **فایل خروجی**
```
# 🔗 TrustLink - کانفیگ‌های قابل اعتماد
# آخرین به‌روزرسانی: 2024-01-01 12:00:00
# تعداد کل: 150
# منبع: https://raw.githubusercontent.com/Amirchelios/V2RayAutoConfig/refs/heads/main/configs/Healthy.txt
#
vmess://config1...
vless://config2...
trojan://config3...
...
```

## 🔍 عیب‌یابی

### **مشکل: دانلود ناموفق**
```bash
# بررسی لاگ‌ها
tail -20 logs/trustlink.log

# بررسی اتصال اینترنت
curl -I https://raw.githubusercontent.com/Amirchelios/V2RayAutoConfig/refs/heads/main/configs/Healthy.txt
```

### **مشکل: فایل ایجاد نشد**
```bash
# بررسی مجوزها
ls -la configs/
chmod 755 configs/

# بررسی وابستگی‌ها
pip install aiohttp
```

### **مشکل: GitHub Actions ناموفق**
```bash
# بررسی Actions در GitHub
# بررسی لاگ‌های ورک‌فلو
# بررسی تنظیمات repository
```

## 🚨 نکات مهم

### **1. امنیت**
- فایل‌های موقت به صورت خودکار پاک می‌شوند
- Backup از فایل موجود قبل از تغییر
- نوشتن اتمیک برای جلوگیری از خرابی

### **2. عملکرد**
- Timeout مناسب برای HTTP requests
- مدیریت session برای بهینه‌سازی
- Logging سطح‌بندی شده

### **3. قابلیت اطمینان**
- کنترل خطا در تمام مراحل
- Fallback برای عملیات ناموفق
- بررسی وضعیت قبل از commit

## 📈 بهبودهای آینده

### **1. هوش مصنوعی**
- تشخیص کیفیت کانفیگ‌ها
- رتبه‌بندی خودکار
- فیلتر کردن کانفیگ‌های مشکوک

### **2. آمارگیری پیشرفته**
- نمودارهای آماری
- گزارش‌های دوره‌ای
- هشدارهای خودکار

### **3. مدیریت پیشرفته**
- تنظیمات قابل تغییر
- API برای کنترل خارجی
- Dashboard وب

## 🤝 مشارکت

برای بهبود TrustLink:

1. **گزارش مشکل**: Issue در GitHub
2. **پیشنهاد بهبود**: Pull Request
3. **تست**: اجرای ورک‌فلو و بررسی نتایج
4. **مستندسازی**: به‌روزرسانی این README

## 📞 پشتیبانی

### **کانال‌های ارتباطی**
- GitHub Issues
- GitHub Discussions
- Email: [your-email@example.com]

### **مستندات اضافی**
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiohttp](https://docs.aiohttp.org/)

---

## 🎉 نتیجه

TrustLink یک سیستم کامل و هوشمند برای مدیریت خودکار کانفیگ‌های قابل اعتماد است که:

- 🔄 **خودکار** اجرا می‌شود
- 🧠 **هوشمند** کانفیگ‌ها را پردازش می‌کند
- 🛡️ **امن** و قابل اعتماد است
- 📊 **قابل ردیابی** و گزارش‌گیری است
- 🚀 **آسان** در استفاده و نگهداری است

با TrustLink، کانفیگ‌های سالم شما همیشه به‌روز و بدون تکرار خواهند بود! 🎯
