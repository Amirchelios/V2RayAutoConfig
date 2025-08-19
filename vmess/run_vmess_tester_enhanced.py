#!/usr/bin/env python3
"""
🚀 VMESS Tester Enhanced Runner - اجراکننده پیشرفته تستر VMESS
این اسکریپت امکان اجرای تستر VMESS با تنظیمات پیشرفته را فراهم می‌کند
"""

import asyncio
import logging
import sys
import os
from vmess_tester import VMESSManager, setup_logging

async def run_enhanced_test():
    """اجرای تست پیشرفته با تنظیمات بهینه"""
    try:
        setup_logging()
        logging.info("شروع تست پیشرفته کانفیگ‌های VMESS")
        
        manager = VMESSManager()
        
        # اجرای تست کامل
        await manager.run_full_test()
        
        logging.info("تست پیشرفته کانفیگ‌های VMESS تکمیل شد")
        
    except Exception as e:
        logging.error(f"خطا در اجرای تست پیشرفته: {e}")
        sys.exit(1)

def main():
    """تابع اصلی"""
    try:
        # اجرای تست
        asyncio.run(run_enhanced_test())
    except KeyboardInterrupt:
        print("\nتست توسط کاربر متوقف شد")
    except Exception as e:
        print(f"خطا در اجرا: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
