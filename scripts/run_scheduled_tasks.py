#!/usr/bin/env python3
"""
🕐 اجراکننده محلی برنامه‌های زمانبندی شده V2Ray AutoConfig

این اسکریپت برای اجرای محلی برنامه‌های زمانبندی شده طراحی شده است.
برای استفاده در سرور یا سیستم محلی مناسب است.
"""

import os
import sys
import time
import logging
import schedule
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

# تنظیمات logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_tasks.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ScheduledTaskRunner:
    """کلاس اصلی برای اجرای برنامه‌های زمانبندی شده"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.logger = logging.getLogger(__name__)
        
    def run_v2ray_autoconfig(self):
        """اجرای V2Ray AutoConfig"""
        try:
            self.logger.info("🚀 شروع اجرای V2Ray AutoConfig")
            
            # تغییر به دایرکتوری اصلی
            os.chdir(self.base_dir)
            
            # اجرای اسکریپت اصلی
            result = subprocess.run([
                sys.executable, 'Files/scrip.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 دقیقه timeout
            
            if result.returncode == 0:
                self.logger.info("✅ V2Ray AutoConfig با موفقیت اجرا شد")
                self.logger.info(f"خروجی: {result.stdout[-500:]}")  # آخرین 500 کاراکتر
            else:
                self.logger.error(f"❌ V2Ray AutoConfig با خطا مواجه شد: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("⏰ V2Ray AutoConfig بیش از 30 دقیقه طول کشید")
        except Exception as e:
            self.logger.error(f"خطا در اجرای V2Ray AutoConfig: {e}")
    
    def run_vless_tester(self):
        """اجرای VLESS Tester"""
        try:
            self.logger.info("🚀 شروع اجرای VLESS Tester")
            
            # تغییر به دایرکتوری vless
            vless_dir = self.base_dir / 'vless'
            os.chdir(vless_dir)
            
            # اجرای VLESS Tester
            result = subprocess.run([
                sys.executable, 'vless_tester.py'
            ], capture_output=True, text=True, timeout=3600)  # 60 دقیقه timeout
            
            if result.returncode == 0:
                self.logger.info("✅ VLESS Tester با موفقیت اجرا شد")
                self.logger.info(f"خروجی: {result.stdout[-500:]}")
            else:
                self.logger.error(f"❌ VLESS Tester با خطا مواجه شد: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("⏰ VLESS Tester بیش از 60 دقیقه طول کشید")
        except Exception as e:
            self.logger.error(f"خطا در اجرای VLESS Tester: {e}")
    
    def run_daily_trustlink_optimizer(self):
        """اجرای Daily TrustLink Optimizer"""
        try:
            self.logger.info("🚀 شروع اجرای Daily TrustLink Optimizer")
            
            # تغییر به دایرکتوری daily-tester
            daily_dir = self.base_dir / 'daily-tester'
            os.chdir(daily_dir)
            
            # اجرای Daily TrustLink Optimizer
            result = subprocess.run([
                sys.executable, 'daily_trustlink_tester.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 دقیقه timeout
            
            if result.returncode == 0:
                self.logger.info("✅ Daily TrustLink Optimizer با موفقیت اجرا شد")
                self.logger.info(f"خروجی: {result.stdout[-500:]}")
            else:
                self.logger.error(f"❌ Daily TrustLink Optimizer با خطا مواجه شد: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("⏰ Daily TrustLink Optimizer بیش از 30 دقیقه طول کشید")
        except Exception as e:
            self.logger.error(f"خطا در اجرای Daily TrustLink Optimizer: {e}")
    
    def run_daily_trustlink_tester(self):
        """اجرای Daily TrustLink Tester"""
        try:
            self.logger.info("🚀 شروع اجرای Daily TrustLink Tester")
            
            # تغییر به دایرکتوری daily-tester
            daily_dir = self.base_dir / 'daily-tester'
            os.chdir(daily_dir)
            
            # اجرای Daily TrustLink Tester
            result = subprocess.run([
                sys.executable, 'daily_trustlink_tester.py'
            ], capture_output=True, text=True, timeout=1800)  # 30 دقیقه timeout
            
            if result.returncode == 0:
                self.logger.info("✅ Daily TrustLink Tester با موفقیت اجرا شد")
                self.logger.info(f"خروجی: {result.stdout[-500:]}")
            else:
                self.logger.error(f"❌ Daily TrustLink Tester با خطا مواجه شد: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("⏰ Daily TrustLink Tester بیش از 30 دقیقه طول کشید")
        except Exception as e:
            self.logger.error(f"خطا در اجرای Daily TrustLink Tester: {e}")
    
    def setup_schedule(self):
        """تنظیم برنامه زمانبندی"""
        self.logger.info("⏰ تنظیم برنامه زمانبندی خودکار")
        
        # V2Ray AutoConfig - 6 بار در روز
        schedule.every().day.at("05:30").do(self.run_v2ray_autoconfig)  # 02:00 UTC
        schedule.every().day.at("09:30").do(self.run_v2ray_autoconfig)  # 06:00 UTC
        schedule.every().day.at("13:30").do(self.run_v2ray_autoconfig)  # 10:00 UTC
        schedule.every().day.at("17:30").do(self.run_v2ray_autoconfig)  # 14:00 UTC
        schedule.every().day.at("21:30").do(self.run_v2ray_autoconfig)  # 18:00 UTC
        schedule.every().day.at("01:30").do(self.run_v2ray_autoconfig)  # 22:00 UTC
        
        # VLESS Tester - هفته‌ای یکبار (یکشنبه)
        schedule.every().sunday.at("06:30").do(self.run_vless_tester)
        
        # Daily TrustLink Optimizer - روزانه ساعت 3 صبح تهران
        schedule.every().day.at("03:00").do(self.run_daily_trustlink_optimizer)
        
        # Daily TrustLink Tester - روزانه
        schedule.every().day.at("03:30").do(self.run_daily_trustlink_tester)
        
        self.logger.info("📅 برنامه زمانبندی تنظیم شد:")
        self.logger.info("  - V2Ray AutoConfig: 6 بار در روز")
        self.logger.info("  - VLESS Tester: یکشنبه‌ها ساعت 06:30")
        self.logger.info("  - Daily TrustLink Optimizer: هر روز ساعت 03:00")
        self.logger.info("  - Daily TrustLink Tester: هر روز ساعت 03:30")
    
    def run_scheduler(self):
        """اجرای اصلی scheduler"""
        self.logger.info("🚀 راه‌اندازی اجراکننده محلی برنامه‌های زمانبندی شده")
        self.logger.info(f"📁 دایرکتوری اصلی: {self.base_dir}")
        
        # تنظیم برنامه زمانبندی
        self.setup_schedule()
        
        # نمایش برنامه زمانبندی
        self.logger.info("📋 برنامه زمانبندی فعلی:")
        for job in schedule.get_jobs():
            self.logger.info(f"  - {job}")
        
        self.logger.info("⏳ منتظر اجرای برنامه‌های زمانبندی شده...")
        self.logger.info("برای توقف، Ctrl+C را فشار دهید")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # بررسی هر دقیقه
        except KeyboardInterrupt:
            self.logger.info("🛑 اجراکننده متوقف شد")
        except Exception as e:
            self.logger.error(f"خطا در اجرای scheduler: {e}")

def main():
    """تابع اصلی"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        runner = ScheduledTaskRunner()
        
        if command == "v2ray":
            runner.run_v2ray_autoconfig()
        elif command == "vless":
            runner.run_vless_tester()
        elif command == "daily":
            runner.run_daily_trustlink_tester()
        elif command == "schedule":
            runner.run_scheduler()
        else:
            print("استفاده:")
            print("  python run_scheduled_tasks.py v2ray    # اجرای V2Ray AutoConfig")
            print("  python run_scheduled_tasks.py vless    # اجرای VLESS Tester")
            print("  python run_scheduled_tasks.py daily    # اجرای Daily TrustLink")
            print("  python run_scheduled_tasks.py schedule # اجرای scheduler")
    else:
        print("🚀 اجراکننده محلی برنامه‌های زمانبندی شده V2Ray AutoConfig")
        print("")
        print("برای اجرای scheduler:")
        print("  python run_scheduled_tasks.py schedule")
        print("")
        print("برای اجرای دستی:")
        print("  python run_scheduled_tasks.py v2ray")
        print("  python run_scheduled_tasks.py vless")
        print("  python run_scheduled_tasks.py daily")

if __name__ == "__main__":
    main()
