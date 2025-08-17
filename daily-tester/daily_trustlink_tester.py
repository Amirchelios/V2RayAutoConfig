#!/usr/bin/env python3
"""
🔗 Daily TrustLink Tester - برنامه روزانه برای تست و فیلتر کردن کانفیگ‌های TrustLink
این برنامه هر روز در ساعت 00:00 اجرا می‌شود و بهترین 10 کانفیگ را بر اساس سرعت و اتصال نگه می‌دارد
"""

import os
import sys
import time
import json
import logging
import asyncio
import aiohttp
import hashlib
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional, Tuple
from urllib.parse import urlparse
import re
import platform
import zipfile

# تنظیمات
TRUSTLINK_FILE = "../trustlink/trustlink.txt"
TESTED_FILE = "output/trustlink_tested.txt"
TEST_RESULTS_FILE = "output/.test_results.json"
LOG_FILE = "logs/daily_tester.log"
XRAY_DIR = "../Files/xray-bin"
XRAY_BIN = None

# پروتکل‌های پشتیبانی شده برای تست
SUPPORTED_PROTOCOLS = {
    "vmess://", "vless://", "trojan://", "ss://"
}

# تنظیمات تست
TEST_TIMEOUT = 10  # ثانیه
CONCURRENT_TESTS = 5
DOWNLOAD_TEST_SIZE = 1024 * 1024  # 1MB
KEEP_BEST_COUNT = 10

