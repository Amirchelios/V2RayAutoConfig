#!/usr/bin/env python3
"""
🔗 TrustLink - برنامه هوشمند برای دانلود و ذخیره کانفیگ‌های سالم
این برنامه هر نیم ساعت کانفیگ‌های Healthy.txt را دانلود کرده و در trustlink.txt ذخیره می‌کند
"""

import os
import sys
import time
import json
import logging
import asyncio
import aiohttp
import hashlib
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional
from urllib.parse import urlparse
import re

# تنظیمات
HEALTHY_URL = "https://raw.githubusercontent.com/Amirchelios/V2RayAutoConfig/refs/heads/main/configs/Healthy.txt"
TRUSTLINK_FILE = "trustlink/trustlink.txt"
TRUSTLINK_METADATA = "trustlink/.trustlink_metadata.json"
BACKUP_FILE = "trustlink/trustlink_backup.txt"
LOG_FILE = "logs/trustlink.log"

# پروتکل‌های پشتیبانی شده
SUPPORTED_PROTOCOLS = {
    "vmess://", "vless://", "trojan://", "ss://", "ssr://", 
    "hysteria://", "hysteria2://", "tuic://", "socks://"
}

# تنظیمات logging
def setup_logging():
    """تنظیم سیستم logging"""
    try:
        os.makedirs("logs", exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    except Exception as e:
        print(f"خطا در ایجاد دایرکتوری logs: {e}")
        # اگر نتوانستیم دایرکتوری logs ایجاد کنیم، از stdout استفاده کن
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )

