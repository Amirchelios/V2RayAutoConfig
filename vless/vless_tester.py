#!/usr/bin/env python3
"""
🔗 VLESS Tester - برنامه هوشمند برای تست و ذخیره کانفیگ‌های VLESS سالم
این برنامه هر ساعت کانفیگ‌های VLESS را از Vless.txt دانلود کرده و در trustlink_vless.txt ذخیره می‌کند
"""

import os
import sys
import time
import json
import logging
import asyncio
import aiohttp
import hashlib
import schedule
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional
from urllib.parse import urlparse
import re

# تنظیمات
VLESS_SOURCE_FILE = "../configs/raw/Vless.txt"
TRUSTLINK_VLESS_FILE = "../trustlink/trustlink_vless.txt"
TRUSTLINK_VLESS_METADATA = "../trustlink/.trustlink_vless_metadata.json"
BACKUP_FILE = "../trustlink/trustlink_vless_backup.txt"
LOG_FILE = "../logs/vless_tester.log"

# پروتکل VLESS
VLESS_PROTOCOL = "vless://"

# تنظیمات تست
TEST_TIMEOUT = 15  # ثانیه
CONCURRENT_TESTS = 10
KEEP_BEST_COUNT = 50  # تعداد کانفیگ‌های سالم نگه‌داری شده

# تنظیمات logging
def setup_logging():
    """تنظیم سیستم logging"""
    try:
        os.makedirs("../logs", exist_ok=True)
        
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

