# 🔄 سیستم ادغام کانفیگ‌های سالم

## 📋 Overview

این سیستم برای حل مشکل بازنویسی (overwrite) شدن فایل `configs/Healthy.txt` طراحی شده است. هدف اصلی حفظ کانفیگ‌های قبلی و اضافه کردن کانفیگ‌های جدید سالم بدون حذف هیچ کانفیگی است.

## 🚀 نحوه کار

### **1. اسکریپت ادغام (`merge_healthy.py`)**

این اسکریپت مسئول ادغام کانفیگ‌های قدیمی و جدید است:

```bash
python3 scripts/merge_healthy.py <new_results_file> <dest_file>
```

**ویژگی‌ها:**
- **حفظ ترتیب**: ابتدا خطوط قدیمی، سپس خطوط جدید
- **حذف تکراری**: کانفیگ‌های تکراری به صورت خودکار حذف می‌شوند
- **نوشتن اتمیک**: استفاده از فایل موقت برای جلوگیری از خرابی
- **فیلتر پروتکل**: فقط کانفیگ‌های معتبر اضافه می‌شوند

### **2. ورک‌فلو GitHub Actions (`health.yml`)**

ورک‌فلو خودکار که هر ساعت اجرا می‌شود:

```yaml
on:
  schedule:
    - cron: "0 * * * *"  # هر ساعت
  workflow_dispatch: {}   # اجرای دستی
```

**مراحل:**
1. **Checkout**: دریافت کد با `fetch-depth: 0`
2. **تست سلامت**: اجرای اسکریپت تست و ذخیره نتایج
3. **ادغام**: اجرای `merge_healthy.py`
4. **Commit & Push**: ذخیره تغییرات با `pull --rebase`

## 🔧 الزامات فنی

### **پروتکل‌های پشتیبانی شده**
```python
SCHEMES = (
    "vmess://", "vless://", "trojan://", "ss://",
    "ssr://", "hysteria://", "hysteria2://", "tuic://", "socks://"
)
```

### **کنترل همزمانی**
```yaml
concurrency:
  group: healthy-update
  cancel-in-progress: true
```

### **امنیت**
- استفاده از فایل موقت برای نوشتن اتمیک
- `pull --rebase` قبل از commit
- بررسی تغییرات قبل از commit

## 📁 ساختار فایل‌ها

```
├── scripts/
│   ├── merge_healthy.py          # اسکریپت ادغام
│   └── README.md                 # این فایل
├── .github/workflows/
│   └── health.yml                # ورک‌فلو GitHub Actions
├── configs/
│   └── Healthy.txt               # فایل نهایی کانفیگ‌ها
└── artifacts/
    └── healthy_new.txt           # نتایج تست جدید
```

## 🧪 تست سیستم

### **تست 1: ادغام اولیه**
```bash
# ایجاد فایل تست قدیمی
echo "vmess://old1" > configs/Healthy.txt
echo "vmess://old2" >> configs/Healthy.txt

# ایجاد فایل تست جدید
echo "vmess://new1" > artifacts/healthy_new.txt
echo "vmess://new2" >> artifacts/healthy_new.txt

# اجرای ادغام
python3 scripts/merge_healthy.py artifacts/healthy_new.txt configs/Healthy.txt
```

**نتیجه مورد انتظار:**
```
vmess://old1
vmess://old2
vmess://new1
vmess://new2
```

### **تست 2: حذف تکراری**
```bash
# فایل جدید شامل کانفیگ تکراری
echo "vmess://old1" > artifacts/healthy_new.txt  # تکراری
echo "vmess://new3" >> artifacts/healthy_new.txt # جدید

# اجرای ادغام
python3 scripts/merge_healthy.py artifacts/healthy_new.txt configs/Healthy.txt
```

**نتیجه مورد انتظار:**
```
vmess://old1
vmess://old2
vmess://new1
vmess://new2
vmess://new3
```

### **تست 3: Idempotent**
```bash
# اجرای مجدد همان ادغام
python3 scripts/merge_healthy.py artifacts/healthy_new.txt configs/Healthy.txt
```

**نتیجه مورد انتظار:** هیچ تغییری در فایل نهایی

## 🚨 نکات مهم

### **1. حفظ کامنت‌ها**
- از فایل قدیمی، تمام خطوط غیرخالی حفظ می‌شوند
- از فایل جدید، فقط کانفیگ‌های معتبر اضافه می‌شوند

### **2. کنترل همزمانی**
- ورک‌فلو‌های همزمان لغو می‌شوند
- `concurrency.group: healthy-update`

### **3. امنیت**
- نوشتن اتمیک روی فایل موقت
- `pull --rebase` برای جلوگیری از کانفلیکت

## 🔍 عیب‌یابی

### **مشکل: فایل merge_healthy.py پیدا نمی‌شود**
```bash
# بررسی وجود فایل
ls -la scripts/merge_healthy.py

# بررسی مجوزها
chmod +x scripts/merge_healthy.py
```

### **مشکل: خطا در ادغام**
```bash
# بررسی محتوای فایل‌ها
cat configs/Healthy.txt
cat artifacts/healthy_new.txt

# اجرای دستی اسکریپت
python3 scripts/merge_healthy.py artifacts/healthy_new.txt configs/Healthy.txt
```

### **مشکل: تغییرات commit نمی‌شوند**
```bash
# بررسی وضعیت git
git status
git diff

# بررسی تغییرات staged
git diff --cached
```

## 📈 بهبودهای آینده

### **1. آمارگیری**
- تعداد کانفیگ‌های ادغام شده
- درصد تکراری‌ها
- زمان اجرا

### **2. اعتبارسنجی پیشرفته**
- بررسی فرمت کانفیگ‌ها
- تست اتصال
- رتبه‌بندی کیفیت

### **3. پشتیبان‌گیری**
- نسخه‌های پشتیبان
- تاریخچه تغییرات
- Rollback خودکار

## 🤝 مشارکت

برای بهبود این سیستم:

1. **گزارش مشکل**: Issue در GitHub
2. **پیشنهاد بهبود**: Pull Request
3. **تست**: اجرای ورک‌فلو و بررسی نتایج
4. **مستندسازی**: به‌روزرسانی این README

---

## 📞 پشتیبانی

برای سوالات یا مشکلات:
- ایجاد Issue در GitHub
- بررسی Logs ورک‌فلو
- تست محلی با اسکریپت‌ها