class TrustLinkManager:
    """مدیریت اصلی برنامه TrustLink"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.existing_configs: Set[str] = set()
        self.metadata: Dict = {}
        self.load_metadata()
        
    def load_metadata(self):
        """بارگذاری متادیتای برنامه"""
        try:
            if os.path.exists(TRUSTLINK_METADATA):
                with open(TRUSTLINK_METADATA, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logging.info("متادیتای برنامه بارگذاری شد")
            else:
                self.metadata = {
                    "last_update": "1970-01-01T00:00:00",
                    "total_downloads": 0,
                    "total_configs": 0,
                    "duplicates_skipped": 0,
                    "last_healthy_url": "",
                    "version": "1.0.0"
                }
                logging.info("متادیتای جدید ایجاد شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری متادیتا: {e}")
            self.metadata = {"last_update": "1970-01-01T00:00:00", "total_downloads": 0}
    
    def save_metadata(self):
        """ذخیره متادیتای برنامه"""
        try:
            os.makedirs(os.path.dirname(TRUSTLINK_METADATA), exist_ok=True)
            with open(TRUSTLINK_METADATA, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logging.info("متادیتای برنامه ذخیره شد")
        except Exception as e:
            logging.error(f"خطا در ذخیره متادیتا: {e}")
    
    async def create_session(self):
        """ایجاد session برای HTTP requests"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)  # کاهش timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
            logging.info("Session جدید ایجاد شد")
    
    async def close_session(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("Session بسته شد")
    
    def load_existing_configs(self):
        """بارگذاری کانفیگ‌های موجود از trustlink.txt"""
        try:
            # اطمینان از وجود دایرکتوری configs
            os.makedirs(os.path.dirname(TRUSTLINK_FILE), exist_ok=True)
            
            if os.path.exists(TRUSTLINK_FILE):
                with open(TRUSTLINK_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    self.existing_configs = {line.strip() for line in lines if line.strip()}
                logging.info(f"{len(self.existing_configs)} کانفیگ موجود بارگذاری شد")
            else:
                self.existing_configs = set()
                logging.info("فایل trustlink.txt وجود ندارد - شروع از صفر")
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های موجود: {e}")
            self.existing_configs = set()
    
    def is_valid_config(self, config: str) -> bool:
        """بررسی اعتبار کانفیگ"""
        if not config or len(config.strip()) < 10:
            return False
        
        config_lower = config.lower().strip()
        return any(config_lower.startswith(protocol) for protocol in SUPPORTED_PROTOCOLS)
    
    def create_config_hash(self, config: str) -> str:
        """ایجاد hash برای کانفیگ (برای تشخیص تکراری)"""
        return hashlib.md5(config.strip().encode('utf-8')).hexdigest()
    
    async def download_healthy_configs(self) -> List[str]:
        """دانلود کانفیگ‌های Healthy.txt از GitHub"""
        try:
            await self.create_session()
            
            logging.info(f"شروع دانلود از: {HEALTHY_URL}")
            async with self.session.get(HEALTHY_URL) as response:
                if response.status == 200:
                    content = await response.text()
                    lines = content.split('\n')
                    valid_configs = []
                    
                    for line in lines:
                        line = line.strip()
                        if self.is_valid_config(line):
                            valid_configs.append(line)
                    
                    logging.info(f"دانلود موفق: {len(valid_configs)} کانفیگ معتبر")
                    return valid_configs
                else:
                    logging.error(f"خطا در دانلود: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logging.error(f"خطا در دانلود کانفیگ‌ها: {e}")
            return []
    
    def merge_configs(self, new_configs: List[str]) -> Dict[str, int]:
        """ادغام کانفیگ‌های جدید با موجود"""
        stats = {
            "new_added": 0,
            "duplicates_skipped": 0,
            "invalid_skipped": 0
        }
        
        # اطمینان از وجود دایرکتوری configs
        os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
        
        # ایجاد backup از فایل موجود
        if os.path.exists(TRUSTLINK_FILE):
            try:
                import shutil
                shutil.copy2(TRUSTLINK_FILE, BACKUP_FILE)
                logging.info("Backup از فایل موجود ایجاد شد")
            except Exception as e:
                logging.warning(f"خطا در ایجاد backup: {e}")
                # اگر backup ناموفق بود، یک فایل خالی ایجاد کن
                try:
                    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
                        f.write("# فایل backup خالی - خطا در کپی فایل اصلی\n")
                    logging.info("فایل backup خالی ایجاد شد")
                except Exception as e2:
                    logging.error(f"خطا در ایجاد فایل backup خالی: {e2}")
        else:
            # اگر فایل اصلی وجود ندارد، یک فایل backup خالی ایجاد کن
            try:
                with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
                    f.write("# فایل backup خالی - فایل اصلی وجود نداشت\n")
                logging.info("فایل backup خالی ایجاد شد")
            except Exception as e:
                logging.warning(f"خطا در ایجاد فایل backup خالی: {e}")
        
        # بررسی و اضافه کردن کانفیگ‌های جدید
        for config in new_configs:
            if not self.is_valid_config(config):
                stats["invalid_skipped"] += 1
                continue
                
            if config in self.existing_configs:
                stats["duplicates_skipped"] += 1
                continue
            
            self.existing_configs.add(config)
            stats["new_added"] += 1
        
        logging.info(f"ادغام کامل: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری، {stats['invalid_skipped']} نامعتبر")
        return stats
    
    def save_trustlink_file(self):
        """ذخیره فایل trustlink.txt"""
        try:
            os.makedirs(os.path.dirname(TRUSTLINK_FILE), exist_ok=True)
            
            # نوشتن اتمیک با فایل موقت
            import tempfile
            fd, tmp_path = tempfile.mkstemp(prefix=".trustlink_", suffix=".tmp", dir=os.path.dirname(TRUSTLINK_FILE) or ".")
            
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    # نوشتن header
                    f.write(f"# 🔗 TrustLink - کانفیگ‌های قابل اعتماد\n")
                    f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# تعداد کل: {len(self.existing_configs)}\n")
                    f.write(f"# منبع: {HEALTHY_URL}\n")
                    f.write(f"#\n")
                    
                    # نوشتن کانفیگ‌ها
                    for config in sorted(self.existing_configs):
                        f.write(f"{config}\n")
                
                # انتقال فایل موقت به مقصد نهایی
                import shutil
                shutil.move(tmp_path, TRUSTLINK_FILE)
                
                logging.info(f"فایل trustlink.txt با موفقیت ذخیره شد: {len(self.existing_configs)} کانفیگ")
                return True
                
            except Exception as e:
                logging.error(f"خطا در نوشتن فایل موقت: {e}")
                try:
                    os.remove(tmp_path)
                except:
                    pass
                return False
                
        except Exception as e:
            logging.error(f"خطا در ذخیره فایل trustlink.txt: {e}")
            return False
    
    def update_metadata(self, stats: Dict[str, int]):
        """به‌روزرسانی متادیتای برنامه"""
        now = datetime.now().isoformat()
        
        self.metadata.update({
            "last_update": now,
            "total_downloads": self.metadata.get("total_downloads", 0) + 1,
            "total_configs": len(self.existing_configs),
            "duplicates_skipped": self.metadata.get("duplicates_skipped", 0) + stats["duplicates_skipped"],
            "last_healthy_url": HEALTHY_URL,
            "last_stats": {
                "new_added": stats["new_added"],
                "duplicates_skipped": stats["duplicates_skipped"],
                "invalid_skipped": stats["invalid_skipped"],
                "timestamp": now
            }
        })
        
        self.save_metadata()
    
    async def run_update(self) -> bool:
        """اجرای یک دور کامل به‌روزرسانی"""
        try:
            logging.info("=" * 50)
            logging.info("شروع به‌روزرسانی TrustLink")
            logging.info("=" * 50)
            
            # بارگذاری کانفیگ‌های موجود
            self.load_existing_configs()
            
            # دانلود کانفیگ‌های جدید
            new_configs = await self.download_healthy_configs()
            if not new_configs:
                logging.warning("هیچ کانفیگ جدیدی دانلود نشد")
                return False
            
            # ادغام کانفیگ‌ها
            stats = self.merge_configs(new_configs)
            
            # ذخیره فایل
            if self.save_trustlink_file():
                # اطمینان از وجود فایل backup
                self.ensure_backup_file_exists()
                
                # به‌روزرسانی متادیتا
                self.update_metadata(stats)
                
                logging.info("✅ به‌روزرسانی با موفقیت انجام شد")
                logging.info(f"📊 آمار: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری")
                return True
            else:
                logging.error("❌ خطا در ذخیره فایل")
                return False
                
        except Exception as e:
            logging.error(f"خطا در اجرای به‌روزرسانی: {e}")
            return False
        finally:
            await self.close_session()
    
    def get_status(self) -> Dict:
        """دریافت وضعیت فعلی برنامه"""
        return {
            "total_configs": len(self.existing_configs),
            "last_update": self.metadata.get("last_update", "نامشخص"),
            "total_downloads": self.metadata.get("total_downloads", 0),
            "duplicates_skipped": self.metadata.get("duplicates_skipped", 0),
            "file_size_kb": os.path.getsize(TRUSTLINK_FILE) / 1024 if os.path.exists(TRUSTLINK_FILE) else 0,
            "backup_exists": os.path.exists(BACKUP_FILE)
        }
    
    def ensure_backup_file_exists(self):
        """اطمینان از وجود فایل backup"""
        try:
            os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
            if not os.path.exists(BACKUP_FILE):
                with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
                    f.write("# فایل backup خالی - ایجاد شده توسط ensure_backup_file_exists\n")
                logging.info("فایل backup خالی ایجاد شد")
        except Exception as e:
            logging.warning(f"خطا در ایجاد فایل backup: {e}")

async def main():
    """تابع اصلی برنامه"""
    setup_logging()
    
    logging.info("🚀 راه‌اندازی TrustLink")
    
    manager = TrustLinkManager()
    
    try:
        # اجرای یک دور به‌روزرسانی با timeout
        async with asyncio.timeout(120):  # timeout 2 دقیقه
            success = await manager.run_update()
        
        if success:
            status = manager.get_status()
            logging.info("📈 وضعیت نهایی:")
            for key, value in status.items():
                logging.info(f"  {key}: {value}")
        else:
            logging.error("❌ به‌روزرسانی ناموفق بود")
            
    except asyncio.TimeoutError:
        logging.error("⏰ timeout: برنامه بیش از 2 دقیقه طول کشید")
    except KeyboardInterrupt:
        logging.info("برنامه توسط کاربر متوقف شد")
    except Exception as e:
        logging.error(f"خطای غیرمنتظره: {e}")
    finally:
        await manager.close_session()

if __name__ == "__main__":
    asyncio.run(main())
