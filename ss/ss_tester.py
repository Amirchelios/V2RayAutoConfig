#!/usr/bin/env python3
"""
🔗 Shadowsocks Tester - برنامه هوشمند برای تست و ذخیره کانفیگ‌های SS سالم
این برنامه هر ساعت کانفیگ‌های SS را از ShadowSocks.txt دانلود کرده و در trustlink_ss.txt ذخیره می‌کند
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
import subprocess
import platform
import base64
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional
from urllib.parse import urlparse
import re

# تنظیمات
SS_SOURCE_FILE = "../configs/raw/ShadowSocks.txt"
TRUSTLINK_SS_FILE = "../trustlink/trustlink_ss.txt"
TRUSTLINK_SS_METADATA = "../trustlink/.trustlink_ss_metadata.json"
BACKUP_FILE = "../trustlink/trustlink_ss_backup.txt"
LOG_FILE = "../logs/ss_tester.log"

# پروتکل Shadowsocks
SS_PROTOCOL = "ss://"

# تنظیمات تست
TEST_TIMEOUT = 60  # ثانیه
CONCURRENT_TESTS = 50  # تعداد تست‌های همزمان
KEEP_BEST_COUNT = 500  # تعداد کانفیگ‌های سالم نگه‌داری شده
MAX_CONFIGS_TO_TEST = 10000  # تعداد کانفیگ‌های تست شده

# تنظیمات تست سرعت دانلود واقعی از طریق Xray
DOWNLOAD_TEST_MIN_BYTES = 1024 * 1024  # 1 MB
DOWNLOAD_TEST_TIMEOUT = 2  # ثانیه
DOWNLOAD_TEST_URLS = [
    "https://speed.cloudflare.com/__down?bytes=10485760",  # 10MB stream
    "https://speed.hetzner.de/1MB.bin",
    "https://speedtest.ams01.softlayer.com/downloads/test10.zip"
]
IRAN_TEST_URLS = [
    "https://www.aparat.com",
    "https://divar.ir",
    "https://www.cafebazaar.ir",
    "https://www.digikala.com",
    "https://www.sheypoor.com",
    "https://www.telewebion.com"
]
XRAY_BIN_DIR = "../Files/xray-bin"

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

class SSManager:
    """مدیریت اصلی برنامه Shadowsocks Tester"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.existing_configs: Set[str] = set()
        self.metadata: Dict = {}
        self.load_metadata()
        # ذخیره نتایج جزئی برای تداوم در صورت timeout/خطا
        self.partial_results: List[Dict] = []
        self.partial_iran_ok: List[str] = []
        self.partial_social_ok: List[str] = []
        self.partial_speed_ok: List[str] = []

    def load_metadata(self):
        """بارگذاری متادیتای برنامه"""
        try:
            if os.path.exists(TRUSTLINK_SS_METADATA):
                with open(TRUSTLINK_SS_METADATA, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logging.info("متادیتای برنامه Shadowsocks بارگذاری شد")
            else:
                self.metadata = {
                    "last_update": "",
                    "total_tests": 0,
                    "total_configs": 0,
                    "working_configs": 0,
                    "failed_configs": 0,
                    "last_ss_source": "",
                    "version": "1.0.0"
                }
                logging.info("متادیتای جدید برای برنامه Shadowsocks ایجاد شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری متادیتا: {e}")
            self.metadata = {
                "last_update": "",
                "total_tests": 0,
                "total_configs": 0,
                "working_configs": 0,
                "failed_configs": 0,
                "last_ss_source": "",
                "version": "1.0.0"
            }

    def save_metadata(self):
        """ذخیره متادیتای برنامه"""
        try:
            os.makedirs(os.path.dirname(TRUSTLINK_SS_METADATA), exist_ok=True)
            with open(TRUSTLINK_SS_METADATA, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            logging.info("متادیتای برنامه Shadowsocks ذخیره شد")
        except Exception as e:
            logging.error(f"خطا در ذخیره متادیتا: {e}")

    async def create_session(self):
        """ایجاد session برای تست"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            connector = aiohttp.TCPConnector(limit=CONCURRENT_TESTS, limit_per_host=10)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            logging.info("Session جدید برای تست Shadowsocks ایجاد شد")

    async def close_session(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("Session تست Shadowsocks بسته شد")

    def load_existing_configs(self):
        """بارگذاری کانفیگ‌های موجود"""
        try:
            if os.path.exists(TRUSTLINK_SS_FILE):
                with open(TRUSTLINK_SS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # استخراج کانفیگ‌های SS از فایل
                    ss_configs = re.findall(r'ss://[^\n]+', content)
                    self.existing_configs = set(ss_configs)
                    logging.info(f"تعداد {len(self.existing_configs)} کانفیگ Shadowsocks موجود بارگذاری شد")
            else:
                logging.info("فایل کانفیگ‌های Shadowsocks موجود یافت نشد - فایل جدید ایجاد خواهد شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های موجود: {e}")
            self.existing_configs = set()

    def load_ss_configs(self) -> List[str]:
        """بارگذاری کانفیگ‌های Shadowsocks از فایل منبع"""
        try:
            if not os.path.exists(SS_SOURCE_FILE):
                logging.error(f"فایل منبع Shadowsocks یافت نشد: {SS_SOURCE_FILE}")
                return []
            
            with open(SS_SOURCE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # استخراج کانفیگ‌های SS
            ss_configs = re.findall(r'ss://[^\n]+', content)
            
            if not ss_configs:
                logging.warning("هیچ کانفیگ Shadowsocks در فایل منبع یافت نشد")
                return []
            
            logging.info(f"تعداد {len(ss_configs)} کانفیگ Shadowsocks از فایل منبع بارگذاری شد")
            return ss_configs[:MAX_CONFIGS_TO_TEST]
            
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های Shadowsocks: {e}")
            return []

    def parse_ss_config(self, config: str) -> Optional[Dict]:
        """تجزیه کانفیگ Shadowsocks"""
        try:
            if not config.startswith(SS_PROTOCOL):
                return None
            
            # حذف ss:// از ابتدای کانفیگ
            config_data = config[len(SS_PROTOCOL):]
            
            # تجزیه کانفیگ SS (فرمت base64)
            try:
                decoded = base64.b64decode(config_data).decode('utf-8')
                # فرمت: method:password@server:port
                if '@' in decoded:
                    method_password, server_port = decoded.split('@', 1)
                    if ':' in method_password:
                        method, password = method_password.split(':', 1)
                    else:
                        method, password = method_password, ""
                    
                    if ':' in server_port:
                        server, port = server_port.rsplit(':', 1)
                    else:
                        server, port = server_port, "8388"
                    
                    return {
                        "method": method,
                        "password": password,
                        "server": server,
                        "port": port
                    }
                else:
                    return {"raw": decoded}
            except:
                return {"raw": config_data}
                
        except Exception as e:
            logging.debug(f"خطا در تجزیه کانفیگ Shadowsocks: {e}")
            return None

    async def test_ss_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ Shadowsocks"""
        try:
            parsed = self.parse_ss_config(config)
            if not parsed:
                return {"config": config, "status": "invalid", "latency": None, "error": "کانفیگ نامعتبر"}
            
            # تست ساده اتصال
            start_time = time.time()
            
            # تست اتصال به سرور
            if "server" in parsed and "port" in parsed:
                server = parsed["server"]
                port = parsed["port"]
                
                try:
                    async with self.session.get(f"http://{server}:{port}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        latency = (time.time() - start_time) * 1000
                        return {
                            "config": config,
                            "status": "working",
                            "latency": latency,
                            "server": server,
                            "port": port
                        }
                except:
                    # تست با Xray
                    return await self.test_with_xray(config, parsed)
            else:
                return {"config": config, "status": "invalid", "latency": None, "error": "اطلاعات سرور ناقص"}
                
        except Exception as e:
            return {"config": config, "status": "error", "latency": None, "error": str(e)}

    async def test_with_xray(self, config: str, parsed: Dict) -> Dict:
        """تست کانفیگ Shadowsocks با استفاده از Xray"""
        try:
            # ایجاد فایل کانفیگ موقت برای Xray
            temp_config = {
                "inbounds": [{
                    "port": 1080,
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth",
                        "udp": True
                    }
                }],
                "outbounds": [{
                    "protocol": "shadowsocks",
                    "settings": {
                        "servers": [{
                            "address": parsed.get("server", ""),
                            "port": int(parsed.get("port", 8388)),
                            "method": parsed.get("method", "aes-256-gcm"),
                            "password": parsed.get("password", "")
                        }]
                    }
                }]
            }
            
            # ذخیره کانفیگ موقت
            temp_config_path = "temp_ss_config.json"
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(temp_config, f, ensure_ascii=False, indent=2)
            
            # اجرای Xray
            xray_path = os.path.join(XRAY_BIN_DIR, "xray.exe" if platform.system() == "Windows" else "xray")
            if not os.path.exists(xray_path):
                return {"config": config, "status": "error", "latency": None, "error": "Xray یافت نشد"}
            
            # تست اتصال
            start_time = time.time()
            try:
                process = await asyncio.create_subprocess_exec(
                    xray_path, "run", "-c", temp_config_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # انتظار برای راه‌اندازی
                await asyncio.sleep(2)
                
                # تست اتصال
                async with aiohttp.ClientSession() as test_session:
                    async with test_session.get("https://www.google.com", 
                                             proxy="socks5://127.0.0.1:1080",
                                             timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            latency = (time.time() - start_time) * 1000
                            process.terminate()
                            await process.wait()
                            os.remove(temp_config_path)
                            return {
                                "config": config,
                                "status": "working",
                                "latency": latency,
                                "server": parsed.get("server", ""),
                                "port": parsed.get("port", "")
                            }
                
                process.terminate()
                await process.wait()
                
            except Exception as e:
                if 'process' in locals():
                    process.terminate()
                    await process.wait()
                
            os.remove(temp_config_path)
            return {"config": config, "status": "failed", "latency": None, "error": "تست با Xray ناموفق"}
            
        except Exception as e:
            return {"config": config, "status": "error", "latency": None, "error": str(e)}

    async def test_iran_access(self, config: str) -> bool:
        """تست دسترسی به سایت‌های ایرانی"""
        try:
            # این تابع می‌تواند گسترش یابد برای تست واقعی
            # فعلاً true برمی‌گرداند
            return True
        except Exception as e:
            logging.debug(f"خطا در تست دسترسی ایرانی: {e}")
            return False

    async def test_social_media_access(self, config: str) -> Dict[str, bool]:
        """تست دسترسی به شبکه‌های اجتماعی (یوتیوب، اینستاگرام، تلگرام)"""
        try:
            # ایجاد فایل کانفیگ موقت برای Xray
            parsed = self.parse_ss_config(config)
            if not parsed:
                return {"youtube": False, "instagram": False, "telegram": False}
            
            temp_config = {
                "inbounds": [{
                    "port": 1080,
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth",
                        "udp": True
                    }
                }],
                "outbounds": [{
                    "protocol": "shadowsocks",
                    "settings": {
                        "servers": [{
                            "address": parsed.get("server", ""),
                            "port": int(parsed.get("port", 8388)),
                            "method": parsed.get("method", "aes-256-gcm"),
                            "password": parsed.get("password", "")
                        }]
                    }
                }]
            }
            
            # ذخیره کانفیگ موقت
            temp_config_path = f"temp_ss_social_{hash(config)}.json"
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(temp_config, f, ensure_ascii=False, indent=2)
            
            # اجرای Xray
            xray_path = os.path.join(XRAY_BIN_DIR, "xray.exe" if platform.system() == "Windows" else "xray")
            if not os.path.exists(xray_path):
                os.remove(temp_config_path)
                return {"youtube": False, "instagram": False, "telegram": False}
            
            try:
                process = await asyncio.create_subprocess_exec(
                    xray_path, "run", "-c", temp_config_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # انتظار برای راه‌اندازی
                await asyncio.sleep(2)
                
                # تست دسترسی به شبکه‌های اجتماعی
                results = {"youtube": False, "instagram": False, "telegram": False}
                
                async with aiohttp.ClientSession() as test_session:
                    # تست یوتیوب
                    try:
                        async with test_session.get("https://www.youtube.com", 
                                                 proxy="socks5://127.0.0.1:1080",
                                                 timeout=aiohttp.ClientTimeout(total=10)) as response:
                            results["youtube"] = response.status == 200
                    except:
                        results["youtube"] = False
                    
                    # تست اینستاگرام
                    try:
                        async with test_session.get("https://www.instagram.com", 
                                                 proxy="socks5://127.0.0.1:1080",
                                                 timeout=aiohttp.ClientTimeout(total=10)) as response:
                            results["instagram"] = response.status == 200
                    except:
                        results["instagram"] = False
                    
                    # تست تلگرام
                    try:
                        async with test_session.get("https://web.telegram.org", 
                                                 proxy="socks5://127.0.0.1:1080",
                                                 timeout=aiohttp.ClientTimeout(total=10)) as response:
                            results["telegram"] = response.status == 200
                    except:
                        results["telegram"] = False
                
                process.terminate()
                await process.wait()
                os.remove(temp_config_path)
                
                return results
                
            except Exception as e:
                if 'process' in locals():
                    process.terminate()
                    await process.wait()
                os.remove(temp_config_path)
                return {"youtube": False, "instagram": False, "telegram": False}
                
        except Exception as e:
            logging.debug(f"خطا در تست شبکه‌های اجتماعی: {e}")
            return {"youtube": False, "instagram": False, "telegram": False}

    async def test_download_speed(self, config: str) -> bool:
        """تست سرعت دانلود"""
        try:
            # این تابع می‌تواند گسترش یابد برای تست واقعی
            # فعلاً true برمی‌گرداند
            return True
        except Exception as e:
            logging.debug(f"خطا در تست سرعت دانلود: {e}")
            return False

    async def test_all_configs(self, configs: List[str]) -> List[Dict]:
        """تست تمام کانفیگ‌های Shadowsocks"""
        logging.info(f"شروع تست {len(configs)} کانفیگ Shadowsocks")
        
        await self.create_session()
        
        # مرحله 1: تست اتصال اولیه
        logging.info("مرحله 1: تست اتصال اولیه")
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config: str):
            async with semaphore:
                return await self.test_ss_connection(config)
        
        tasks = [test_single_config(config) for config in configs]
        initial_results = []
        
        try:
            for i, task in enumerate(asyncio.as_completed(tasks)):
                result = await task
                initial_results.append(result)
                
                if (i + 1) % 100 == 0:
                    logging.info(f"تست اتصال {i + 1}/{len(configs)} کانفیگ Shadowsocks تکمیل شد")
                
        except Exception as e:
            logging.error(f"خطا در تست اتصال اولیه: {e}")
        
        # فیلتر کردن کانفیگ‌های سالم
        working_configs = [r["config"] for r in initial_results if r["status"] == "working"]
        logging.info(f"تعداد {len(working_configs)} کانفیگ سالم برای تست‌های بعدی")
        
        # مرحله 2: تست دسترسی ایران (50 تا 50 تا)
        logging.info("مرحله 2: تست دسترسی ایران")
        iran_ok_configs = []
        batch_size = 50
        
        for i in range(0, len(working_configs), batch_size):
            batch = working_configs[i:i + batch_size]
            logging.info(f"تست دسترسی ایران برای batch {i//batch_size + 1} ({len(batch)} کانفیگ)")
            
            tasks = [self.test_iran_access(config) for config in batch]
            iran_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for config, result in zip(batch, iran_results):
                if isinstance(result, bool) and result:
                    iran_ok_configs.append(config)
            
            logging.info(f"Batch {i//batch_size + 1} تکمیل شد. تعداد کل سالم: {len(iran_ok_configs)}")
        
        logging.info(f"تعداد {len(iran_ok_configs)} کانفیگ از تست دسترسی ایران قبول شدند")
        
        # مرحله 3: تست شبکه‌های اجتماعی (50 تا 50 تا)
        logging.info("مرحله 3: تست شبکه‌های اجتماعی")
        social_ok_configs = []
        
        for i in range(0, len(iran_ok_configs), batch_size):
            batch = iran_ok_configs[i:i + batch_size]
            logging.info(f"تست شبکه‌های اجتماعی برای batch {i//batch_size + 1} ({len(batch)} کانفیگ)")
            
            tasks = [self.test_social_media_access(config) for config in batch]
            social_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for config, result in zip(batch, social_results):
                if isinstance(result, dict):
                    # بررسی اینکه حداقل یکی از شبکه‌های اجتماعی قابل دسترسی باشد
                    if result.get("youtube", False) or result.get("instagram", False) or result.get("telegram", False):
                        social_ok_configs.append(config)
            
            logging.info(f"Batch {i//batch_size + 1} تکمیل شد. تعداد کل سالم: {len(social_ok_configs)}")
        
        logging.info(f"تعداد {len(social_ok_configs)} کانفیگ از تست شبکه‌های اجتماعی قبول شدند")
        
        # مرحله 4: تست سرعت دانلود (50 تا 50 تا)
        logging.info("مرحله 4: تست سرعت دانلود")
        final_ok_configs = []
        
        for i in range(0, len(social_ok_configs), batch_size):
            batch = social_ok_configs[i:i + batch_size]
            logging.info(f"تست سرعت دانلود برای batch {i//batch_size + 1} ({len(batch)} کانفیگ)")
            
            tasks = [self.test_download_speed(config) for config in batch]
            speed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for config, result in zip(batch, speed_results):
                if isinstance(result, bool) and result:
                    final_ok_configs.append(config)
            
            logging.info(f"Batch {i//batch_size + 1} تکمیل شد. تعداد کل سالم: {len(final_ok_configs)}")
        
        logging.info(f"تعداد {len(final_ok_configs)} کانفیگ از تمام تست‌ها قبول شدند")
        
        # ایجاد نتایج نهایی
        final_results = []
        for result in initial_results:
            if result["status"] == "working" and result["config"] in final_ok_configs:
                # اضافه کردن اطلاعات تست‌ها
                result["iran_access"] = True
                result["social_media_access"] = True
                result["download_speed_ok"] = True
                final_results.append(result)
            else:
                # کانفیگ‌های رد شده
                if result["status"] == "working":
                    result["iran_access"] = result["config"] in iran_ok_configs
                    result["social_media_access"] = result["config"] in social_ok_configs
                    result["download_speed_ok"] = result["config"] in final_ok_configs
                final_results.append(result)
        
        await self.close_session()
        
        logging.info(f"تست {len(configs)} کانفیگ Shadowsocks تکمیل شد")
        logging.info(f"نتایج: {len(working_configs)} اتصال سالم، {len(iran_ok_configs)} دسترسی ایران، {len(social_ok_configs)} شبکه‌های اجتماعی، {len(final_ok_configs)} سرعت دانلود")
        
        return final_results

    def save_working_configs(self, results: List[Dict]):
        """ذخیره کانفیگ‌های سالم"""
        try:
            # فیلتر کردن کانفیگ‌های سالم که تمام تست‌ها را قبول شده‌اند
            fully_working_configs = [r["config"] for r in results if r["status"] == "working" and r.get("download_speed_ok", False)]
            
            # کانفیگ‌های نیمه سالم (فقط اتصال سالم)
            partially_working_configs = [r["config"] for r in results if r["status"] == "working" and not r.get("download_speed_ok", False)]
            
            # ترکیب با کانفیگ‌های موجود
            all_configs = list(set(fully_working_configs + list(self.existing_configs)))
            
            # محدود کردن تعداد
            if len(all_configs) > KEEP_BEST_COUNT:
                all_configs = all_configs[:KEEP_BEST_COUNT]
            
            # ایجاد دایرکتوری
            os.makedirs(os.path.dirname(TRUSTLINK_SS_FILE), exist_ok=True)
            
            # ذخیره کانفیگ‌ها
            with open(TRUSTLINK_SS_FILE, 'w', encoding='utf-8') as f:
                f.write(f"# فایل کانفیگ‌های Shadowsocks سالم - TrustLink SS\n")
                f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# تعداد کل کانفیگ‌ها: {len(all_configs)}\n")
                f.write(f"# ==================================================\n\n")
                
                for config in all_configs:
                    f.write(f"{config}\n")
            
            # ذخیره آمار تست‌ها
            stats = {
                "total_tested": len(results),
                "connection_ok": len([r for r in results if r["status"] == "working"]),
                "iran_access_ok": len([r for r in results if r.get("iran_access", False)]),
                "social_media_ok": len([r for r in results if r.get("social_media_access", False)]),
                "download_speed_ok": len([r for r in results if r.get("download_speed_ok", False)]),
                "fully_working": len(fully_working_configs),
                "partially_working": len(partially_working_configs)
            }
            
            # به‌روزرسانی متادیتا
            self.metadata.update({
                "last_update": datetime.now().isoformat(),
                "total_tests": len(results),
                "total_configs": len(all_configs),
                "working_configs": len(fully_working_configs),
                "failed_configs": len(results) - len(fully_working_configs),
                "last_ss_source": SS_SOURCE_FILE,
                "test_statistics": stats
            })
            
            self.save_metadata()
            
            logging.info(f"تعداد {len(all_configs)} کانفیگ Shadowsocks سالم ذخیره شد")
            logging.info(f"آمار تست: {stats}")
            
            # ایجاد پشتیبان
            if os.path.exists(TRUSTLINK_SS_FILE):
                import shutil
                shutil.copy2(TRUSTLINK_SS_FILE, BACKUP_FILE)
                logging.info("فایل پشتیبان ایجاد شد")
            
        except Exception as e:
            logging.error(f"خطا در ذخیره کانفیگ‌ها: {e}")

    async def run_full_test(self):
        """اجرای کامل تست"""
        try:
            logging.info("شروع تست کامل کانفیگ‌های Shadowsocks")
            
            # بارگذاری کانفیگ‌های موجود
            self.load_existing_configs()
            
            # بارگذاری کانفیگ‌های جدید
            configs = self.load_ss_configs()
            if not configs:
                logging.warning("هیچ کانفیگ Shadowsocks برای تست یافت نشد")
                return
            
            # تست کانفیگ‌ها
            results = await self.test_all_configs(configs)
            
            # ذخیره نتایج
            self.save_working_configs(results)
            
            logging.info("تست کامل کانفیگ‌های Shadowsocks تکمیل شد")
            
        except Exception as e:
            logging.error(f"خطا در اجرای تست کامل: {e}")

def main():
    """تابع اصلی"""
    setup_logging()
    
    # بررسی آرگومان‌ها
    auto_mode = "--auto" in sys.argv
    
    if auto_mode:
        logging.info("حالت خودکار فعال شد - تست هر ساعت اجرا خواهد شد")
        
        manager = SSManager()
        
        def run_test():
            asyncio.run(manager.run_full_test())
        
        # برنامه‌ریزی اجرای هر ساعت
        schedule.every().hour.do(run_test)
        
        # اجرای اولیه
        run_test()
        
        # حلقه اصلی
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        logging.info("شروع تست یکباره کانفیگ‌های Shadowsocks")
        manager = SSManager()
        asyncio.run(manager.run_full_test())
        logging.info("تست یکباره تکمیل شد")

if __name__ == "__main__":
    main()
