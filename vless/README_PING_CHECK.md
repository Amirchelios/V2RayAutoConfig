# 🌐 Ping Check با check-host.net API

## 📋 توضیحات

این قابلیت جدید به برنامه VLess Tester اضافه شده است که از طریق API سایت check-host.net، سرورها را تست ping می‌کند. این تست بعد از تست TCP و قبل از تست دسترسی ایرانی انجام می‌شود.

## 🎯 هدف

- **تمرکز روی لوکیشن ایران، مشهد**: تست‌ها با تمرکز روی نودهای ایران انجام می‌شود
- **ارسال 50 تا 50 تا IP**: برای سرعت بالا، IP ها در batches 50 تایی ارسال می‌شوند
- **فیلتر کردن سرورهای سالم**: فقط سرورهایی که ping موفق دارند و traceroute ندارند سالم در نظر گرفته می‌شوند

## 🔧 نحوه کارکرد

### 1. تست Ping
- ارسال درخواست ping به check-host.net API
- انتظار برای آماده شدن نتایج (حداکثر 30 ثانیه)
- تحلیل نتایج ping و traceroute

### 2. معیارهای سلامت سرور
سرور سالم در نظر گرفته می‌شود اگر:
- ✅ **حداقل یک نود ping موفق داشته باشد**
- ❌ **هیچ نودی traceroute نداشته باشد** (null یا empty)

### 3. فلو تست
```
TCP Test → Ping Check
```

## 📊 تنظیمات

```python
# تنظیمات check-host.net API
CHECK_HOST_API_BASE = "https://check-host.net"
CHECK_HOST_PING_ENDPOINT = "/check-ping"
CHECK_HOST_RESULT_ENDPOINT = "/check-result"
CHECK_HOST_FOCUS_NODE = "ir2.node.check-host.net"  # نود ایران مشهد
CHECK_HOST_BATCH_SIZE = 50  # ارسال 50 تا 50 تا IP
```

## 🚀 استفاده

### اجرای عادی
```bash
python vless_tester.py
```

### تست ping جداگانه
```bash
python test_ping.py
```

## 📈 مزایا

1. **سرعت بالا**: ارسال batch های 50 تایی IP
2. **تمرکز جغرافیایی**: تست با نودهای ایران
3. **فیلتر دقیق**: رد کردن سرورهایی که traceroute دارند
4. **یکپارچگی**: کاملاً در فلو تست اصلی ادغام شده
5. **ذخیره جزئی**: نتایج در صورت timeout ذخیره می‌شوند

## 🔍 نمونه خروجی

```
🌐 شروع تست ping با check-host.net برای 150 کانفیگ سالم
📦 تست batch 1/3: 50 IP
✅ درخواست ping ارسال شد - Request ID: abc123
🌍 نودهای تست: ['us1.node.check-host.net', 'ch1.node.check-host.net', 'pt1.node.check-host.net']
✅ نتایج ping آماده شدند - زمان انتظار: 8 ثانیه
✅ IP 8.8.8.8: Ping موفق
✅ IP 1.1.1.1: Ping موفق
❌ IP 192.168.1.1: Ping ناموفق
...
✅ تست ping کامل شد: 45 کانفیگ سالم از 150
🌍 IP های سالم: 45 از 50
```

## ⚠️ نکات مهم

1. **Timeout**: هر batch حداکثر 30 ثانیه منتظر نتایج می‌ماند
2. **Rate Limiting**: بین batches 1 ثانیه صبر می‌شود
3. **Error Handling**: در صورت خطا، کل batch ناموفق در نظر گرفته می‌شود
4. **Fallback**: در صورت عدم دسترسی به API، تست‌ها ادامه می‌یابند

## 🧪 تست

برای تست عملکرد ping check:

```bash
cd vless
python test_ping.py
```

این اسکریپت چند IP نمونه را تست می‌کند و نتایج را نمایش می‌دهد.

## 📝 تغییرات در فایل اصلی

### فایل‌های تغییر یافته:
- `vless_tester.py`: اضافه شدن متدهای ping check
- `test_ping.py`: اسکریپت تست جداگانه (جدید)

### متدهای اضافه شده:
- `check_host_ping_batch()`: تست ping برای batch از IP ها
- `_analyze_ping_results()`: تحلیل نتایج ping
- `filter_configs_by_ping_check()`: فیلتر کردن کانفیگ‌ها بر اساس ping

### فلو تست به‌روزرسانی شده:
- فاز 1: تست اتصال TCP
- **فاز 2: تست ping با check-host.net** ← **جدید**

## 🔗 منابع

- [check-host.net API Documentation](https://check-host.net/check-ping)
- [VLess Protocol](https://github.com/XTLS/Xray-core/discussions/716)
- [TrustLink V2Ray AutoConfig](https://github.com/your-repo/V2RayAutoConfig)
