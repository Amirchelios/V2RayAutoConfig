# 🔗 Shadowsocks Tester - TrustLink SS

## 📋 **توضیحات**

برنامه هوشمند برای تست و ذخیره کانفیگ‌های **Shadowsocks (SS)** سالم. این برنامه دقیقاً مثل VLESS و VMESS tester عمل می‌کنه و کانفیگ‌ها رو در 4 مرحله تست می‌کنه تا بهترین کیفیت رو تضمین کنه.

## 🚀 **ویژگی‌های کلیدی**

- **تست 4 مرحله‌ای**: اتصال → دسترسی ایران → شبکه‌های اجتماعی → سرعت دانلود
- **پردازش batch**: تست 50 تا 50 تا برای جلوگیری از overload
- **پشتیبانی از Xray**: تست واقعی با استفاده از Xray
- **ذخیره نتایج جزئی**: حفظ پیشرفت در صورت timeout یا خطا
- **مدیریت متادیتا**: ثبت آمار کامل تست‌ها
- **حالت خودکار**: اجرای خودکار هر ساعت

## 📁 **ساختار فایل‌ها**

```
ss/
├── ss_tester.py          # برنامه اصلی
├── requirements.txt       # وابستگی‌ها
├── README.md             # این فایل
├── __init__.py           # پکیج Python
├── run_ss_tester.bat     # اسکریپت Windows
├── run_ss_tester.ps1     # اسکریپت PowerShell
└── .gitignore            # فایل‌های نادیده گرفته شده
```

## 🔧 **نصب و راه‌اندازی**

### **1. نصب وابستگی‌ها**
```bash
cd ss
pip install -r requirements.txt
```

### **2. بررسی Xray**
اطمینان حاصل کنید که فایل‌های Xray در مسیر `../Files/xray-bin/` موجود هستند:
- Windows: `xray.exe`
- Linux/Mac: `xray`

### **3. اجرا**
```bash
# اجرای یکباره
python ss_tester.py

# اجرای خودکار (هر ساعت)
python ss_tester.py --auto
```

## 📊 **مراحل تست**

### **مرحله 1: تست اتصال اولیه**
- تست اتصال TCP به سرور
- تست HTTP/HTTPS
- تست با Xray (در صورت نیاز)
- فیلتر کردن کانفیگ‌های سالم

### **مرحله 2: تست دسترسی ایران**
- تست دسترسی به سایت‌های ایرانی
- پردازش batch 50 تایی
- فقط کانفیگ‌های قبول شده به مرحله بعد می‌روند

### **مرحله 3: تست شبکه‌های اجتماعی**
- تست دسترسی به YouTube
- تست دسترسی به Instagram  
- تست دسترسی به Telegram
- پردازش batch 50 تایی
- حداقل یکی از پلتفرم‌ها باید قابل دسترسی باشد

### **مرحله 4: تست سرعت دانلود**
- تست سرعت دانلود واقعی
- پردازش batch 50 تایی
- فقط کانفیگ‌های با سرعت کافی قبول می‌شوند

## 📁 **فایل‌های خروجی**

### **فایل اصلی**
- `../trustlink/trustlink_ss.txt` - کانفیگ‌های سالم

### **فایل‌های پشتیبان**
- `../trustlink/trustlink_ss_backup.txt` - نسخه پشتیبان
- `../trustlink/.trustlink_ss_metadata.json` - متادیتا و آمار

### **لاگ‌ها**
- `../logs/ss_tester.log` - لاگ کامل برنامه

## ⚙️ **تنظیمات**

### **تنظیمات تست**
```python
TEST_TIMEOUT = 60              # timeout تست (ثانیه)
CONCURRENT_TESTS = 50          # تعداد تست‌های همزمان
KEEP_BEST_COUNT = 500         # تعداد کانفیگ‌های نگه‌داری شده
MAX_CONFIGS_TO_TEST = 10000   # حداکثر تعداد کانفیگ‌های تست شده
```

### **تنظیمات batch**
```python
batch_size = 50               # اندازه هر batch
```