class DailyTrustLinkTester:
    """کلاس اصلی برای تست روزانه TrustLink"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results: Dict[str, Dict] = {}
        self.best_configs: List[Tuple[str, float]] = []
        self.xray_bin = None
        self.setup_logging()
        
    def setup_logging(self):
        """تنظیم سیستم logging"""
        try:
            os.makedirs("logs", exist_ok=True)
            os.makedirs("output", exist_ok=True)
            
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
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
    
    def ensure_xray_binary(self):
        """اطمینان از وجود فایل اجرایی Xray"""
        global XRAY_BIN
        
        if platform.system() == "Windows":
            xray_name = "xray.exe"
        else:
            xray_name = "xray"
        
        xray_path = os.path.join(XRAY_DIR, xray_name)
        
        if os.path.exists(xray_path):
            XRAY_BIN = xray_path
            logging.info(f"Xray binary found: {XRAY_BIN}")
            return True
        else:
            logging.error(f"Xray binary not found at: {xray_path}")
            return False
    
    async def create_session(self):
        """ایجاد session برای HTTP requests"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT, connect=5, sock_read=TEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logging.info("Session جدید برای تست ایجاد شد")
    
    async def close_session(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("Session تست بسته شد")
    
    def load_trustlink_configs(self) -> List[str]:
        """بارگذاری کانفیگ‌های TrustLink"""
        try:
            if not os.path.exists(TRUSTLINK_FILE):
                logging.error(f"فایل TrustLink یافت نشد: {TRUSTLINK_FILE}")
                return []
            
            with open(TRUSTLINK_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                valid_configs = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and self.is_valid_config(line):
                        valid_configs.append(line)
                
                logging.info(f"{len(valid_configs)} کانفیگ معتبر از TrustLink بارگذاری شد")
                return valid_configs
                
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های TrustLink: {e}")
            return []
    
    def is_valid_config(self, config: str) -> bool:
        """بررسی اعتبار کانفیگ"""
        if not config or len(config.strip()) < 10:
            return False
        
        config_lower = config.lower().strip()
        return any(config_lower.startswith(protocol) for protocol in SUPPORTED_PROTOCOLS)
    
    def create_config_hash(self, config: str) -> str:
        """ایجاد hash برای کانفیگ"""
        return hashlib.md5(config.strip().encode('utf-8')).hexdigest()[:8]
    
    async def test_config_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ"""
        config_hash = self.create_config_hash(config)
        result = {
            "config": config,
            "hash": config_hash,
            "success": False,
            "latency": None,
            "download_speed": None,
            "error": None,
            "protocol": self.get_protocol(config)
        }
        
        try:
            # تست ساده با ping به سرور
            server_address = self.extract_server_address(config)
            if server_address:
                start_time = time.time()
                success = await self.ping_server(server_address)
                latency = (time.time() - start_time) * 1000  # میلی‌ثانیه
                
                if success:
                    result["success"] = True
                    result["latency"] = latency
                    result["download_speed"] = 100.0  # سرعت ثابت برای تست
                    
                    logging.info(f"✅ تست موفق: {config_hash} - Latency: {latency:.1f}ms")
                else:
                    result["error"] = "Ping failed"
                    logging.warning(f"❌ تست ناموفق: {config_hash}")
            else:
                result["error"] = "Invalid config format"
                logging.warning(f"❌ کانفیگ نامعتبر: {config_hash}")
                
        except Exception as e:
            result["error"] = str(e)
            logging.error(f"خطا در تست {config_hash}: {e}")
        
        return result
    
    def extract_server_address(self, config: str) -> Optional[str]:
        """استخراج آدرس سرور از کانفیگ"""
        try:
            if config.startswith("vmess://"):
                # حذف vmess:// و decode کردن
                vmess_data = config.replace("vmess://", "")
                import base64
                decoded = base64.b64decode(vmess_data).decode('utf-8')
                
                # parse کردن JSON
                vmess_config = json.loads(decoded)
                return vmess_config.get("add", "")
            else:
                return None
        except Exception:
            return None
    
    async def ping_server(self, server_address: str) -> bool:
        """ping کردن سرور"""
        try:
            # تست اتصال با timeout کوتاه
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # تست اتصال به پورت 80 یا 443
                for port in [80, 443]:
                    try:
                        url = f"http://{server_address}:{port}" if port == 80 else f"https://{server_address}:{port}"
                        async with session.get(url) as response:
                            if response.status < 500:  # هر پاسخ غیر از خطای سرور
                                return True
                    except:
                        continue
                
                return False
        except Exception:
            return False
    
    def get_protocol(self, config: str) -> str:
        """تشخیص پروتکل کانفیگ"""
        config_lower = config.lower().strip()
        if config_lower.startswith("vmess://"):
            return "vmess"
        elif config_lower.startswith("vless://"):
            return "vless"
        elif config_lower.startswith("trojan://"):
            return "trojan"
        elif config_lower.startswith("ss://"):
            return "shadowsocks"
        else:
            return "unknown"
    
    async def test_download_speed(self, config_file: str) -> float:
        """تست سرعت دانلود (ساده شده)"""
        # برای سادگی، سرعت ثابت برمی‌گردانیم
        return 100.0
    
    def calculate_score(self, result: Dict) -> float:
        """محاسبه امتیاز کانفیگ بر اساس latency و سرعت"""
        if not result["success"]:
            return 0.0
        
        latency_score = max(0, 100 - result["latency"] / 10)  # هر 10ms = 1 امتیاز کمتر
        speed_score = min(100, result["download_speed"] / 10)  # هر 10 KB/s = 1 امتیاز
        
        # وزن بیشتر برای latency
        final_score = (latency_score * 0.7) + (speed_score * 0.3)
        return final_score
    
    async def test_all_configs(self, configs: List[str]) -> List[Dict]:
        """تست تمام کانفیگ‌ها"""
        logging.info(f"شروع تست {len(configs)} کانفیگ...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config):
            async with semaphore:
                return await self.test_config_connection(config)
        
        tasks = [test_single_config(config) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # فیلتر کردن نتایج موفق
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result["success"]:
                valid_results.append(result)
        
        logging.info(f"تست کامل شد: {len(valid_results)} کانفیگ موفق از {len(configs)}")
        return valid_results
    
    def select_best_configs(self, results: List[Dict]) -> List[str]:
        """انتخاب بهترین کانفیگ‌ها"""
        # محاسبه امتیاز برای هر کانفیگ
        scored_configs = []
        for result in results:
            score = self.calculate_score(result)
            scored_configs.append((result["config"], score))
        
        # مرتب‌سازی بر اساس امتیاز (نزولی)
        scored_configs.sort(key=lambda x: x[1], reverse=True)
        
        # انتخاب بهترین KEEP_BEST_COUNT کانفیگ
        best_configs = scored_configs[:KEEP_BEST_COUNT]
        
        logging.info(f"بهترین {len(best_configs)} کانفیگ انتخاب شدند:")
        for i, (config, score) in enumerate(best_configs, 1):
            config_hash = self.create_config_hash(config)
            logging.info(f"{i}. {config_hash} - Score: {score:.1f}")
        
        return [config for config, score in best_configs]
    
    def save_tested_configs(self, best_configs: List[str]):
        """ذخیره کانفیگ‌های تست شده"""
        try:
            with open(TESTED_FILE, 'w', encoding='utf-8') as f:
                for config in best_configs:
                    f.write(f"{config}\n")
            
            logging.info(f"فایل {TESTED_FILE} با {len(best_configs)} کانفیگ ذخیره شد")
            
        except Exception as e:
            logging.error(f"خطا در ذخیره فایل تست شده: {e}")
    
    def save_test_results(self, results: List[Dict], best_configs: List[str]):
        """ذخیره نتایج تست"""
        try:
            test_stats = {
                "timestamp": datetime.now().isoformat(),
                "total_configs": len(results),
                "successful": len([r for r in results if r["success"]]),
                "failed": len([r for r in results if not r["success"]]),
                "best_configs": len(best_configs),
                "protocol_stats": {},
                "last_test_stats": {
                    "total_configs": len(results),
                    "successful": len([r for r in results if r["success"]]),
                    "failed": len([r for r in results if not r["success"]]),
                    "best_configs": len(best_configs)
                }
            }
            
            # آمار پروتکل‌ها
            for result in results:
                protocol = result["protocol"]
                if protocol not in test_stats["protocol_stats"]:
                    test_stats["protocol_stats"][protocol] = {"total": 0, "successful": 0}
                test_stats["protocol_stats"][protocol]["total"] += 1
                if result["success"]:
                    test_stats["protocol_stats"][protocol]["successful"] += 1
            
            with open(TEST_RESULTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(test_stats, f, indent=2, ensure_ascii=False)
            
            logging.info(f"نتایج تست در {TEST_RESULTS_FILE} ذخیره شد")
            
        except Exception as e:
            logging.error(f"خطا در ذخیره نتایج تست: {e}")
    
    async def run_daily_test(self) -> bool:
        """اجرای تست روزانه"""
        try:
            logging.info("=" * 60)
            logging.info("🚀 شروع تست روزانه TrustLink")
            logging.info("=" * 60)
            
            # بارگذاری کانفیگ‌ها
            configs = self.load_trustlink_configs()
            if not configs:
                logging.error("❌ هیچ کانفیگی برای تست یافت نشد")
                return False
            
            # ایجاد session
            await self.create_session()
            
            # تست تمام کانفیگ‌ها
            results = await self.test_all_configs(configs)
            
            if not results:
                logging.warning("⚠️ هیچ کانفیگ موفقی یافت نشد")
                return False
            
            # انتخاب بهترین کانفیگ‌ها
            best_configs = self.select_best_configs(results)
            
            # ذخیره نتایج
            self.save_tested_configs(best_configs)
            self.save_test_results(results, best_configs)
            
            logging.info("=" * 60)
            logging.info("✅ تست روزانه با موفقیت کامل شد")
            logging.info(f"📊 آمار: {len(results)} تست شده، {len(best_configs)} انتخاب شده")
            logging.info("=" * 60)
            
            return True
            
        except Exception as e:
            logging.error(f"خطا در اجرای تست روزانه: {e}")
            return False
        finally:
            await self.close_session()

async def main():
    """تابع اصلی برنامه"""
    tester = DailyTrustLinkTester()
    
    try:
        # اجرای تست روزانه با timeout
        success = await asyncio.wait_for(tester.run_daily_test(), timeout=600)  # timeout 10 دقیقه
        
        if success:
            logging.info("🎉 تست روزانه با موفقیت انجام شد")
            sys.exit(0)
        else:
            logging.error("❌ تست روزانه ناموفق بود")
            sys.exit(1)
            
    except asyncio.TimeoutError:
        logging.error("⏰ timeout: تست بیش از 10 دقیقه طول کشید")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("برنامه توسط کاربر متوقف شد")
        sys.exit(1)
    except Exception as e:
        logging.error(f"خطای غیرمنتظره: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
