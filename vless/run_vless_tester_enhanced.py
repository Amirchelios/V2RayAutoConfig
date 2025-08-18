#!/usr/bin/env python3
"""
🔗 Enhanced VLESS Tester - نسخه بهبود یافته تستر VLESS
این اسکریپت تمام کانفیگ‌های VLESS را از منابع مختلف دانلود کرده و تست می‌کند
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# اضافه کردن مسیر فعلی به sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vless_tester import VLESSManager, setup_logging

async def run_enhanced_vless_tester():
    """اجرای تستر VLESS بهبود یافته"""
    setup_logging()
    
    logging.info("🚀 راه‌اندازی Enhanced TrustLink VLESS Tester")
    logging.info("=" * 60)
    
    manager = VLESSManager()
    
    try:
        # اجرای یک دور به‌روزرسانی با timeout طولانی
        async with asyncio.timeout(7200):  # timeout 2 ساعت
            success = await manager.run_vless_update()
        
        if success:
            status = manager.get_status()
            logging.info("📈 وضعیت نهایی VLESS:")
            for key, value in status.items():
                logging.info(f"  {key}: {value}")
            
            # نمایش آمار ایران access
            if hasattr(manager, 'iran_access_stats'):
                stats = manager.iran_access_stats
                logging.info("🇮🇷 آمار دسترسی از ایران:")
                logging.info(f"  کل تست شده: {stats['total_tested']}")
                logging.info(f"  قابل دسترس از ایران: {stats['iran_accessible']}")
                logging.info(f"  سایر: {stats['other_configs']}")
                logging.info(f"  انتخاب شده - ایران: {stats['selected_iran']}")
                logging.info(f"  انتخاب شده - سایر: {stats['selected_other']}")
        else:
            logging.error("❌ به‌روزرسانی VLESS ناموفق بود")
            
    except asyncio.TimeoutError:
        logging.error("⏰ timeout: برنامه VLESS بیش از 2 ساعت طول کشید")
    except KeyboardInterrupt:
        logging.info("برنامه VLESS توسط کاربر متوقف شد")
    except Exception as e:
        logging.error(f"خطای غیرمنتظره در VLESS: {e}")
    finally:
        await manager.close_session()

def main():
    """تابع اصلی"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("""
🔗 Enhanced VLESS Tester - راهنما

استفاده:
  python run_vless_tester_enhanced.py          # اجرای کامل
  python run_vless_tester_enhanced.py --help   # نمایش این راهنما

ویژگی‌ها:
  ✅ دانلود از منابع مختلف VLESS
  ✅ تست تمام کانفیگ‌ها (تا 10000 کانفیگ)
  ✅ تست دسترسی از ایران
  ✅ انتخاب بهترین کانفیگ‌ها
  ✅ ذخیره در trustlink_vless.txt
            """)
            return
        else:
            print(f"پارامتر ناشناخته: {sys.argv[1]}")
            print("برای راهنما: python run_vless_tester_enhanced.py --help")
            return
    
    # اجرای تستر
    asyncio.run(run_enhanced_vless_tester())

if __name__ == "__main__":
    main()