class VLESSManager:
    """مدیریت اصلی برنامه VLESS Tester"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.existing_configs: Set[str] = set()
        self.metadata: Dict = {}
        self.load_metadata()
        
    def load_metadata(self):
        """بارگذاری متادیتای برنامه"""
        try:
            if os.path.exists(TRUSTLINK_VLESS_METADATA):
                with open(TRUSTLINK_VLESS_METADATA, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logging.info("متادیتای برنامه VLESS بارگذاری شد")
            else:
                self.metadata = {
                    "last_update": "1970-01-01T00:00:00",
                    "total_tests": 0,
                    "total_configs": 0,
                    "working_configs": 0,
                    "failed_configs": 0,
                    "last_vless_source": VLESS_SOURCE_FILE,
                    "version": "1.0.0"
                }
                logging.info("متادیتای جدید VLESS ایجاد شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری متادیتا: {e}")
            self.metadata = {"last_update": "1970-01-01T00:00:00", "total_tests": 0}
    
    def save_metadata(self):
        """ذخیره متادیتای برنامه"""
        try:
            os.makedirs(os.path.dirname(TRUSTLINK_VLESS_METADATA), exist_ok=True)
            with open(TRUSTLINK_VLESS_METADATA, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logging.info("متادیتای برنامه VLESS ذخیره شد")
        except Exception as e:
            logging.error(f"خطا در ذخیره متادیتا: {e}")
    
    async def create_session(self):
        """ایجاد session برای HTTP requests"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT, connect=5, sock_read=TEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logging.info("Session جدید برای تست VLESS ایجاد شد")
    
    async def close_session(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("Session VLESS بسته شد")
    
    def load_existing_configs(self):
        """بارگذاری کانفیگ‌های موجود از trustlink_vless.txt"""
        try:
            # اطمینان از وجود دایرکتوری trustlink
            os.makedirs(os.path.dirname(TRUSTLINK_VLESS_FILE), exist_ok=True)
            
            if os.path.exists(TRUSTLINK_VLESS_FILE):
                with open(TRUSTLINK_VLESS_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # فیلتر کردن header ها و خطوط خالی
                    valid_configs = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and self.is_valid_vless_config(line):
                            valid_configs.append(line)
                    
                    self.existing_configs = set(valid_configs)
                logging.info(f"{len(self.existing_configs)} کانفیگ VLESS موجود بارگذاری شد")
            else:
                self.existing_configs = set()
                logging.info("فایل trustlink_vless.txt وجود ندارد - شروع از صفر")
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های VLESS موجود: {e}")
            self.existing_configs = set()
    
    def is_valid_vless_config(self, config: str) -> bool:
        """بررسی اعتبار کانفیگ VLESS"""
        if not config or len(config.strip()) < 10:
            return False
        
        config_lower = config.lower().strip()
        return config_lower.startswith(VLESS_PROTOCOL)
    
    def create_config_hash(self, config: str) -> str:
        """ایجاد hash برای کانفیگ (برای تشخیص تکراری)"""
        return hashlib.md5(config.strip().encode('utf-8')).hexdigest()
    
    def load_vless_source_configs(self) -> List[str]:
        """بارگذاری کانفیگ‌های VLESS از فایل منبع"""
        try:
            if not os.path.exists(VLESS_SOURCE_FILE):
                logging.error(f"فایل منبع VLESS یافت نشد: {VLESS_SOURCE_FILE}")
                return []
            
            with open(VLESS_SOURCE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                valid_configs = []
                
                for line in lines:
                    line = line.strip()
                    if self.is_valid_vless_config(line):
                        valid_configs.append(line)
                
                logging.info(f"{len(valid_configs)} کانفیگ VLESS معتبر از فایل منبع بارگذاری شد")
                return valid_configs
                
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های VLESS از فایل منبع: {e}")
            return []
    
    def extract_server_address(self, config: str) -> Optional[str]:
        """استخراج آدرس سرور از کانفیگ VLESS"""
        try:
            if config.startswith(VLESS_PROTOCOL):
                # حذف vless:// و parse کردن
                vless_data = config.replace(VLESS_PROTOCOL, "")
                
                # پیدا کردن @ برای جدا کردن UUID و آدرس
                at_index = vless_data.find('@')
                if at_index != -1:
                    # آدرس سرور بعد از @
                    server_part = vless_data[at_index + 1:]
                    
                    # پیدا کردن : برای جدا کردن IP و پورت
                    colon_index = server_part.find(':')
                    if colon_index != -1:
                        ip = server_part[:colon_index]
                        # حذف query parameters اگر وجود داشته باشد
                        question_index = ip.find('?')
                        if question_index != -1:
                            ip = ip[:question_index]
                        return ip
                
                return None
            else:
                return None
        except Exception:
            return None
    
    async def test_vless_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ VLESS"""
        config_hash = self.create_config_hash(config)[:8]
        result = {
            "config": config,
            "hash": config_hash,
            "success": False,
            "latency": None,
            "error": None,
            "server_address": None
        }
        
        try:
            # استخراج آدرس سرور
            server_address = self.extract_server_address(config)
            if server_address:
                result["server_address"] = server_address
                
                # تست اتصال با ping به سرور
                start_time = time.time()
                success = await self.ping_server(server_address)
                latency = (time.time() - start_time) * 1000  # میلی‌ثانیه
                
                if success:
                    result["success"] = True
                    result["latency"] = latency
                    logging.info(f"✅ تست VLESS موفق: {config_hash} - Latency: {latency:.1f}ms")
                else:
                    result["error"] = "Ping failed"
                    logging.warning(f"❌ تست VLESS ناموفق: {config_hash}")
            else:
                result["error"] = "Invalid VLESS config format"
                logging.warning(f"❌ کانفیگ VLESS نامعتبر: {config_hash}")
                
        except Exception as e:
            result["error"] = str(e)
            logging.error(f"خطا در تست VLESS {config_hash}: {e}")
        
        return result
    
    async def ping_server(self, server_address: str) -> bool:
        """ping کردن سرور"""
        try:
            # تست اتصال با timeout کوتاه
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # تست اتصال به پورت‌های مختلف
                for port in [80, 443, 8080, 8443]:
                    try:
                        url = f"http://{server_address}:{port}" if port in [80, 8080] else f"https://{server_address}:{port}"
                        async with session.get(url) as response:
                            if response.status < 500:  # هر پاسخ غیر از خطای سرور
                                return True
                    except:
                        continue
                
                return False
        except Exception:
            return False
    
    async def test_all_vless_configs(self, configs: List[str]) -> List[Dict]:
        """تست تمام کانفیگ‌های VLESS"""
        logging.info(f"شروع تست {len(configs)} کانفیگ VLESS...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config):
            async with semaphore:
                return await self.test_vless_connection(config)
        
        tasks = [test_single_config(config) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # فیلتر کردن نتایج موفق
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result["success"]:
                valid_results.append(result)
        
        logging.info(f"تست VLESS کامل شد: {len(valid_results)} کانفیگ موفق از {len(configs)}")
        return valid_results
    
    def select_best_vless_configs(self, results: List[Dict]) -> List[str]:
        """انتخاب بهترین کانفیگ‌های VLESS"""
        # مرتب‌سازی بر اساس latency (صعودی - کمترین latency اول)
        sorted_results = sorted(results, key=lambda x: x["latency"] if x["latency"] else float('inf'))
        
        # انتخاب بهترین KEEP_BEST_COUNT کانفیگ
        best_configs = sorted_results[:KEEP_BEST_COUNT]
        
        logging.info(f"بهترین {len(best_configs)} کانفیگ VLESS انتخاب شدند:")
        for i, result in enumerate(best_configs, 1):
            config_hash = result["hash"]
            latency = result["latency"]
            server = result["server_address"]
            logging.info(f"{i}. {config_hash} - Latency: {latency:.1f}ms - Server: {server}")
        
        return [result["config"] for result in best_configs]
    
    def merge_vless_configs(self, new_configs: List[str]) -> Dict[str, int]:
        """ادغام کانفیگ‌های VLESS جدید با موجود"""
        stats = {
            "new_added": 0,
            "duplicates_skipped": 0,
            "invalid_skipped": 0
        }
        
        # اطمینان از وجود دایرکتوری trustlink
        os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
        
        # ایجاد backup از فایل موجود
        if os.path.exists(TRUSTLINK_VLESS_FILE):
            try:
                import shutil
                shutil.copy2(TRUSTLINK_VLESS_FILE, BACKUP_FILE)
                logging.info("Backup از فایل VLESS موجود ایجاد شد")
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
            if not self.is_valid_vless_config(config):
                stats["invalid_skipped"] += 1
                continue
                
            if config in self.existing_configs:
                stats["duplicates_skipped"] += 1
                continue
            
            self.existing_configs.add(config)
            stats["new_added"] += 1
        
        logging.info(f"ادغام VLESS کامل: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری، {stats['invalid_skipped']} نامعتبر")
        return stats
    
    def save_trustlink_vless_file(self):
        """ذخیره فایل trustlink_vless.txt"""
        try:
            os.makedirs(os.path.dirname(TRUSTLINK_VLESS_FILE), exist_ok=True)
            
            # نوشتن اتمیک با فایل موقت
            import tempfile
            fd, tmp_path = tempfile.mkstemp(prefix=".trustlink_vless_", suffix=".tmp", dir=os.path.dirname(TRUSTLINK_VLESS_FILE) or ".")
            
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    # نوشتن header
                    f.write("# فایل کانفیگ‌های VLESS سالم - TrustLink VLESS\n")
                    f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# تعداد کل کانفیگ‌ها: {len(self.existing_configs)}\n")
                    f.write("# " + "="*50 + "\n\n")
                    
                    # نوشتن کانفیگ‌ها
                    for config in sorted(self.existing_configs):
                        f.write(f"{config}\n")
                
                # انتقال فایل موقت به مقصد نهایی
                import shutil
                shutil.move(tmp_path, TRUSTLINK_VLESS_FILE)
                
                logging.info(f"فایل trustlink_vless.txt با موفقیت ذخیره شد: {len(self.existing_configs)} کانفیگ")
                return True
                
            except Exception as e:
                logging.error(f"خطا در نوشتن فایل موقت: {e}")
                try:
                    os.remove(tmp_path)
                except:
                    pass
                return False
                
        except Exception as e:
            logging.error(f"خطا در ذخیره فایل trustlink_vless.txt: {e}")
            return False
    
    def update_metadata(self, stats: Dict[str, int], test_results: List[Dict]):
        """به‌روزرسانی متادیتای برنامه"""
        now = datetime.now().isoformat()
        
        working_count = len([r for r in test_results if r["success"]])
        failed_count = len([r for r in test_results if not r["success"]])
        
        self.metadata.update({
            "last_update": now,
            "total_tests": self.metadata.get("total_tests", 0) + 1,
            "total_configs": len(self.existing_configs),
            "working_configs": working_count,
            "failed_configs": failed_count,
            "last_vless_source": VLESS_SOURCE_FILE,
            "last_stats": {
                "new_added": stats["new_added"],
                "duplicates_skipped": stats["duplicates_skipped"],
                "invalid_skipped": stats["invalid_skipped"],
                "working_configs": working_count,
                "failed_configs": failed_count,
                "timestamp": now
            }
        })
        
        self.save_metadata()
    
    async def run_vless_update(self) -> bool:
        """اجرای یک دور کامل به‌روزرسانی VLESS"""
        try:
            logging.info("=" * 60)
            logging.info("🚀 شروع به‌روزرسانی TrustLink VLESS")
            logging.info("=" * 60)
            
            # بارگذاری کانفیگ‌های موجود
            self.load_existing_configs()
            
            # بارگذاری کانفیگ‌های VLESS از فایل منبع
            source_configs = self.load_vless_source_configs()
            if not source_configs:
                logging.warning("هیچ کانفیگ VLESS جدیدی از فایل منبع بارگذاری نشد")
                return False
            
            # ایجاد session
            await self.create_session()
            
            # تست تمام کانفیگ‌های VLESS
            test_results = await self.test_all_vless_configs(source_configs)
            if not test_results:
                logging.warning("هیچ کانفیگ VLESS موفقی یافت نشد")
                return False
            
            # انتخاب بهترین کانفیگ‌های VLESS
            best_configs = self.select_best_vless_configs(test_results)
            
            # ادغام کانفیگ‌ها
            stats = self.merge_vless_configs(best_configs)
            
            # ذخیره فایل
            if self.save_trustlink_vless_file():
                # به‌روزرسانی متادیتا
                self.update_metadata(stats, test_results)
                
                logging.info("✅ به‌روزرسانی VLESS با موفقیت انجام شد")
                logging.info(f"📊 آمار: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری")
                logging.info(f"🔗 کانفیگ‌های VLESS سالم: {len(best_configs)}")
                return True
            else:
                logging.error("❌ خطا در ذخیره فایل VLESS")
                return False
                
        except Exception as e:
            logging.error(f"خطا در اجرای به‌روزرسانی VLESS: {e}")
            return False
        finally:
            await self.close_session()
    
    def get_status(self) -> Dict:
        """دریافت وضعیت فعلی برنامه"""
        return {
            "total_configs": len(self.existing_configs),
            "last_update": self.metadata.get("last_update", "نامشخص"),
            "total_tests": self.metadata.get("total_tests", 0),
            "working_configs": self.metadata.get("working_configs", 0),
            "failed_configs": self.metadata.get("failed_configs", 0),
            "file_size_kb": os.path.getsize(TRUSTLINK_VLESS_FILE) / 1024 if os.path.exists(TRUSTLINK_VLESS_FILE) else 0,
            "backup_exists": os.path.exists(BACKUP_FILE)
        }

async def run_vless_tester():
    """اجرای تستر VLESS"""
    setup_logging()
    
    logging.info("🚀 راه‌اندازی TrustLink VLESS Tester")
    
    manager = VLESSManager()
    
    try:
        # اجرای یک دور به‌روزرسانی با timeout
        async with asyncio.timeout(300):  # timeout 5 دقیقه
            success = await manager.run_vless_update()
        
        if success:
            status = manager.get_status()
            logging.info("📈 وضعیت نهایی VLESS:")
            for key, value in status.items():
                logging.info(f"  {key}: {value}")
        else:
            logging.error("❌ به‌روزرسانی VLESS ناموفق بود")
            
    except asyncio.TimeoutError:
        logging.error("⏰ timeout: برنامه VLESS بیش از 5 دقیقه طول کشید")
    except KeyboardInterrupt:
        logging.info("برنامه VLESS توسط کاربر متوقف شد")
    except Exception as e:
        logging.error(f"خطای غیرمنتظره در VLESS: {e}")
    finally:
        await manager.close_session()

def schedule_vless_tester():
    """تنظیم اجرای خودکار هر ساعت"""
    logging.info("⏰ تنظیم اجرای خودکار هر ساعت برای VLESS Tester")
    
    # اجرای اولیه
    schedule.every().hour.do(lambda: asyncio.run(run_vless_tester()))
    
    # اجرای فوری در شروع
    schedule.every().minute.do(lambda: asyncio.run(run_vless_tester())).until("23:59")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # بررسی هر دقیقه
        except KeyboardInterrupt:
            logging.info("برنامه VLESS Tester متوقف شد")
            break
        except Exception as e:
            logging.error(f"خطا در اجرای خودکار: {e}")
            time.sleep(60)

async def main():
    """تابع اصلی برنامه"""
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # حالت خودکار
        schedule_vless_tester()
    else:
        # اجرای یکباره
        await run_vless_tester()

if __name__ == "__main__":
    asyncio.run(main())
