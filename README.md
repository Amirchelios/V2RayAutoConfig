# 🔗 TrustLink V2Ray AutoConfig

## 📋 **توضیحات**

پروژه هوشمند برای تست و ذخیره کانفیگ‌های **V2Ray** سالم. این پروژه شامل **3 برنامه tester** است که کانفیگ‌ها را در **4 مرحله** تست می‌کنند تا بهترین کیفیت را تضمین کنند.

## 🚀 **برنامه‌های Tester موجود**

### **1. 🔗 VLESS Tester**
- **دایرکتوری**: `vless/`
- **فایل اصلی**: `vless_tester.py`
- **پروتکل**: VLESS (`vless://`)
- **ویژگی**: تست 4 مرحله‌ای + شبکه‌های اجتماعی

### **2. 🔗 VMESS Tester**
- **دایرکتوری**: `vmess/`
- **فایل اصلی**: `vmess_tester.py`
- **پروتکل**: VMESS (`vmess://`)
- **ویژگی**: تست 4 مرحله‌ای + شبکه‌های اجتماعی

### **3. 🔗 Shadowsocks Tester**
- **دایرکتوری**: `ss/`
- **فایل اصلی**: `ss_tester.py`
- **پروتکل**: Shadowsocks (`ss://`)
- **ویژگی**: تست 4 مرحله‌ای + شبکه‌های اجتماعی

## 📊 **مراحل تست (همه Tester ها)**

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

## 🔧 **نصب و راه‌اندازی**

### **1. نصب وابستگی‌ها**
```bash
# برای VLESS Tester
cd vless
pip install -r requirements.txt

# برای VMESS Tester
cd vmess
pip install -r requirements.txt

# برای Shadowsocks Tester
cd ss
pip install -r requirements.txt
```

### **2. بررسی Xray**
اطمینان حاصل کنید که فایل‌های Xray در مسیر `Files/xray-bin/` موجود هستند:
- Windows: `xray.exe`
- Linux/Mac: `xray`

### **3. اجرا**
```bash
# VLESS Tester
cd vless
python vless_tester.py

# VMESS Tester
cd vmess
python vmess_tester.py

# Shadowsocks Tester
cd ss
python ss_tester.py
```

## 📁 **ساختار پروژه**

```
V2RayAutoConfig/
├── vless/                    # VLESS Tester
│   ├── vless_tester.py
│   ├── run_vless_tester_enhanced.py
│   ├── requirements.txt
│   ├── README.md
│   └── ...
├── vmess/                    # VMESS Tester
│   ├── vmess_tester.py
│   ├── run_vmess_tester_enhanced.py
│   ├── requirements.txt
│   ├── README.md
│   └── ...
├── ss/                       # Shadowsocks Tester
│   ├── ss_tester.py
│   ├── run_ss_tester_enhanced.py
│   ├── requirements.txt
│   ├── README.md
│   └── ...
├── .github/workflows/        # GitHub Actions
│   ├── vless-tester-weekly.yml
│   ├── vmess-tester-weekly.yml
│   ├── ss-tester-weekly.yml
│   ├── vless-tester-manual.yml
│   ├── vmess-tester-manual.yml
│   ├── ss-tester-manual.yml
│   └── ...
├── configs/                  # فایل‌های منبع
│   ├── raw/
│   │   ├── Vless.txt
│   │   ├── Vmess.txt
│   │   └── ShadowSocks.txt
│   └── ...
├── trustlink/                # نتایج تست
│   ├── trustlink_vless.txt
│   ├── trustlink_vmess.txt
│   ├── trustlink_ss.txt
│   └── ...
└── logs/                     # لاگ‌ها
    ├── vless_tester.log
    ├── vmess_tester.log
    └── ss_tester.log
```

## 🔄 **GitHub Actions**

### **اجرای خودکار هفتگی**
- **VLESS Tester**: هر هفته یکشنبه ساعت 2 صبح
- **VMESS Tester**: هر هفته یکشنبه ساعت 2 صبح  
- **Shadowsocks Tester**: هر هفته یکشنبه ساعت 2 صبح

### **اجرای دستی**
هر tester دارای workflow دستی با پارامترهای قابل تنظیم است:
- حالت تست (یکباره/خودکار)
- حداکثر تعداد کانفیگ
- اندازه batch
- سطح لاگ
- و...

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

## 📈 **آمار و گزارش‌گیری**

### **فایل‌های خروجی**
هر tester فایل‌های زیر را تولید می‌کند:
- کانفیگ‌های سالم
- متادیتا و آمار
- فایل پشتیبان
- لاگ‌های کامل

### **متادیتا**
```json
{
  "last_update": "2024-01-01T12:00:00",
  "total_tests": 1000,
  "working_configs": 450,
  "test_statistics": {
    "connection_ok": 800,
    "iran_access_ok": 600,
    "social_media_ok": 500,
    "download_speed_ok": 450
  }
}
```

## 🚨 **مدیریت خطا**

### **ذخیره نتایج جزئی**
در صورت timeout یا خطا، هر tester نتایج جزئی را ذخیره می‌کند:
1. **Speed OK** - کانفیگ‌های قبول شده در تست سرعت
2. **Social Media OK** - کانفیگ‌های قبول شده در تست شبکه‌های اجتماعی
3. **Iran Access OK** - کانفیگ‌های قبول شده در تست دسترسی ایران
4. **Connection OK** - کانفیگ‌های قبول شده در تست اتصال

## 🔄 **حالت خودکار**

### **اجرای هر ساعت**
```bash
# VLESS Tester
python vless_tester.py --auto

# VMESS Tester  
python vmess_tester.py --auto

# Shadowsocks Tester
python ss_tester.py --auto
```

## 🛠️ **توسعه و سفارشی‌سازی**

### **اضافه کردن Tester جدید**
1. ایجاد دایرکتوری جدید
2. کپی کردن ساختار از tester موجود
3. تغییر پروتکل و parsing
4. تنظیم GitHub Actions

### **تغییر تنظیمات**
هر tester دارای فایل تنظیمات جداگانه است که می‌توانید تغییر دهید.

## 📞 **پشتیبانی**

برای گزارش مشکلات یا پیشنهادات:
1. بررسی لاگ‌های مربوط به هر tester
2. بررسی فایل‌های متادیتا
3. تست با تعداد کمتری کانفیگ
4. ایجاد issue در repository

## 📄 **لایسنس**

این پروژه تحت لایسنس TrustLink منتشر می‌شود.

---

**🔗 TrustLink V2Ray AutoConfig v2.0.0**

**✨ شامل 3 Tester کامل: VLESS, VMESS, Shadowsocks**