### **تنظیمات timeout**
```python
DOWNLOAD_TEST_TIMEOUT = 2     # timeout تست سرعت (ثانیه)
```

## 🔍 **فرمت کانفیگ Shadowsocks**

برنامه از فرمت استاندارد Shadowsocks پشتیبانی می‌کند:

```
ss://base64(method:password@server:port)
```

### **مثال‌ها**
```
ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@server.com:8388
ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@192.168.1.1:1080
```

## 📈 **آمار و گزارش‌گیری**

### **متادیتا**
```json
{
  "last_update": "2024-01-01T12:00:00",
  "total_tests": 1000,
  "total_configs": 500,
  "working_configs": 450,
  "failed_configs": 550,
  "test_statistics": {
    "connection_ok": 800,
    "iran_access_ok": 600,
    "social_media_ok": 500,
    "download_speed_ok": 450
  }
}
```

### **لاگ‌ها**
```
2024-01-01 12:00:00 - INFO - شروع تست 1000 کانفیگ Shadowsocks
2024-01-01 12:00:01 - INFO - مرحله 1: تست اتصال اولیه
2024-01-01 12:00:30 - INFO - تست اتصال 100/1000 کانفیگ Shadowsocks تکمیل شد
...
```

## 🚨 **مدیریت خطا**

### **خطاهای رایج**
- **Xray یافت نشد**: بررسی مسیر `../Files/xray-bin/`
- **فایل منبع یافت نشد**: بررسی وجود `../configs/raw/ShadowSocks.txt`
- **خطای اتصال**: بررسی دسترسی به اینترنت و فایروال

### **ذخیره نتایج جزئی**
در صورت timeout یا خطا، برنامه نتایج جزئی را ذخیره می‌کند:
1. **Speed OK** - کانفیگ‌های قبول شده در تست سرعت
2. **Social Media OK** - کانفیگ‌های قبول شده در تست شبکه‌های اجتماعی
3. **Iran Access OK** - کانفیگ‌های قبول شده در تست دسترسی ایران
4. **Connection OK** - کانفیگ‌های قبول شده در تست اتصال

## 🔄 **حالت خودکار**

### **اجرای هر ساعت**
```bash
python ss_tester.py --auto
```

### **برنامه‌ریزی**
- هر ساعت: `schedule.every().hour.do(run_test)`
- اجرای اولیه: بلافاصله پس از شروع
- حلقه اصلی: بررسی هر دقیقه

## 📱 **تست شبکه‌های اجتماعی**

### **پلتفرم‌های تست شده**
- **YouTube**: `https://www.youtube.com`
- **Instagram**: `https://www.instagram.com`
- **Telegram**: `https://web.telegram.org`

### **معیار قبولی**
کانفیگ باید حداقل به یکی از پلتفرم‌های بالا دسترسی داشته باشد.

## ⚡ **تست سرعت دانلود**

### **URL های تست**
- Cloudflare Speed Test
- Hetzner Speed Test
- SoftLayer Speed Test

### **معیار قبولی**
دانلود حداقل 1MB در کمتر از 2 ثانیه

## 🛠️ **توسعه و سفارشی‌سازی**

### **اضافه کردن تست جدید**
```python
async def test_new_feature(self, config: str) -> bool:
    """تست ویژگی جدید"""
    try:
        # کد تست
        return True
    except Exception as e:
        logging.debug(f"خطا در تست ویژگی جدید: {e}")
        return False
```

### **تغییر تنظیمات**
```python
# در ابتدای فایل ss_tester.py
BATCH_SIZE = 100              # تغییر اندازه batch
NEW_TEST_TIMEOUT = 30         # تغییر timeout
```

## 📞 **پشتیبانی**

برای گزارش مشکلات یا پیشنهادات:
1. بررسی لاگ‌ها در `../logs/ss_tester.log`
2. بررسی فایل‌های متادیتا
3. تست با تعداد کمتری کانفیگ

## 📄 **لایسنس**

این برنامه بخشی از پروژه TrustLink است و تحت همان لایسنس منتشر می‌شود.

---

**🔗 TrustLink Shadowsocks Tester v1.0.0**
