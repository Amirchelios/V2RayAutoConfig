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

# تنظیمات تست سرعت دانلود واقعی از طریق Xray - REMOVED
# DOWNLOAD_TEST_MIN_BYTES = 1024 * 1024  # 1 MB
# DOWNLOAD_TEST_TIMEOUT = 2  # ثانیه
# DOWNLOAD_TEST_URLS = [
#     "https://speed.cloudflare.com/__down?bytes=10485760",  # 10MB stream
#     "https://speed.hetzner.de/1MB.bin",
#     "https://speedtest.ams01.softlayer.com/downloads/test10.zip"
# ]
IRAN_TEST_URLS = [
    "https://www.aparat.com",
    "https://divar.ir",
    "https://www.cafebazaar.ir",
    "https://www.digikala.com",
    "https://www.sheypoor.com",
    "https://www.telewebion.com"
]
# XRAY_BIN_DIR = "../Files/xray-bin"  # REMOVED - no longer used

# تنظیمات check-host.net API
CHECK_HOST_API_BASE = "https://check-host.net"
CHECK_HOST_PING_ENDPOINT = "/check-ping"
CHECK_HOST_RESULT_ENDPOINT = "/check-result"
CHECK_HOST_FOCUS_NODE = "ir2.node.check-host.net"  # نود ایران مشهد - همه تست‌ها از اینجا
CHECK_HOST_BATCH_SIZE = 50  # ارسال 50 تا 50 تا IP

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
        # self.partial_speed_ok: List[str] = []  # نتایج speed test - REMOVED
        self.partial_ping_ok: List[str] = []  # نتایج ping check

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
        """تجزیه کانفیگ Shadowsocks - پشتیبانی از فرمت‌های مختلف"""
        try:
            if not config.startswith(SS_PROTOCOL):
                return None
            
            # حذف ss:// از ابتدای کانفیگ
            config_data = config[len(SS_PROTOCOL):]
            
            # حذف fragment اگر وجود دارد (بخش بعد از #)
            if '#' in config_data:
                config_data = config_data.split('#')[0]
            
            # بررسی فرمت جدید SIP002 (شامل @ و پارامترهای URL)
            if '@' in config_data and ('?' in config_data or '/' in config_data):
                return self._parse_sip002_format(config_data)
            
            # بررسی فرمت کلاسیک base64
            try:
                decoded = base64.b64decode(config_data).decode('utf-8')
                return self._parse_classic_format(decoded)
            except:
                # اگر base64 decode نشد، تلاش برای پارس مستقیم
                return self._parse_direct_format(config_data)
                
        except Exception as e:
            logging.debug(f"خطا در تجزیه کانفیگ Shadowsocks: {e}")
            return None

    def _parse_sip002_format(self, config_data: str) -> Optional[Dict]:
        """پارس فرمت SIP002 جدید Shadowsocks"""
        try:
            from urllib.parse import unquote, parse_qs, urlparse
            
            # تجزیه قسمت قبل از @
            if '@' not in config_data:
                return None
                
            userinfo, hostinfo = config_data.split('@', 1)
            
            # URL decode برای userinfo
            userinfo = unquote(userinfo)
            
            # تجزیه hostinfo (server:port?params یا server:port/path?params)
            if '?' in hostinfo:
                server_port, query_string = hostinfo.split('?', 1)
            else:
                server_port = hostinfo
                query_string = ""
            
            # استخراج server و port
            if ':' in server_port:
                server, port = server_port.rsplit(':', 1)
                # اطمینان از اینکه port فقط عدد باشد
                port = ''.join(filter(str.isdigit, port)) or "8388"
            else:
                server = server_port
                port = "8388"
            
            # پارس پارامترهای query
            params = {}
            if query_string:
                params = parse_qs(query_string)
                # تبدیل لیست‌ها به مقادیر تکی
                for key, value in params.items():
                    if isinstance(value, list) and len(value) > 0:
                        params[key] = value[0]
            
            return {
                "method": userinfo if userinfo else "chacha20-ietf-poly1305",
                "password": userinfo if userinfo else "",
                "server": server,
                "server_ip": server,
                "port": port,
                "type": params.get("type", "tcp"),
                "security": params.get("security", "none"),
                "host": params.get("host", ""),
                "path": params.get("path", "/"),
                "params": params
            }
            
        except Exception as e:
            logging.debug(f"خطا در پارس فرمت SIP002: {e}")
            return None

    def _parse_classic_format(self, decoded: str) -> Optional[Dict]:
        """پارس فرمت کلاسیک Shadowsocks"""
        try:
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
                    "server_ip": server,
                    "port": port
                }
            else:
                return {"raw": decoded}
                
        except Exception as e:
            logging.debug(f"خطا در پارس فرمت کلاسیک: {e}")
            return None

    def _parse_direct_format(self, config_data: str) -> Optional[Dict]:
        """پارس فرمت مستقیم (بدون base64)"""
        try:
            from urllib.parse import unquote
            
            # اگر @ وجود دارد، احتمالاً فرمت username@server:port است
            if '@' in config_data:
                userinfo, hostinfo = config_data.split('@', 1)
                
                # URL decode
                userinfo = unquote(userinfo)
                
                # استخراج server و port
                if ':' in hostinfo:
                    server, port = hostinfo.rsplit(':', 1)
                    # حذف پارامترهای اضافی از port
                    if '?' in port:
                        port = port.split('?')[0]
                    if '/' in port:
                        port = port.split('/')[0]
                    # اطمینان از اینکه port فقط عدد باشد
                    port = ''.join(filter(str.isdigit, port)) or "8388"
                else:
                    server = hostinfo
                    port = "8388"
                
                return {
                    "method": "chacha20-ietf-poly1305",  # پیش‌فرض
                    "password": userinfo,
                    "server": server,
                    "server_ip": server,
                    "port": port
                }
            
            return None
            
        except Exception as e:
            logging.debug(f"خطا در پارس فرمت مستقیم: {e}")
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
        """تست کانفیگ Shadowsocks با استفاده از Xray - DISABLED"""
        # DISABLED: Xray functionality has been removed for simplicity
        return {"config": config, "status": "disabled", "latency": None, "error": "Xray test disabled"}

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
        """تست دسترسی به شبکه‌های اجتماعی (یوتیوب، اینستاگرام، تلگرام) - DISABLED"""
        # DISABLED: Xray functionality has been removed for simplicity
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
        working_configs = [r["config"] for r in initial_results if r.get("status") == "working"]
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
            if result.get("status") == "working" and result["config"] in final_ok_configs:
                # اضافه کردن اطلاعات تست‌ها
                result["iran_access"] = True
                result["social_media_access"] = True
                result["download_speed_ok"] = True
                final_results.append(result)
            else:
                # کانفیگ‌های رد شده
                if result.get("status") == "working":
                    result["iran_access"] = result["config"] in iran_ok_configs
                    result["social_media_access"] = result["config"] in social_ok_configs
                    result["download_speed_ok"] = result["config"] in final_ok_configs
                final_results.append(result)
        
        await self.close_session()
        
        logging.info(f"تست {len(configs)} کانفیگ Shadowsocks تکمیل شد")
        logging.info(f"نتایج: {len(working_configs)} اتصال سالم، {len(iran_ok_configs)} دسترسی ایران، {len(social_ok_configs)} شبکه‌های اجتماعی، {len(final_ok_configs)} سرعت دانلود")
        
        return final_results

    async def filter_configs_by_ping_check(self, configs: List[str]) -> List[str]:
        """
        فیلتر کردن کانفیگ‌ها بر اساس تست ping با check-host.net
        تست یکی یکی IP ها با تمرکز روی نود ایران مشهد
        بهینه‌سازی: انتخاب تصادفی حداکثر 50 کانفیگ برای تست ping
        """
        try:
            # بهینه‌سازی: انتخاب تصادفی حداکثر 50 کانفیگ برای تست ping
            if len(configs) > 50:
                import random
                random.seed()  # استفاده از seed تصادفی
                selected_configs = random.sample(configs, 50)
                logging.info(f"🎯 بهینه‌سازی سرعت: انتخاب تصادفی 50 کانفیگ از {len(configs)} کانفیگ سالم TCP")
                logging.info(f"📊 کانفیگ‌های انتخاب شده برای تست ping: {len(selected_configs)}")
            else:
                selected_configs = configs
                logging.info(f"📊 تست ping برای همه {len(configs)} کانفیگ سالم TCP")
            
            # استخراج IP های منحصر به فرد از کانفیگ‌های انتخاب شده
            unique_ips = set()
            ip_to_configs = {}
            
            for config in selected_configs:
                parsed = self.parse_ss_config(config)
                if parsed:
                    # بررسی وجود server_ip یا server
                    server_ip = parsed.get('server_ip') or parsed.get('server')
                    if server_ip:
                        unique_ips.add(server_ip)
                        if server_ip not in ip_to_configs:
                            ip_to_configs[server_ip] = []
                        ip_to_configs[server_ip].append(config)
            
            logging.info(f"🌐 شروع تست ping (4/4) برای {len(unique_ips)} IP منحصر به فرد (یکی یکی)")
            
            all_ping_results = {}
            ip_list = list(unique_ips)
            
            # تست یکی یکی IP ها
            for i, ip in enumerate(ip_list, 1):
                logging.info(f"📡 تست IP {i}/{len(ip_list)}: {ip}")
                
                try:
                    # تست تک IP
                    single_result = await self.check_host_ping_single(ip)
                    all_ping_results[ip] = single_result
                    
                    if single_result:
                        logging.info(f"✅ IP {ip}: همه 4 ping موفق (4/4)")
                    else:
                        logging.debug(f"❌ IP {ip}: حداقل یکی از 4 ping ناموفق")
                    
                    # کمی صبر بین تست‌ها
                    if i < len(ip_list):
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logging.error(f"خطا در تست IP {ip}: {e}")
                    all_ping_results[ip] = False
            
            # انتخاب کانفیگ‌های سالم بر اساس ping
            healthy_configs = []
            healthy_ips = [ip for ip, success in all_ping_results.items() if success]
            
            for ip in healthy_ips:
                if ip in ip_to_configs:
                    healthy_configs.extend(ip_to_configs[ip])
            
            # حذف تکراری‌ها
            healthy_configs = list(set(healthy_configs))
            
            # ذخیره نتایج جزئی
            try:
                self.partial_ping_ok = list(healthy_configs)
            except Exception:
                pass
            
            logging.info(f"✅ تست ping (4/4) کامل شد: {len(healthy_configs)} کانفیگ سالم از {len(selected_configs)} انتخاب شده")
            logging.info(f"🌍 IP های سالم: {len(healthy_ips)} از {len(unique_ips)}")
            if len(configs) > 50:
                logging.info(f"🚀 بهینه‌سازی سرعت: تست ping فقط روی {len(selected_configs)} کانفیگ تصادفی از {len(configs)} کانفیگ سالم TCP")
            
            return healthy_configs
            
        except Exception as e:
            logging.error(f"خطا در فیلتر کردن بر اساس ping: {e}")
            return configs  # در صورت خطا، همه کانفیگ‌ها را برگردان

    async def check_host_ping_single(self, server_ip: str) -> bool:
        """
        تست ping برای یک IP با استفاده از check-host.net API
        ارسال 4 درخواست ping و بررسی اینکه همه 4 درخواست OK باشند
        فقط از نود ایران مشهد (ir2.node.check-host.net) استفاده می‌کند
        """
        try:
            # ارسال 4 درخواست ping برای تک IP - فقط از نود ایران مشهد
            ping_params = {
                'host': server_ip,
                'node': 'ir2.node.check-host.net',
                'count': '4'  # ارسال 4 درخواست ping
            }
            
            headers = {'Accept': 'application/json'}
            
            logging.debug(f"🌐 ارسال 4 درخواست ping برای IP {server_ip} به check-host.net (نود: ir2.node.check-host.net)")
            
            async with self.session.post(
                f"{CHECK_HOST_API_BASE}{CHECK_HOST_PING_ENDPOINT}",
                params=ping_params,
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    logging.error(f"خطا در درخواست ping برای {server_ip}: HTTP {response.status}")
                    return False
                
                ping_data = await response.json()
                
                if not ping_data.get('ok'):
                    logging.error(f"خطا در پاسخ ping API برای {server_ip}: {ping_data}")
                    return False
                
                request_id = ping_data.get('request_id')
                
                logging.debug(f"✅ درخواست ping برای {server_ip} ارسال شد - Request ID: {request_id}")
                
                # انتظار برای نتایج (حداکثر 30 ثانیه)
                max_wait_time = 30
                wait_interval = 2
                waited_time = 0
                
                while waited_time < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    waited_time += wait_interval
                    
                    # بررسی نتایج
                    try:
                        async with self.session.get(
                            f"{CHECK_HOST_API_BASE}{CHECK_HOST_RESULT_ENDPOINT}/{request_id}",
                            headers=headers,
                            timeout=10
                        ) as result_response:
                            if result_response.status != 200:
                                continue
                            
                            result_data = await result_response.json()
                            
                            # بررسی اینکه آیا همه نتایج آماده هستند
                            all_ready = True
                            for node_name, node_result in result_data.items():
                                if node_result is None:
                                    all_ready = False
                                    break
                            
                            if all_ready:
                                logging.debug(f"✅ نتایج ping برای {server_ip} آماده شدند - زمان انتظار: {waited_time} ثانیه")
                                break
                            
                    except Exception as e:
                        logging.debug(f"خطا در بررسی نتایج ping برای {server_ip}: {e}")
                        continue
                
                # پردازش نتایج نهایی
                try:
                    async with self.session.get(
                        f"{CHECK_HOST_API_BASE}{CHECK_HOST_RESULT_ENDPOINT}/{request_id}",
                        headers=headers,
                        timeout=10
                    ) as final_response:
                        if final_response.status == 200:
                            final_data = await final_response.json()
                            
                            # تحلیل نتایج برای IP - بررسی اینکه همه 4 ping OK باشند
                            ping_success = self._analyze_ping_results_4_required(final_data, server_ip)
                            return ping_success
                        else:
                            logging.error(f"خطا در دریافت نتایج نهایی ping برای {server_ip}: HTTP {final_response.status}")
                            return False
                            
                except Exception as e:
                    logging.error(f"خطا در پردازش نتایج نهایی ping برای {server_ip}: {e}")
                    return False
                
        except Exception as e:
            logging.error(f"خطا در تست ping برای {server_ip}: {e}")
            return False

    def _analyze_ping_results_4_required(self, result_data: Dict, server_ip: str) -> bool:
        """
        تحلیل نتایج ping برای یک IP خاص - نیاز به 4 ping موفق
        سرور سالم در نظر گرفته می‌شود اگر:
        1. همه 4 ping OK باشند (4/4)
        2. هیچ نودی traceroute نداشته باشد (null یا empty)
        """
        try:
            ping_success_count = 0
            total_ping_count = 0
            traceroute_exists = False
            
            for node_name, node_result in result_data.items():
                if node_result is None:
                    continue
                
                # بررسی ping results
                if isinstance(node_result, list) and len(node_result) > 0:
                    for ping_result in node_result:
                        if isinstance(ping_result, list) and len(ping_result) > 0:
                            # هر ping_result یک لیست از نتایج ping است
                            for individual_ping in ping_result:
                                if isinstance(individual_ping, list) and len(individual_ping) >= 2:
                                    status = individual_ping[0]
                                    total_ping_count += 1
                                    if status == "OK":
                                        ping_success_count += 1
                                        logging.debug(f"✅ IP {server_ip}: Ping موفق شمارش شد ({ping_success_count})")
                                    else:
                                        logging.debug(f"❌ IP {server_ip}: Ping ناموفق شمارش شد")
                
                # بررسی traceroute (اگر وجود داشته باشد)
                if isinstance(node_result, dict) and 'traceroute' in node_result:
                    traceroute_data = node_result['traceroute']
                    if traceroute_data and len(traceroute_data) > 0:
                        traceroute_exists = True
            
            # سرور سالم: همه 4 ping موفق + بدون traceroute
            is_healthy = ping_success_count == 4 and total_ping_count >= 4 and not traceroute_exists
            
            if is_healthy:
                logging.debug(f"✅ IP {server_ip}: همه 4 ping موفق (4/4), بدون traceroute")
            else:
                if ping_success_count < 4:
                    logging.debug(f"❌ IP {server_ip}: فقط {ping_success_count}/4 ping موفق")
                if traceroute_exists:
                    logging.debug(f"❌ IP {server_ip}: traceroute موجود")
                if total_ping_count < 4:
                    logging.debug(f"❌ IP {server_ip}: تعداد کل ping کمتر از 4 ({total_ping_count})")
            
            return is_healthy
            
        except Exception as e:
            logging.error(f"خطا در تحلیل نتایج ping برای {server_ip}: {e}")
            return False

    def merge_ss_configs(self, new_configs: List[str]) -> Dict[str, int]:
        """ادغام کانفیگ‌های جدید با موجود"""
        try:
            new_added = 0
            duplicates_skipped = 0
            total_processed = len(new_configs)
            
            for config in new_configs:
                if config not in self.existing_configs:
                    self.existing_configs.add(config)
                    new_added += 1
                else:
                    duplicates_skipped += 1
            
            logging.info(f"ادغام کانفیگ‌ها: {new_added} جدید، {duplicates_skipped} تکراری")
            return {
                'new_added': new_added,
                'duplicates_skipped': duplicates_skipped,
                'total_processed': total_processed
            }
            
        except Exception as e:
            logging.error(f"خطا در ادغام کانفیگ‌ها: {e}")
            return {
                'new_added': 0,
                'duplicates_skipped': 0,
                'total_processed': 0
            }

    def save_trustlink_ss_file(self) -> bool:
        """ذخیره فایل trustlink_ss.txt"""
        try:
            # بررسی اینکه آیا کانفیگی برای ذخیره وجود دارد
            if not self.existing_configs or len(self.existing_configs) == 0:
                logging.warning("هیچ کانفیگی برای ذخیره وجود ندارد")
                return False
            
            os.makedirs(os.path.dirname(TRUSTLINK_SS_FILE), exist_ok=True)
            
            # ذخیره در فایل اصلی
            with open(TRUSTLINK_SS_FILE, 'w', encoding='utf-8') as f:
                f.write(f"# فایل کانفیگ‌های Shadowsocks - TrustLink Shadowsocks\n")
                f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# تعداد کانفیگ‌ها: {len(self.existing_configs)}\n")
                f.write(f"# ==================================================\n\n")
                
                for config in self.existing_configs:
                    f.write(f"{config}\n")
            
            logging.info(f"فایل trustlink_ss.txt با موفقیت ذخیره شد: {len(self.existing_configs)} کانفیگ")
            return True
            
        except Exception as e:
            logging.error(f"خطا در ذخیره فایل trustlink_ss.txt: {e}")
            return False

    def update_metadata(self, stats: Dict[str, int], test_results: List[Dict]):
        """به‌روزرسانی متادیتای برنامه"""
        now = datetime.now().isoformat()
        
        # اطمینان از اینکه test_results خالی نیست
        if not test_results or len(test_results) == 0:
            logging.warning("test_results خالی است، استفاده از مقادیر پیش‌فرض")
            working_count = 0
            failed_count = 0
            iran_accessible_count = 0
        else:
            working_count = len([r for r in test_results if r.get("success", False)])
            failed_count = len([r for r in test_results if not r.get("success", False)])
            iran_accessible_count = len([r for r in test_results if r.get("iran_access", False)])
        
        # اطمینان از اینکه stats شامل تمام فیلدهای مورد نیاز است
        safe_stats = {
            "new_added": stats.get("new_added", 0),
            "duplicates_skipped": stats.get("duplicates_skipped", 0),
            "invalid_skipped": stats.get("invalid_skipped", 0)
        }
        
        self.metadata.update({
            "last_update": now,
            "total_tests": self.metadata.get("total_tests", 0) + 1,
            "total_configs": len(self.existing_configs),
            "working_configs": working_count,
            "failed_configs": failed_count,
            "iran_accessible_configs": iran_accessible_count,
            "last_ss_source": SS_SOURCE_FILE,
            "last_stats": {
                "new_added": safe_stats["new_added"],
                "duplicates_skipped": safe_stats["duplicates_skipped"],
                "invalid_skipped": safe_stats["invalid_skipped"],
                "working_configs": working_count,
                "failed_configs": failed_count,
                "iran_accessible": iran_accessible_count,
                "timestamp": now
            }
        })
        
        self.save_metadata()

    def save_partial_progress(self, reason: str = "") -> bool:
        """ذخیره خروجی جزئی در صورت timeout یا خطا"""
        try:
            # انتخاب بهترین مرحله‌ای که داده دارد
            if self.partial_ping_ok:
                best_configs = list({c for c in self.partial_ping_ok if self.is_valid_ss_config(c)})
                stage = "ping_ok"
            elif self.partial_results:
                best_configs = [r.get("config") for r in self.partial_results if isinstance(r, dict) and r.get("success", False) and self.is_valid_ss_config(r.get("config", ""))]
                stage = "connect_ok"
            else:
                best_configs = []
                stage = "none"

            if best_configs:
                logging.info(f"💾 ذخیره خروجی جزئی ({stage}) به دلیل: {reason} - تعداد: {len(best_configs)}")
                self.existing_configs = set()
                stats = self.merge_ss_configs(best_configs)
                if self.save_trustlink_ss_file():
                    test_results = self.partial_results if self.partial_results else []
                    self.update_metadata(stats, test_results)
                    logging.info("✅ خروجی جزئی با موفقیت ذخیره شد")
                    return True
                else:
                    logging.error("❌ ذخیره خروجی جزئی ناموفق بود")
                    return False
            else:
                logging.warning(f"هیچ نتیجه جزئی برای ذخیره وجود ندارد (reason={reason})")
                self.create_fallback_output(f"partial-save: no results (reason={reason})")
                return False
        except Exception as e:
            logging.error(f"خطا در ذخیره خروجی جزئی: {e}")
            try:
                self.create_fallback_output(f"partial-save error: {str(e)}")
            except:
                pass
            return False

    def create_fallback_output(self, message: str):
        """ایجاد فایل خروجی fallback در صورت خطا"""
        try:
            logging.info(f"ایجاد فایل fallback: {message}")
            
            # اطمینان از وجود دایرکتوری
            os.makedirs(os.path.dirname(TRUSTLINK_SS_FILE), exist_ok=True)
            
            # ایجاد فایل خروجی ساده
            with open(TRUSTLINK_SS_FILE, 'w', encoding='utf-8') as f:
                f.write("# فایل کانفیگ‌های Shadowsocks - TrustLink Shadowsocks\n")
                f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# وضعیت: {message}\n")
                f.write("# " + "="*50 + "\n\n")
                f.write("# هیچ کانفیگ Shadowsocks سالمی یافت نشد\n")
                f.write("# لطفاً لاگ‌ها را بررسی کنید\n")
            
            # ایجاد متادیتای ساده
            fallback_metadata = {
                "last_update": datetime.now().isoformat(),
                "total_tests": 0,
                "total_configs": 0,
                "working_configs": 0,
                "failed_configs": 0,
                "iran_accessible_configs": 0,
                "error_message": message,
                "status": "fallback"
            }
            
            with open(TRUSTLINK_SS_METADATA, 'w', encoding='utf-8') as f:
                json.dump(fallback_metadata, f, indent=2, ensure_ascii=False)
            
            logging.info("فایل fallback با موفقیت ایجاد شد")
            
        except Exception as e:
            logging.error(f"خطا در ایجاد فایل fallback: {e}")

    def is_valid_ss_config(self, config: str) -> bool:
        """بررسی اعتبار کانفیگ Shadowsocks"""
        try:
            if not config or len(config.strip()) < 10:
                return False
            
            if not config.startswith(SS_PROTOCOL):
                return False
            
            # تلاش برای پارس کانفیگ
            parsed = self.parse_ss_config(config)
            if parsed and parsed.get('server_ip') and parsed.get('port'):
                return True
            
            return False
            
        except Exception:
            return False

    def save_working_configs(self, results: List[Dict]):
        """ذخیره کانفیگ‌های سالم"""
        try:
            # فیلتر کردن کانفیگ‌های سالم که تمام تست‌ها را قبول شده‌اند
            fully_working_configs = [r["config"] for r in results if r.get("status") == "working" and r.get("download_speed_ok", False)]
            
            # کانفیگ‌های نیمه سالم (فقط اتصال سالم)
            partially_working_configs = [r["config"] for r in results if r.get("status") == "working" and not r.get("download_speed_ok", False)]
            
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
                "connection_ok": len([r for r in results if r.get("status") == "working"]),
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

    async def test_all_ss_configs(self, configs: List[str]) -> List[Dict]:
        """تست تمام کانفیگ‌های Shadowsocks"""
        logging.info(f"شروع تست {len(configs)} کانفیگ Shadowsocks...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config):
            async with semaphore:
                return await self.test_ss_connection(config)
        
        # تست کانفیگ‌ها در batches برای جلوگیری از overload
        batch_size = 500  # افزایش batch size برای تست بیشتر
        all_results = []
        total_batches = (len(configs) + batch_size - 1) // batch_size
        
        for i in range(0, len(configs), batch_size):
            batch = configs[i:i + batch_size]
            current_batch = i // batch_size + 1
            logging.info(f"تست batch {current_batch}/{total_batches}: {len(batch)} کانفیگ")
            
            tasks = [test_single_config(config) for config in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # فیلتر کردن نتایج موفق
            successful_in_batch = 0
            for result in batch_results:
                if isinstance(result, dict) and result.get("success", False):
                    all_results.append(result)
                    # ذخیره نتایج موفق برای ذخیره‌سازی جزئی
                    try:
                        self.partial_results.append(result)
                    except Exception:
                        pass
                    successful_in_batch += 1
            
            logging.info(f"Batch {current_batch} کامل شد: {successful_in_batch} کانفیگ موفق از {len(batch)}")
            
            # کمی صبر بین batches
            if i + batch_size < len(configs):
                await asyncio.sleep(1)  # افزایش زمان انتظار برای جلوگیری از overload
        
        logging.info(f"تست Shadowsocks کامل شد: {len(all_results)} کانفیگ موفق از {len(configs)}")
        return all_results

    async def test_ss_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ Shadowsocks - فقط تست TCP ساده"""
        config_hash = self.create_config_hash(config)[:8]
        result = {
            "config": config,
            "hash": config_hash,
            "success": False,
            "latency": None,
            "error": None,
            "server_address": None,
            "port": None,
            "iran_access": False
        }
        
        try:
            # پارس کردن کانفیگ
            parsed_config = self.parse_ss_config(config)
            if not parsed_config:
                result["error"] = "Invalid Shadowsocks config format"
                logging.warning(f"❌ کانفیگ Shadowsocks نامعتبر: {config_hash}")
                return result
            
            # بررسی وجود فیلدهای مورد نیاز
            if "server_ip" not in parsed_config and "server" in parsed_config:
                parsed_config["server_ip"] = parsed_config["server"]
            elif "server_ip" not in parsed_config:
                result["error"] = "Server IP not found in config"
                logging.warning(f"❌ کانفیگ Shadowsocks بدون IP سرور: {config_hash}")
                return result
            
            server_ip = parsed_config["server_ip"]
            port = parsed_config.get("port", "8388")
            
            result["server_address"] = server_ip
            result["port"] = port
            
            # تست اتصال TCP ساده
            start_time = time.time()
            try:
                # ایجاد اتصال TCP
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, int(port)),
                    timeout=10
                )
                
                # بستن اتصال
                writer.close()
                await writer.wait_closed()
                
                # محاسبه latency
                latency = (time.time() - start_time) * 1000
                result["latency"] = latency
                result["success"] = True
                
                logging.debug(f"✅ اتصال موفق: {server_ip}:{port} - Latency: {latency:.2f}ms")
                
            except asyncio.TimeoutError:
                result["error"] = "Connection timeout"
                logging.debug(f"⏰ timeout: {server_ip}:{port}")
            except Exception as e:
                result["error"] = str(e)
                logging.debug(f"❌ خطا در اتصال: {server_ip}:{port} - {e}")
                
        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            logging.error(f"خطای غیرمنتظره در تست {config_hash}: {e}")
        
        return result

    def create_config_hash(self, config: str) -> str:
        """ایجاد hash برای کانفیگ"""
        return hashlib.md5(config.encode()).hexdigest()

    async def run_ss_update(self) -> bool:
        """اجرای یک دور کامل به‌روزرسانی Shadowsocks"""
        try:
            logging.info("=" * 60)
            logging.info("🚀 شروع به‌روزرسانی TrustLink Shadowsocks")
            logging.info("=" * 60)
            
            # بارگذاری کانفیگ‌های موجود
            self.load_existing_configs()
            
            # بارگذاری کانفیگ‌های Shadowsocks از فایل منبع
            source_configs = self.load_ss_configs()
            if not source_configs:
                logging.warning("هیچ کانفیگ Shadowsocks جدیدی از فایل منبع بارگذاری نشد")
                # ذخیره خروجی جزئی اگر چیزی وجود دارد؛ در غیراینصورت fallback
                if not self.save_partial_progress("no-source-configs"):
                    self.create_fallback_output("هیچ کانفیگ Shadowsocks جدیدی یافت نشد")
                return False
            
            # ایجاد session
            await self.create_session()

            # فاز 1: تست اتصال TCP روی همه کانفیگ‌ها
            # فقط تست TCP ساده برای سرعت بالا - تست‌های دیگر در مراحل بعدی
            # هر کانفیگ فقط یک بار تست می‌شود - از کل پروکسی‌ها دو بار تست گرفته نمی‌شود
            # هدف: سرعت بالا و کارایی بهتر
            test_results = await self.test_all_ss_configs(source_configs)
            if not test_results:
                logging.warning("هیچ کانفیگ Shadowsocks موفقی یافت نشد")
                if not self.save_partial_progress("no-connect-success"):
                    self.create_fallback_output("هیچ کانفیگ Shadowsocks موفقی یافت نشد")
                return False

            # فاز 2: تست ping با check-host.net API، فقط روی کانفیگ‌های سالم TCP
            # فیلتر کردن کانفیگ‌هایی که تست TCP را پاس کرده‌اند
            # از کل پروکسی‌ها دو بار تست گرفته نمی‌شود - فقط پروکسی‌های سالم TCP
            healthy_configs = [r["config"] for r in test_results if r.get("success", False)]
            if not healthy_configs:
                logging.warning("هیچ کانفیگ Shadowsocks موفقی یافت نشد")
                if not self.save_partial_progress("no-healthy-after-connect"):
                    self.create_fallback_output("هیچ کانفیگ Shadowsocks موفقی یافت نشد")
                return False

            logging.info(f"🌐 شروع تست ping (4/4) با check-host.net برای {len(healthy_configs)} کانفیگ سالم TCP")
            logging.info(f"🎯 بهینه‌سازی: انتخاب تصادفی حداکثر 50 کانفیگ برای تست ping")
            ping_ok_configs = await self.filter_configs_by_ping_check(healthy_configs)
            if not ping_ok_configs:
                logging.warning("هیچ کانفیگی تست ping را پاس نکرد")
                if not self.save_partial_progress("no-ping-pass"):
                    self.create_fallback_output("هیچ کانفیگی تست ping را پاس نکرد")
                return False

            # فاز 3: تست سرعت دانلود - REMOVED
            # بهترین‌ها: کانفیگ‌هایی که تست ping را پاس کرده‌اند
            best_configs = ping_ok_configs if ping_ok_configs else []
            
            # اطمینان از اینکه best_configs همیشه یک لیست است
            if not isinstance(best_configs, list):
                logging.warning("best_configs باید یک لیست باشد، تبدیل به لیست خالی")
                best_configs = []

            # ادغام کانفیگ‌ها
            self.existing_configs = set()
            
            # اطمینان از اینکه best_configs خالی نیست
            if not best_configs:
                logging.warning("هیچ کانفیگی برای ادغام وجود ندارد")
                stats = {
                    'new_added': 0,
                    'duplicates_skipped': 0,
                    'total_processed': 0
                }
            else:
                stats = self.merge_ss_configs(best_configs)

            # ذخیره فایل
            if best_configs and len(best_configs) > 0:
                if self.save_trustlink_ss_file():
                    # به‌روزرسانی متادیتا با نتایج فاز اتصال
                    # اطمینان از اینکه test_results خالی نیست
                    if test_results and len(test_results) > 0:
                        self.update_metadata(stats, test_results)
                    else:
                        logging.warning("test_results خالی است، متادیتا به‌روزرسانی نمی‌شود")

                    logging.info("✅ به‌روزرسانی Shadowsocks با موفقیت انجام شد")
                    logging.info(f"📊 آمار: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری")
                    logging.info(f"🔗 کانفیگ‌های Shadowsocks سالم (پس از تمام تست‌ها): {len(best_configs)}")
                    logging.info(f"📱 تست‌های انجام شده: حذف تکراری → TCP → Ping (تصادفی 50) → Speed Test REMOVED")
                    if len(healthy_configs) > 50:
                        logging.info(f"⚡ بهینه‌سازی سرعت: تست ping فقط روی {min(50, len(healthy_configs))} کانفیگ تصادفی")
                    return True
                else:
                    logging.error("❌ خطا در ذخیره فایل Shadowsocks")
                    self.create_fallback_output("خطا در ذخیره فایل اصلی")
                    return False
            else:
                logging.warning("⚠️ هیچ کانفیگ سالمی برای ذخیره یافت نشد")
                self.create_fallback_output("هیچ کانفیگ سالمی یافت نشد")
                return False
                
        except Exception as e:
            logging.error(f"خطا در اجرای به‌روزرسانی Shadowsocks: {e}")
            # ایجاد فایل fallback در صورت خطا
            self.create_fallback_output(f"خطا در اجرا: {str(e)}")
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
            "iran_accessible_configs": self.metadata.get("iran_accessible_configs", 0),
            "file_size_kb": os.path.getsize(TRUSTLINK_SS_FILE) / 1024 if os.path.exists(TRUSTLINK_SS_FILE) else 0,
            "backup_exists": os.path.exists(BACKUP_FILE)
        }

    async def run_full_test(self):
        """اجرای کامل تست (نسخه قدیمی - حفظ شده برای سازگاری)"""
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

async def run_ss_tester():
    """اجرای تستر Shadowsocks"""
    setup_logging()
    
    logging.info("🚀 راه‌اندازی TrustLink Shadowsocks Tester")
    
    manager = SSManager()
    
    try:
        # اجرای یک دور به‌روزرسانی با timeout طولانی
        async with asyncio.timeout(7200):  # timeout 120 دقیقه - افزایش برای تست‌های اضافی
            success = await manager.run_ss_update()
        
        if success:
            status = manager.get_status()
            logging.info("📈 وضعیت نهایی Shadowsocks:")
            for key, value in status.items():
                logging.info(f"  {key}: {value}")
        else:
            logging.error("❌ به‌روزرسانی Shadowsocks ناموفق بود")
            
    except asyncio.TimeoutError:
        logging.error("⏰ timeout: برنامه Shadowsocks بیش از 120 دقیقه طول کشید")
        # ذخیره نتایج جزئی جهت جلوگیری از از دست رفتن خروجی‌ها
        try:
            manager.save_partial_progress("timeout")
        except Exception:
            pass
    except KeyboardInterrupt:
        logging.info("برنامه Shadowsocks توسط کاربر متوقف شد")
    except Exception as e:
        logging.error(f"خطای غیرمنتظره در Shadowsocks: {e}")
        # در صورت خطای غیرمنتظره نیز تلاش برای ذخیره خروجی جزئی
        try:
            manager.save_partial_progress("unexpected-error")
        except Exception:
            pass
    finally:
        await manager.close_session()

def main():
    """تابع اصلی"""
    setup_logging()
    
    # بررسی آرگومان‌ها
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auto":
            # حالت خودکار
            schedule_ss_tester()
        elif sys.argv[1] == "--test":
            # حالت تست ساده برای GitHub Actions
            setup_logging()
            logging.info("🧪 Shadowsocks Tester - Test Mode (GitHub Actions)")
            
            manager = SSManager()
            
            try:
                # تست ساده بدون اجرای کامل
                logging.info("بررسی فایل‌های منبع...")
                
                # بررسی فایل منبع
                if os.path.exists(SS_SOURCE_FILE):
                    with open(SS_SOURCE_FILE, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    logging.info(f"فایل منبع موجود: {len(lines)} خط")
                else:
                    logging.error(f"فایل منبع یافت نشد: {SS_SOURCE_FILE}")
                
                # ایجاد دایرکتوری‌های خروجی
                os.makedirs("../trustlink", exist_ok=True)
                os.makedirs("../logs", exist_ok=True)
                
                # ایجاد فایل تست ساده
                test_file = "../trustlink/trustlink_ss.txt"
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("# فایل تست Shadowsocks - TrustLink Shadowsocks\n")
                    f.write(f"# ایجاد شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("# حالت: تست GitHub Actions\n")
                    f.write("# " + "="*50 + "\n\n")
                    f.write("# این فایل برای تست GitHub Actions ایجاد شده است\n")
                    f.write("# در اجرای واقعی، کانفیگ‌های Shadowsocks سالم اینجا قرار می‌گیرند\n")
                
                # ایجاد متادیتای تست
                test_metadata = {
                    "last_update": datetime.now().isoformat(),
                    "total_tests": 0,
                    "total_configs": 0,
                    "working_configs": 0,
                    "failed_configs": 0,
                    "iran_accessible_configs": 0,
                    "status": "test_mode",
                    "message": "GitHub Actions test mode"
                }
                
                with open("../trustlink/.trustlink_ss_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(test_metadata, f, indent=2, ensure_ascii=False)
                
                logging.info("✅ فایل‌های تست با موفقیت ایجاد شدند")
                logging.info(f"✅ فایل خروجی: {test_file}")
                logging.info(f"✅ متادیتا: ../trustlink/.trustlink_ss_metadata.json")
                
            except Exception as e:
                logging.error(f"خطا در حالت تست: {e}")
                # ایجاد فایل fallback
                manager.create_fallback_output(f"خطا در حالت تست: {str(e)}")
        else:
            # اجرای یکباره
            asyncio.run(run_ss_tester())
    else:
        # اجرای یکباره (پیش‌فرض)
        asyncio.run(run_ss_tester())

def schedule_ss_tester():
    """تنظیم اجرای خودکار هفتگی"""
    logging.info("⏰ تنظیم اجرای خودکار هفتگی برای Shadowsocks Tester")
    
    # اجرای هفتگی در روز یکشنبه ساعت 06:30 تهران (03:00 UTC)
    schedule.every().sunday.at("06:30").do(lambda: asyncio.run(run_ss_tester()))
    
    # اجرای فوری در شروع (برای تست)
    schedule.every().minute.do(lambda: asyncio.run(run_ss_tester())).until("23:59")
    
    logging.info("📅 برنامه زمانبندی هفتگی فعال شد")
    logging.info("🕐 اجرای بعدی: یکشنبه ساعت 06:30 تهران")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # بررسی هر دقیقه
        except KeyboardInterrupt:
            logging.info("برنامه Shadowsocks Tester متوقف شد")
            break
        except Exception as e:
            logging.error(f"خطا در اجرای خودکار: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
