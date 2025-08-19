#!/usr/bin/env python3
"""
🔗 TrustLink Shadowsocks Tester - Enhanced Runner

این اسکریپت پیشرفته برای اجرای Shadowsocks Tester با گزینه‌های مختلف است.
"""

import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path

# اضافه کردن مسیر فعلی به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ss_tester import SSManager, setup_logging
except ImportError as e:
    print(f"❌ خطا در import کردن SSManager: {e}")
    print("📁 اطمینان حاصل کنید که در دایرکتوری ss هستید")
    sys.exit(1)

def check_environment():
    """بررسی محیط اجرا"""
    print("📋 بررسی محیط...")
    
    # بررسی Xray
    xray_path = Path("../Files/xray-bin/xray.exe")
    if not xray_path.exists():
        xray_path = Path("../Files/xray-bin/xray")
    
    if not xray_path.exists():
        print("❌ فایل Xray یافت نشد!")
        print(f"📁 مسیر مورد انتظار: {xray_path}")
        return False
    
    print(f"✅ Xray یافت شد: {xray_path}")
    
    # بررسی فایل منبع
    source_path = Path("../configs/raw/ShadowSocks.txt")
    if not source_path.exists():
        print("❌ فایل منبع Shadowsocks یافت نشد!")
        print(f"📁 مسیر مورد انتظار: {source_path}")
        return False
    
    print(f"✅ فایل منبع یافت شد: {source_path}")
    
    # بررسی دایرکتوری‌های خروجی
    output_dirs = [
        Path("../trustlink"),
        Path("../logs")
    ]
    
    for dir_path in output_dirs:
        dir_path.mkdir(exist_ok=True)
        print(f"✅ دایرکتوری آماده: {dir_path}")
    
    return True

def setup_enhanced_logging():
    """تنظیم logging پیشرفته"""
    log_dir = Path("../logs")
    log_dir.mkdir(exist_ok=True)
    
    # تنظیم logging برای runner
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "ss_runner.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

async def run_single_test():
    """اجرای تست یکباره"""
    print("🚀 شروع تست یکباره کانفیگ‌های Shadowsocks...")
    
    try:
        manager = SSManager()
        await manager.run_full_test()
        print("✅ تست یکباره تکمیل شد")
        return True
    except Exception as e:
        print(f"❌ خطا در اجرای تست: {e}")
        return False

async def run_auto_test():
    """اجرای تست خودکار"""
    print("🔄 شروع حالت خودکار - تست هر ساعت اجرا خواهد شد")
    
    try:
        manager = SSManager()
        
        # اجرای اولیه
        print("📊 اجرای تست اولیه...")
        await manager.run_full_test()
        
        # برنامه‌ریزی اجرای هر ساعت
        import schedule
        import time
        
        schedule.every().hour.do(lambda: asyncio.run(manager.run_full_test()))
        
        print("⏰ برنامه‌ریزی اجرای هر ساعت فعال شد")
        print("🔄 برای توقف برنامه Ctrl+C را فشار دهید")
        
        # حلقه اصلی
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        print("\n⏹️ برنامه توسط کاربر متوقف شد")
        return True
    except Exception as e:
        print(f"❌ خطا در حالت خودکار: {e}")
        return False

def show_status():
    """نمایش وضعیت فعلی"""
    print("📊 بررسی وضعیت فعلی...")
    
    try:
        # بررسی فایل‌های خروجی
        output_files = {
            "کانفیگ‌های سالم": Path("../trustlink/trustlink_ss.txt"),
            "متادیتا": Path("../trustlink/.trustlink_ss_metadata.json"),
            "پشتیبان": Path("../trustlink/trustlink_ss_backup.txt"),
            "لاگ": Path("../logs/ss_tester.log")
        }
        
        for name, file_path in output_files.items():
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"✅ {name}: {file_path} ({size} bytes)")
            else:
                print(f"❌ {name}: یافت نشد")
        
        # نمایش آمار از متادیتا
        metadata_path = Path("../trustlink/.trustlink_ss_metadata.json")
        if metadata_path.exists():
            import json
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                print(f"\n📈 آمار تست:")
                print(f"  آخرین به‌روزرسانی: {metadata.get('last_update', 'نامشخص')}")
                print(f"  کل تست‌ها: {metadata.get('total_tests', 0)}")
                print(f"  کانفیگ‌های سالم: {metadata.get('working_configs', 0)}")
                print(f"  کل کانفیگ‌ها: {metadata.get('total_configs', 0)}")
                
                if 'test_statistics' in metadata:
                    stats = metadata['test_statistics']
                    print(f"  اتصال سالم: {stats.get('connection_ok', 0)}")
                    print(f"  دسترسی ایران: {stats.get('iran_access_ok', 0)}")
                    print(f"  شبکه‌های اجتماعی: {stats.get('social_media_ok', 0)}")
                    print(f"  سرعت دانلود: {stats.get('download_speed_ok', 0)}")
                    
            except Exception as e:
                print(f"⚠️ خطا در خواندن متادیتا: {e}")
        
    except Exception as e:
        print(f"❌ خطا در بررسی وضعیت: {e}")

def main():
    """تابع اصلی"""
    parser = argparse.ArgumentParser(
        description="TrustLink Shadowsocks Tester - Enhanced Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال‌های استفاده:
  python run_ss_tester_enhanced.py              # تست یکباره
  python run_ss_tester_enhanced.py --auto       # حالت خودکار
  python run_ss_tester_enhanced.py --status     # نمایش وضعیت
  python run_ss_tester_enhanced.py --check      # بررسی محیط
        """
    )
    
    parser.add_argument(
        '--auto', 
        action='store_true',
        help='اجرای خودکار هر ساعت'
    )
    
    parser.add_argument(
        '--status', 
        action='store_true',
        help='نمایش وضعیت فعلی'
    )
    
    parser.add_argument(
        '--check', 
        action='store_true',
        help='بررسی محیط بدون اجرا'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='نمایش جزئیات بیشتر'
    )
    
    args = parser.parse_args()
    
    # تنظیم logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        setup_enhanced_logging()
    
    print("🔗 TrustLink Shadowsocks Tester - Enhanced Runner")
    print("=" * 50)
    
    # بررسی محیط
    if not check_environment():
        print("\n❌ محیط آماده نیست. لطفاً مشکلات را برطرف کنید.")
        sys.exit(1)
    
    print("\n✅ محیط آماده است")
    
    # اگر فقط بررسی محیط درخواست شده
    if args.check:
        print("\n✅ بررسی محیط تکمیل شد")
        return
    
    # اگر نمایش وضعیت درخواست شده
    if args.status:
        show_status()
        return
    
    # اجرای تست
    try:
        if args.auto:
            asyncio.run(run_auto_test())
        else:
            asyncio.run(run_single_test())
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
