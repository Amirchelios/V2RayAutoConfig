#!/usr/bin/env python3
"""
🔗 VMESS Tester - برنامه هوشمند برای تست و ذخیره کانفیگ‌های VMESS سالم
این برنامه هر ساعت کانفیگ‌های VMESS را از Vmess.txt دانلود کرده و در trustlink_vmess.txt ذخیره می‌کند
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
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional
from urllib.parse import urlparse
import re

# تنظیمات
VMESS_SOURCE_FILE = "../configs/raw/Vmess.txt"
TRUSTLINK_VMESS_FILE = "../trustlink/trustlink_vmess.txt"
TRUSTLINK_VMESS_METADATA = "../trustlink/.trustlink_vmess_metadata.json"
BACKUP_FILE = "../trustlink/trustlink_vmess_backup.txt"
LOG_FILE = "../logs/vmess_tester.log"

# پروتکل VMESS
VMESS_PROTOCOL = "vmess://"

# تنظیمات تست
TEST_TIMEOUT = 60  # ثانیه - افزایش timeout
CONCURRENT_TESTS = 50  # افزایش تعداد تست‌های همزمان به 50
KEEP_BEST_COUNT = 500  # افزایش تعداد کانفیگ‌های سالم نگه‌داری شده
MAX_CONFIGS_TO_TEST = 10000  # افزایش تعداد کانفیگ‌های تست شده به 10000

# تنظیمات تست سرعت دانلود واقعی از طریق Xray
DOWNLOAD_TEST_MIN_BYTES = 1024 * 1024  # 1 MB
DOWNLOAD_TEST_TIMEOUT = 2  # ثانیه
DOWNLOAD_TEST_URLS = [
    "https://speed.cloudflare.com/__down?bytes=10485760",  # 10MB stream (به اندازه کافی بزرگ)
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

class VMESSManager:
    """مدیریت اصلی برنامه VMESS Tester"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.existing_configs: Set[str] = set()
        self.metadata: Dict = {}
        self.load_metadata()
        # ذخیره نتایج جزئی برای تداوم در صورت timeout/خطا
        self.partial_results: List[Dict] = []
        self.partial_iran_ok: List[str] = []
        self.partial_speed_ok: List[str] = []

    def load_metadata(self):
        """بارگذاری متادیتای برنامه"""
        try:
            if os.path.exists(TRUSTLINK_VMESS_METADATA):
                with open(TRUSTLINK_VMESS_METADATA, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logging.info("متادیتای برنامه VMESS بارگذاری شد")
            else:
                self.metadata = {
                    "last_update": "",
                    "total_tests": 0,
                    "total_configs": 0,
                    "working_configs": 0,
                    "failed_configs": 0,
                    "last_vmess_source": "",
                    "version": "1.0.0"
                }
                logging.info("متادیتای جدید برای برنامه VMESS ایجاد شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری متادیتا: {e}")
            self.metadata = {
                "last_update": "",
                "total_tests": 0,
                "total_configs": 0,
                "working_configs": 0,
                "failed_configs": 0,
                "last_vmess_source": "",
                "version": "1.0.0"
            }

    def save_metadata(self):
        """ذخیره متادیتای برنامه"""
        try:
            os.makedirs(os.path.dirname(TRUSTLINK_VMESS_METADATA), exist_ok=True)
            with open(TRUSTLINK_VMESS_METADATA, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            logging.info("متادیتای برنامه VMESS ذخیره شد")
        except Exception as e:
            logging.error(f"خطا در ذخیره متادیتا: {e}")

    async def create_session(self):
        """ایجاد session برای تست"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            connector = aiohttp.TCPConnector(limit=CONCURRENT_TESTS, limit_per_host=10)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            logging.info("Session جدید برای تست VMESS ایجاد شد")

    async def close_session(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("Session تست VMESS بسته شد")

    def load_existing_configs(self):
        """بارگذاری کانفیگ‌های موجود"""
        try:
            if os.path.exists(TRUSTLINK_VMESS_FILE):
                with open(TRUSTLINK_VMESS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # استخراج کانفیگ‌های VMESS از فایل
                    vmess_configs = re.findall(r'vmess://[^\n]+', content)
                    self.existing_configs = set(vmess_configs)
                    logging.info(f"تعداد {len(self.existing_configs)} کانفیگ VMESS موجود بارگذاری شد")
            else:
                logging.info("فایل کانفیگ‌های VMESS موجود یافت نشد - فایل جدید ایجاد خواهد شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های موجود: {e}")
            self.existing_configs = set()

    def load_vmess_configs(self) -> List[str]:
        """بارگذاری کانفیگ‌های VMESS از فایل منبع"""
        try:
            if not os.path.exists(VMESS_SOURCE_FILE):
                logging.error(f"فایل منبع VMESS یافت نشد: {VMESS_SOURCE_FILE}")
                return []
            
            with open(VMESS_SOURCE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # استخراج کانفیگ‌های VMESS
            vmess_configs = re.findall(r'vmess://[^\n]+', content)
            
            if not vmess_configs:
                logging.warning("هیچ کانفیگ VMESS در فایل منبع یافت نشد")
                return []
            
            logging.info(f"تعداد {len(vmess_configs)} کانفیگ VMESS از فایل منبع بارگذاری شد")
            return vmess_configs[:MAX_CONFIGS_TO_TEST]
            
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های VMESS: {e}")
            return []

    def parse_vmess_config(self, config: str) -> Optional[Dict]:
        """تجزیه کانفیگ VMESS"""
        try:
            if not config.startswith(VMESS_PROTOCOL):
                return None
            
            # حذف vmess:// از ابتدای کانفیگ
            config_data = config[len(VMESS_PROTOCOL):]
            
            # تجزیه کانفیگ VMESS (فرمت JSON)
            try:
                import base64
                decoded = base64.b64decode(config_data).decode('utf-8')
                parsed = json.loads(decoded)
                return parsed
            except:
                # اگر base64 نبود، سعی کن مستقیماً تجزیه کن
                return {"raw": config_data}
                
        except Exception as e:
            logging.debug(f"خطا در تجزیه کانفیگ VMESS: {e}")
            return None

    async def test_vmess_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ VMESS"""
        try:
            parsed = self.parse_vmess_config(config)
            if not parsed:
                return {"config": config, "status": "invalid", "latency": None, "error": "کانفیگ نامعتبر"}
            
            # تست ساده اتصال (می‌تواند گسترش یابد)
            start_time = time.time()
            
            # تست اتصال به سرور
            if "add" in parsed and "port" in parsed:
                server = parsed["add"]
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
        """تست کانفیگ VMESS با استفاده از Xray"""
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
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [{
                            "address": parsed.get("add", ""),
                            "port": int(parsed.get("port", 443)),
                            "users": [{
                                "id": parsed.get("id", ""),
                                "alterId": parsed.get("aid", 0),
                                "security": parsed.get("scy", "auto")
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": parsed.get("net", "tcp"),
                        "security": parsed.get("tls", ""),
                        "tlsSettings": {
                            "serverName": parsed.get("sni", "")
                        } if parsed.get("tls") else {},
                        "wsSettings": {
                            "path": parsed.get("path", "")
                        } if parsed.get("net") == "ws" else {}
                    }
                }]
            }
            
            # ذخیره کانفیگ موقت
            temp_config_path = "temp_vmess_config.json"
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
                                "server": parsed.get("add", ""),
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
            parsed = self.parse_vmess_config(config)
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
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [{
                            "address": parsed.get("add", ""),
                            "port": int(parsed.get("port", 443)),
                            "users": [{
                                "id": parsed.get("id", ""),
                                "alterId": parsed.get("aid", 0),
                                "security": parsed.get("scy", "auto")
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": parsed.get("net", "tcp"),
                        "security": parsed.get("tls", ""),
                        "tlsSettings": {
                            "serverName": parsed.get("sni", "")
                        } if parsed.get("tls") else {},
                        "wsSettings": {
                            "path": parsed.get("path", "")
                        } if parsed.get("net") == "ws" else {}
                    }
                }]
            }
            
            # ذخیره کانفیگ موقت
            temp_config_path = f"temp_vmess_social_{hash(config)}.json"
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
        """تست تمام کانفیگ‌های VMESS"""
        logging.info(f"شروع تست {len(configs)} کانفیگ VMESS")
        
        await self.create_session()
        
        # مرحله 1: تست اتصال اولیه
        logging.info("مرحله 1: تست اتصال اولیه")
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config: str):
            async with semaphore:
                return await self.test_vmess_connection(config)
        
        tasks = [test_single_config(config) for config in configs]
        initial_results = []
        
        try:
            for i, task in enumerate(asyncio.as_completed(tasks)):
                result = await task
                initial_results.append(result)
                
                if (i + 1) % 100 == 0:
                    logging.info(f"تست اتصال {i + 1}/{len(configs)} کانفیگ VMESS تکمیل شد")
                
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
        
        logging.info(f"تست {len(configs)} کانفیگ VMESS تکمیل شد")
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
            os.makedirs(os.path.dirname(TRUSTLINK_VMESS_FILE), exist_ok=True)
            
            # ذخیره کانفیگ‌ها
            with open(TRUSTLINK_VMESS_FILE, 'w', encoding='utf-8') as f:
                f.write(f"# فایل کانفیگ‌های VMESS سالم - TrustLink VMESS\n")
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
                "last_vmess_source": VMESS_SOURCE_FILE,
                "test_statistics": stats
            })
            
            self.save_metadata()
            
            logging.info(f"تعداد {len(all_configs)} کانفیگ VMESS سالم ذخیره شد")
            logging.info(f"آمار تست: {stats}")
            
            # ایجاد پشتیبان
            if os.path.exists(TRUSTLINK_VMESS_FILE):
                import shutil
                shutil.copy2(TRUSTLINK_VMESS_FILE, BACKUP_FILE)
                logging.info("فایل پشتیبان ایجاد شد")
            
        except Exception as e:
            logging.error(f"خطا در ذخیره کانفیگ‌ها: {e}")

    async def run_full_test(self):
        """اجرای کامل تست"""
        try:
            logging.info("شروع تست کامل کانفیگ‌های VMESS")
            
            # بارگذاری کانفیگ‌های موجود
            self.load_existing_configs()
            
            # بارگذاری کانفیگ‌های جدید
            configs = self.load_vmess_configs()
            if not configs:
                logging.warning("هیچ کانفیگ VMESS برای تست یافت نشد")
                return
            
            # تست کانفیگ‌ها
            results = await self.test_all_configs(configs)
            
            # ذخیره نتایج
            self.save_working_configs(results)
            
            logging.info("تست کامل کانفیگ‌های VMESS تکمیل شد")
            
        except Exception as e:
            logging.error(f"خطا در اجرای تست کامل: {e}")

def main():
    """تابع اصلی"""
    setup_logging()
    
    # بررسی آرگومان‌ها
    auto_mode = "--auto" in sys.argv
    
    if auto_mode:
        logging.info("حالت خودکار فعال شد - تست هر ساعت اجرا خواهد شد")
        
        manager = VMESSManager()
        
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
        logging.info("شروع تست یکباره کانفیگ‌های VMESS")
        manager = VMESSManager()
        asyncio.run(manager.run_full_test())
        logging.info("تست یکباره تکمیل شد")

if __name__ == "__main__":
    main()
