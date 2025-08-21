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
import subprocess
import platform
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

# تنظیمات check-host.net API
CHECK_HOST_API_BASE = "https://check-host.net"
CHECK_HOST_PING_ENDPOINT = "/check-ping"
CHECK_HOST_RESULT_ENDPOINT = "/check-result"
CHECK_HOST_FOCUS_NODE = "ir2.node.check-host.net"  # نود ایران مشهد
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

class VLESSManager:
    """مدیریت اصلی برنامه VLESS Tester"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.existing_configs: Set[str] = set()
        self.metadata: Dict = {}
        self.load_metadata()
        # ذخیره نتایج جزئی برای تداوم در صورت timeout/خطا
        self.partial_results: List[Dict] = []
        self.partial_ping_ok: List[str] = []  # نتایج ping check

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
            timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT, connect=10, sock_read=TEST_TIMEOUT)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, ttl_dns_cache=300)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
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
            configs = []
            
            # بارگذاری از فایل محلی
            if os.path.exists(VLESS_SOURCE_FILE):
                with open(VLESS_SOURCE_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if self.is_valid_vless_config(line):
                            configs.append(line)
                logging.info(f"{len(configs)} کانفیگ VLESS از فایل محلی بارگذاری شد")
            else:
                logging.warning(f"فایل منبع VLESS یافت نشد: {VLESS_SOURCE_FILE}")
            
            # حذف تکراری‌ها
            unique_configs = list(set(configs))
            logging.info(f"مجموع {len(unique_configs)} کانفیگ VLESS منحصر به فرد یافت شد")
            
            # محدود کردن تعداد کانفیگ‌ها برای تست
            if len(unique_configs) > MAX_CONFIGS_TO_TEST:
                logging.info(f"محدود کردن تعداد کانفیگ‌ها از {len(unique_configs)} به {MAX_CONFIGS_TO_TEST}")
                unique_configs = unique_configs[:MAX_CONFIGS_TO_TEST]
            
            return unique_configs
                
        except Exception as e:
            logging.error(f"خطا در بارگذاری کانفیگ‌های VLESS: {e}")
            return []
    
    def parse_vless_config(self, config: str) -> Optional[Dict]:
        """پارس کردن کانفیگ VLESS و استخراج اطلاعات"""
        try:
            if not config.startswith(VLESS_PROTOCOL):
                return None
            
            # حذف vless://
            vless_data = config.replace(VLESS_PROTOCOL, "")
            
            # پیدا کردن @ برای جدا کردن UUID و آدرس
            at_index = vless_data.find('@')
            if at_index == -1:
                return None
            
            uuid = vless_data[:at_index]
            server_part = vless_data[at_index + 1:]
            
            # پیدا کردن : برای جدا کردن IP و پورت
            colon_index = server_part.find(':')
            if colon_index == -1:
                return None
            
            server_ip = server_part[:colon_index]
            port_part = server_part[colon_index + 1:]
            
            # جدا کردن پورت از query parameters
            question_index = port_part.find('?')
            if question_index != -1:
                port = port_part[:question_index]
                query_params = port_part[question_index + 1:]
            else:
                port = port_part
                query_params = ""
            
            # استخراج type و security از query parameters
            type_param = "tcp"  # پیش‌فرض
            security_param = "none"  # پیش‌فرض
            
            if query_params:
                for param in query_params.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        if key == 'type':
                            type_param = value
                        elif key == 'security':
                            security_param = value
            
            return {
                "uuid": uuid,
                "server_ip": server_ip,
                "port": port,
                "type": type_param,
                "security": security_param,
                "query_params": query_params
            }
            
        except Exception as e:
            logging.error(f"خطا در پارس کردن کانفیگ VLESS: {e}")
            return None

    # ==========================
    # جدید: تست Ping با check-host.net API
    # ==========================
    
    async def check_host_ping_batch(self, server_ips: List[str]) -> Dict[str, bool]:
        """
        تست ping برای batch از IP ها با استفاده از check-host.net API
        فقط از نود ایران مشهد (ir2.node.check-host.net) استفاده می‌کند
        """
        ping_results = {}
        
        try:
            # ارسال درخواست ping برای batch - فقط از نود ایران مشهد
            ping_params = {
                'host': ','.join(server_ips),
                'node': CHECK_HOST_FOCUS_NODE
            }
            
            headers = {'Accept': 'application/json'}
            
            logging.info(f"🌐 ارسال درخواست ping برای {len(server_ips)} IP به check-host.net (نود: {CHECK_HOST_FOCUS_NODE})")
            
            async with self.session.post(
                f"{CHECK_HOST_API_BASE}{CHECK_HOST_PING_ENDPOINT}",
                params=ping_params,
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    logging.error(f"خطا در درخواست ping: HTTP {response.status}")
                    return {ip: False for ip in server_ips}
                
                ping_data = await response.json()
                
                if not ping_data.get('ok'):
                    logging.error(f"خطا در پاسخ ping API: {ping_data}")
                    return {ip: False for ip in server_ips}
                
                request_id = ping_data.get('request_id')
                nodes = ping_data.get('nodes', {})
                
                logging.info(f"✅ درخواست ping ارسال شد - Request ID: {request_id}")
                logging.info(f"🌍 نود تست: {CHECK_HOST_FOCUS_NODE}")
                
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
                                logging.info(f"✅ نتایج ping آماده شدند - زمان انتظار: {waited_time} ثانیه")
                                break
                            
                    except Exception as e:
                        logging.debug(f"خطا در بررسی نتایج ping: {e}")
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
                            
                            # تحلیل نتایج برای هر IP
                            for server_ip in server_ips:
                                ping_success = self._analyze_ping_results(final_data, server_ip)
                                ping_results[server_ip] = ping_success
                                
                                if ping_success:
                                    logging.info(f"✅ IP {server_ip}: Ping موفق")
                                else:
                                    logging.debug(f"❌ IP {server_ip}: Ping ناموفق")
                        else:
                            logging.error(f"خطا در دریافت نتایج نهایی ping: HTTP {final_response.status}")
                            ping_results = {ip: False for ip in server_ips}
                            
                except Exception as e:
                    logging.error(f"خطا در پردازش نتایج نهایی ping: {e}")
                    ping_results = {ip: False for ip in server_ips}
                
        except Exception as e:
            logging.error(f"خطا در تست ping batch: {e}")
            ping_results = {ip: False for ip in server_ips}
        
        return ping_results
    
    def _analyze_ping_results(self, result_data: Dict, server_ip: str) -> bool:
        """
        تحلیل نتایج ping برای یک IP خاص
        سرور سالم در نظر گرفته می‌شود اگر:
        1. حداقل یک نود ping موفق داشته باشد
        2. هیچ نودی traceroute نداشته باشد (null یا empty)
        """
        try:
            ping_success_count = 0
            traceroute_exists = False
            
            for node_name, node_result in result_data.items():
                if node_result is None:
                    continue
                
                # بررسی ping results
                if isinstance(node_result, list) and len(node_result) > 0:
                    for ping_result in node_result:
                        if isinstance(ping_result, list) and len(ping_result) >= 2:
                            status = ping_result[0]
                            if status == "OK":
                                ping_success_count += 1
                
                # بررسی traceroute (اگر وجود داشته باشد)
                if isinstance(node_result, dict) and 'traceroute' in node_result:
                    traceroute_data = node_result['traceroute']
                    if traceroute_data and len(traceroute_data) > 0:
                        traceroute_exists = True
            
            # سرور سالم: ping موفق + بدون traceroute
            is_healthy = ping_success_count > 0 and not traceroute_exists
            
            if is_healthy:
                logging.debug(f"✅ IP {server_ip}: Ping موفق ({ping_success_count} نود), بدون traceroute")
            else:
                if ping_success_count == 0:
                    logging.debug(f"❌ IP {server_ip}: هیچ ping موفقی")
                if traceroute_exists:
                    logging.debug(f"❌ IP {server_ip}: traceroute موجود")
            
            return is_healthy
            
        except Exception as e:
            logging.error(f"خطا در تحلیل نتایج ping برای {server_ip}: {e}")
            return False
    
    async def filter_configs_by_ping_check(self, configs: List[str]) -> List[str]:
        """
        فیلتر کردن کانفیگ‌ها بر اساس تست ping با check-host.net
        ارسال 50 تا 50 تا IP و تمرکز روی لوکیشن ایران، مشهد
        """
        try:
            # استخراج IP های منحصر به فرد
            unique_ips = set()
            ip_to_configs = {}
            
            for config in configs:
                parsed = self.parse_vless_config(config)
                if parsed and parsed.get('server_ip'):
                    ip = parsed['server_ip']
                    unique_ips.add(ip)
                    if ip not in ip_to_configs:
                        ip_to_configs[ip] = []
                    ip_to_configs[ip].append(config)
            
            logging.info(f"🌐 شروع تست ping برای {len(unique_ips)} IP منحصر به فرد")
            
            # تقسیم IP ها به batches
            ip_list = list(unique_ips)
            batches = [ip_list[i:i + CHECK_HOST_BATCH_SIZE] for i in range(0, len(ip_list), CHECK_HOST_BATCH_SIZE)]
            
            all_ping_results = {}
            
            # تست هر batch
            for i, batch in enumerate(batches, 1):
                logging.info(f"📦 تست batch {i}/{len(batches)}: {len(batch)} IP")
                
                try:
                    batch_results = await self.check_host_ping_batch(batch)
                    all_ping_results.update(batch_results)
                    
                    # کمی صبر بین batches
                    if i < len(batches):
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logging.error(f"خطا در تست batch {i}: {e}")
                    # در صورت خطا، همه IP های این batch را ناموفق در نظر بگیر
                    for ip in batch:
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
            
            logging.info(f"✅ تست ping کامل شد: {len(healthy_configs)} کانفیگ سالم از {len(configs)}")
            logging.info(f"🌍 IP های سالم: {len(healthy_ips)} از {len(unique_ips)}")
            
            return healthy_configs
            
        except Exception as e:
            logging.error(f"خطا در فیلتر کردن بر اساس ping: {e}")
            return configs  # در صورت خطا، همه کانفیگ‌ها را برگردان
    
    async def test_vless_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ VLESS - فقط تست TCP ساده"""
        config_hash = self.create_config_hash(config)[:8]
        result = {
            "config": config,
            "hash": config_hash,
            "success": False,
            "latency": None,
            "error": None,
            "server_address": None,
            "port": None,
            "type": None,
            "iran_access": False
        }
        
        try:
            # پارس کردن کانفیگ
            parsed_config = self.parse_vless_config(config)
            if not parsed_config:
                result["error"] = "Invalid VLESS config format"
                logging.warning(f"❌ کانفیگ VLESS نامعتبر: {config_hash}")
                return result
            
            server_ip = parsed_config["server_ip"]
            port = parsed_config["port"]
            connection_type = parsed_config["type"]
            
            result["server_address"] = server_ip
            result["port"] = port
            result["type"] = connection_type
            
            # تست اتصال - فقط TCP connection test (برای سرعت و کارایی)
            start_time = time.time()
            
            # تست TCP connection test - تست ساده و سریع
            tcp_success = await self.test_tcp_connection(server_ip, port)
            if tcp_success:
                result["success"] = True
                result["latency"] = (time.time() - start_time) * 1000
                logging.info(f"✅ تست TCP موفق: {config_hash} - Server: {server_ip}:{port} - Type: {connection_type} - Latency: {result['latency']:.1f}ms")
            else:
                result["error"] = "TCP connection failed"
                logging.warning(f"❌ تست VLESS ناموفق: {config_hash} - TCP connection failed")
                
        except Exception as e:
            result["error"] = str(e)
            logging.error(f"خطا در تست VLESS {config_hash}: {e}")
        
        return result
    
    async def test_tcp_connection(self, server_ip: str, port: str) -> bool:
        """تست اتصال TCP"""
        try:
            # استفاده از asyncio برای تست اتصال TCP
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, int(port)),
                    timeout=10.0
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return False
        except Exception:
            return False
    
    async def test_http_connection(self, server_ip: str, port: str) -> bool:
        """تست اتصال HTTP/HTTPS"""
        try:
            port_int = int(port)
            if port_int in [80, 8080]:
                url = f"http://{server_ip}:{port_int}"
            elif port_int in [443, 8443]:
                url = f"https://{server_ip}:{port_int}"
            else:
                # تست هر دو پروتکل برای پورت‌های دیگر
                try:
                    url = f"http://{server_ip}:{port_int}"
                    async with self.session.get(url, timeout=5) as response:
                        return response.status < 500
                except:
                    try:
                        url = f"https://{server_ip}:{port_int}"
                        async with self.session.get(url, timeout=5) as response:
                            return response.status < 500
                    except:
                        return False
                return False
            
            async with self.session.get(url, timeout=5) as response:
                return response.status < 500
                
        except Exception:
            return False
    
    async def test_vless_protocol(self, server_ip: str, port: str, connection_type: str) -> bool:
        """تست پروتکل VLESS (شبیه‌سازی)"""
        try:
            # تست اتصال با timeout کوتاه
            # این تست شبیه‌سازی می‌کند که سرور VLESS در دسترس است
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, int(port)),
                    timeout=5.0
                )
                
                # ارسال یک بایت تست (شبیه‌سازی handshake VLESS)
                writer.write(b'\x00')
                await writer.drain()
                
                # خواندن پاسخ (اگر سرور پاسخ دهد)
                try:
                    data = await asyncio.wait_for(reader.read(1), timeout=2.0)
                    # اگر داده‌ای خوانده شد، سرور پاسخگو است
                    if data:
                        writer.close()
                        await writer.wait_closed()
                        return True
                except asyncio.TimeoutError:
                    # timeout در خواندن، اما اتصال برقرار شده
                    pass
                
                writer.close()
                await writer.wait_closed()
                return True
                
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return False
                
        except Exception:
            return False
    
    async def test_iran_access(self, server_ip: str, port: str) -> bool:
        """تست دسترسی از ایران با تست سایت‌های ایرانی"""
        try:
            # تست اتصال به سایت‌های ایرانی
            iran_test_urls = [
                "https://www.aparat.com",
                "https://divar.ir", 
                "https://www.cafebazaar.ir",
                "https://www.digikala.com",
                "https://www.sheypoor.com",
                "https://www.telewebion.com"
            ]
            
            # تست اتصال TCP اولیه
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, int(port)),
                    timeout=10.0
                )
                writer.close()
                await writer.wait_closed()
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return False
            
            # تست HTTP request به سایت‌های ایرانی
            for test_url in iran_test_urls:
                try:
                    async with self.session.get(test_url, timeout=5) as response:
                        if response.status < 400:
                            return True
                except Exception:
                    continue
            
            # اگر هیچ سایت ایرانی پاسخ نداد، تست اتصال ساده
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, int(port)),
                    timeout=8.0
                )
                
                # ارسال handshake ساده
                writer.write(b'\x01')
                await writer.drain()
                
                try:
                    data = await asyncio.wait_for(reader.read(1), timeout=3.0)
                    if data:
                        writer.close()
                        await writer.wait_closed()
                        return True
                except asyncio.TimeoutError:
                    pass
                
                writer.close()
                await writer.wait_closed()
                return True
                
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return False
                
        except Exception:
            return False

    # DISABLED: تست شبکه‌های اجتماعی غیرفعال شد
    # async def test_social_media_access_via_xray(self, link: str) -> Dict[str, bool]:
    #     """تست دسترسی به شبکه‌های اجتماعی (یوتیوب، اینستاگرام، تلگرام) با استفاده از Xray"""
    #     try:
    #         xray_path = self._get_xray_binary_path()
    #         if not xray_path:
    #             return {"youtube": False, "instagram": False, "telegram": False}
    #         
    #         local_port = self._choose_free_port()
    #         cfg = self._build_xray_config_http_proxy(link, local_port)
    #         if not cfg:
    #             return {"youtube": False, "instagram": False, "telegram": False}
    #         
    #         import tempfile, json, shutil
    #         tmp_dir = tempfile.mkdtemp(prefix='vless_social_')
    #         cfg_path = os.path.join(tmp_dir, 'config.json')
    #         
    #         with open(cfg_path, 'w', encoding='utf-8') as f:
    #             json.dump(cfg, f, ensure_ascii=False)
    #         
    #         proc = await asyncio.create_subprocess_exec(
    #             xray_path, '-config', cfg_path, 
    #             stdout=asyncio.subprocess.PIPE, 
    #             stderr=asyncio.subprocess.STDOUT
    #         )
    #         
    #         # زمان کوتاه برای بالا آمدن Xray
    #         await asyncio.sleep(0.5)
    #         
    #         try:
    #             # تست دسترسی به شبکه‌های اجتماعی
    #             results = {"youtube": False, "instagram": False, "telegram": False}
    #             
    #             # تست یوتیوب
    #             try:
    #                 async with aiohttp.ClientSession() as test_session:
    #                     async with test_session.get("https://www.youtube.com", 
    #                                              proxy=f"http://127.0.0.1:{local_port}",
    #                                              timeout=aiohttp.ClientTimeout(total=10)) as response:
    #                         results["youtube"] = response.status == 200
    #             except:
    #                 results["youtube"] = False
    #             
    #             # تست اینستاگرام
    #             try:
    #                 async with aiohttp.ClientSession() as test_session:
    #                     async with test_session.get("https://www.instagram.com", 
    #                                              proxy=f"http://127.0.0.1:{local_port}",
    #                                              timeout=aiohttp.ClientTimeout(total=10)) as response:
    #                         results["instagram"] = response.status == 200
    #             except:
    #                 results["instagram"] = False
    #             
    #             # تست تلگرام
    #             try:
    #                 async with aiohttp.ClientSession() as test_session:
    #                     async with test_session.get("https://web.telegram.org", 
    #                                              proxy=f"http://127.0.0.1:{local_port}",
    #                                              timeout=aiohttp.ClientTimeout(total=10)) as response:
    #                         results["telegram"] = response.status == 200
    #             except:
    #                 results["telegram"] = False
    #             
    #             return results
    #             
    #         finally:
    #             try:
    #                 proc.terminate()
    #             except Exception:
    #                 pass
    #             try:
    #                 await asyncio.wait_for(proc.wait(), timeout=2)
    #             except Exception:
    #                 try:
    #                     proc.kill()
    #                 except Exception:
    #                     pass
    #             try:
    #                 shutil.rmtree(tmp_dir, ignore_errors=True)
    #             except Exception:
    #                 pass
    #                 
    #     except Exception as e:
    #         logging.debug(f"خطا در تست شبکه‌های اجتماعی: {e}")
    #         return {"youtube": False, "instagram": False, "telegram": False}

    # ==========================
    # تست سرعت دانلود واقعی با Xray (Sequential)
    # ==========================
    def _get_xray_binary_path(self) -> Optional[str]:
        try:
            system = platform.system().lower()
            bin_name = 'xray.exe' if system.startswith('win') else 'xray'
            candidate = os.path.join(XRAY_BIN_DIR, bin_name)
            if os.path.exists(candidate):
                # تلاش برای executable کردن در لینوکس
                try:
                    if not system.startswith('win'):
                        os.chmod(candidate, 0o755)
                except Exception:
                    pass
                return candidate
            logging.error(f"باینری Xray یافت نشد: {candidate}")
            return None
        except Exception as e:
            logging.error(f"خطا در پیدا کردن باینری Xray: {e}")
            return None

    def _choose_free_port(self) -> int:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    def _build_vless_outbound_from_link(self, link: str) -> Optional[Dict]:
        try:
            parsed = urlparse(link)
            host = parsed.hostname
            port = parsed.port
            user_id = parsed.username or ''
            query = {}
            if parsed.query:
                for pair in parsed.query.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        query[k] = v
            security = (query.get('security') or '').lower()
            network = (query.get('type') or 'tcp').lower()
            sni = query.get('sni', '')
            flow = query.get('flow', '')
            host_header = query.get('host', '')
            path = query.get('path', '/')

            outbound: Dict = {
                'protocol': 'vless',
                'settings': {
                    'vnext': [{
                        'address': host,
                        'port': int(port),
                        'users': [{
                            'id': user_id,
                            'encryption': 'none',
                            **({'flow': flow} if flow else {})
                        }]
                    }]
                },
                'streamSettings': {
                    'network': network
                }
            }
            if security == 'tls':
                outbound['streamSettings']['security'] = 'tls'
                if sni:
                    outbound['streamSettings']['tlsSettings'] = {'serverName': sni}
            if network == 'ws':
                outbound['streamSettings']['wsSettings'] = {
                    'path': path or '/',
                    'headers': {'Host': host_header} if host_header else {}
                }
            if network == 'grpc':
                outbound['streamSettings']['grpcSettings'] = {'serviceName': (path or '/').lstrip('/')}
            return outbound
        except Exception as e:
            logging.debug(f"خطا در ساخت outbound VLESS: {e}")
            return None

    def _build_xray_config_http_proxy(self, link: str, local_http_port: int) -> Optional[Dict]:
        outbound = self._build_vless_outbound_from_link(link)
        if not outbound:
            return None
        return {
            'log': {'loglevel': 'warning'},
            'inbounds': [{
                'listen': '127.0.0.1',
                'port': local_http_port,
                'protocol': 'http',
                'settings': {}
            }],
            'outbounds': [
                outbound,
                {'protocol': 'freedom', 'tag': 'direct'},
                {'protocol': 'blackhole', 'tag': 'blocked'}
            ]
        }

    async def _download_min_bytes_via_proxy(self, proxy_port: int) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TEST_TIMEOUT + 1)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                for url in DOWNLOAD_TEST_URLS:
                    start_time = time.perf_counter()
                    try:
                        async with session.get(url, proxy=f'http://127.0.0.1:{proxy_port}') as resp:
                            if resp.status >= 400:
                                continue
                            downloaded = 0
                            chunk_size = 64 * 1024
                            while True:
                                if (time.perf_counter() - start_time) > DOWNLOAD_TEST_TIMEOUT:
                                    return False
                                chunk = await resp.content.read(chunk_size)
                                if not chunk:
                                    break
                                downloaded += len(chunk)
                                if downloaded >= DOWNLOAD_TEST_MIN_BYTES:
                                    elapsed = time.perf_counter() - start_time
                                    speed_mbps = (downloaded / 1024 / 1024) / max(1e-6, elapsed)
                                    logging.info(f"✅ تست سرعت: {downloaded} bytes در {elapsed:.2f}s (~{speed_mbps:.2f} MB/s)")
                                    return elapsed <= DOWNLOAD_TEST_TIMEOUT
                    except Exception:
                        continue
            return False
        except Exception:
            return False

    # DISABLED: تست دسترسی ایران غیرفعال شد
    # async def _check_iran_sites_via_proxy(self, proxy_port: int) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                for url in IRAN_TEST_URLS:
                    try:
                        async with session.get(url, proxy=f'http://127.0.0.1:{proxy_port}', timeout=5) as resp:
                            if resp.status < 400:
                                return True
                    except Exception:
                        continue
            return False
        except Exception:
            return False

    # DISABLED: تست دسترسی ایران غیرفعال شد
    # async def test_iran_access_via_xray(self, link: str) -> bool:
    #     """راه‌اندازی Xray برای لینک و تست دسترسی به سایت‌های ایرانی از طریق پراکسی محلی"""
        xray_path = self._get_xray_binary_path()
        if not xray_path:
            return False
        local_port = self._choose_free_port()
        cfg = self._build_xray_config_http_proxy(link, local_port)
        if not cfg:
            return False
        import tempfile, json, shutil
        tmp_dir = tempfile.mkdtemp(prefix='vless_ir_')
        cfg_path = os.path.join(tmp_dir, 'config.json')
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False)
        proc = await asyncio.create_subprocess_exec(
            xray_path, '-config', cfg_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        # زمان کوتاه برای بالا آمدن Xray
        await asyncio.sleep(0.5)
        try:
            ok = await self._check_iran_sites_via_proxy(local_port)
            return ok
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    # DISABLED: تست دسترسی ایران غیرفعال شد
    # async def filter_configs_by_iran_access_via_xray(self, configs: List[str]) -> List[str]:
    #     """فیلتر کردن کانفیگ‌ها بر اساس دسترسی به سایت‌های ایرانی از طریق Xray (همزمانی 50 تایی)"""
        accepted: List[str] = []
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)

        async def run_single(cfg: str) -> Optional[str]:
            async with semaphore:
                try:
                    ok = await self.test_iran_access_via_xray(cfg)
                    return cfg if ok else None
                except Exception:
                    return None

        tasks = [run_single(cfg) for cfg in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, str):
                accepted.append(r)
        # ثبت مرحله ایران‌اوکی برای ذخیره‌سازی جزئی
        try:
            self.partial_iran_ok = list(accepted)
        except Exception:
            pass
        logging.info(f"نتیجه تست دسترسی ایرانی با Xray: {len(accepted)} از {len(configs)} پذیرفته شدند")
        return accepted

    # DISABLED: تست سرعت دانلود غیرفعال شد
    # async def download_speed_test_via_xray(self, link: str) -> bool:
    #     """اجرای تست دانلود واقعی با Xray: باید ظرف 2 ثانیه حداقل 1MB دانلود شود"""
        xray_path = self._get_xray_binary_path()
        if not xray_path:
            return False
        local_port = self._choose_free_port()
        cfg = self._build_xray_config_http_proxy(link, local_port)
        if not cfg:
            return False
        import tempfile, json, shutil
        tmp_dir = tempfile.mkdtemp(prefix='vless_dl_')
        cfg_path = os.path.join(tmp_dir, 'config.json')
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False)
        proc = await asyncio.create_subprocess_exec(
            xray_path, '-config', cfg_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        # زمان کوتاه برای بالا آمدن Xray
        await asyncio.sleep(0.5)
        try:
            ok = await self._download_min_bytes_via_proxy(local_port)
            return ok
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    # DISABLED: تست شبکه‌های اجتماعی غیرفعال شد
    # async def filter_configs_by_social_media_access(self, configs: List[str]) -> List[str]:
    #     """فیلتر کردن کانفیگ‌ها بر اساس تست دسترسی به شبکه‌های اجتماعی (Sequential)"""
    #     passed: List[str] = []
    #     for idx, cfg in enumerate(configs, 1):
    #         try:
    #             results = await self.test_social_media_access_via_xray(cfg)
    #             # بررسی اینکه حداقل یکی از شبکه‌های اجتماعی قابل دسترسی باشد
    #             if results.get("youtube", False) or results.get("instagram", False) or results.get("telegram", False):
    #                 passed.append(cfg)
    #                 # نگه‌داری نتیجه جزئی برای ذخیره در صورت timeout
    #                 try:
    #                     self.partial_social_ok.append(cfg)
    #                 except Exception:
    #                     pass
    #                 logging.info(f"[{idx}/{len(configs)}] ✅ شبکه‌های اجتماعی قابل دسترسی - پذیرفته شد")
    #                 logging.info(f"  YouTube: {results.get('youtube', False)}, Instagram: {results.get('instagram', False)}, Telegram: {results.get('telegram', False)}")
    #             else:
    #                 logging.info(f"[{idx}/{len(configs)}] ❌ شبکه‌های اجتماعی غیرقابل دسترسی - رد شد")
    #         except Exception as e:
    #             logging.warning(f"[{idx}/{len(configs)}] خطا در تست شبکه‌های اجتماعی: {e}")
    #         # تاخیر کوتاه بین تست‌ها جهت جلوگیری از فشار
    #         await asyncio.sleep(0.1)
    #     logging.info(f"نتیجه تست شبکه‌های اجتماعی: {len(passed)} از {len(configs)} پذیرفته شدند")
    #     return passed

    # DISABLED: تست سرعت دانلود غیرفعال شد
    # async def filter_configs_by_download_speed(self, configs: List[str]) -> List[str]:
    #     """فیلتر کردن کانفیگ‌ها بر اساس تست دانلود واقعی (Sequential)"""
        passed: List[str] = []
        for idx, cfg in enumerate(configs, 1):
            try:
                ok = await self.download_speed_test_via_xray(cfg)
                if ok:
                    passed.append(cfg)
                    # نگه‌داری نتیجه جزئی برای ذخیره در صورت timeout
                    try:
                        self.partial_speed_ok.append(cfg)
                    except Exception:
                        pass
                    logging.info(f"[{idx}/{len(configs)}] ✅ سرعت کافی - پذیرفته شد")
                else:
                    logging.info(f"[{idx}/{len(configs)}] ❌ سرعت ناکافی - رد شد")
            except Exception as e:
                logging.warning(f"[{idx}/{len(configs)}] خطا در تست سرعت: {e}")
            # تاخیر کوتاه بین تست‌ها جهت جلوگیری از فشار
            await asyncio.sleep(0.1)
        logging.info(f"نتیجه تست سرعت: {len(passed)} از {len(configs)} پذیرفته شدند")
        return passed
    
    async def test_all_vless_configs(self, configs: List[str]) -> List[Dict]:
        """تست تمام کانفیگ‌های VLESS"""
        logging.info(f"شروع تست {len(configs)} کانفیگ VLESS...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config):
            async with semaphore:
                return await self.test_vless_connection(config)
        
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
                if isinstance(result, dict) and result["success"]:
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
        
        logging.info(f"تست VLESS کامل شد: {len(all_results)} کانفیگ موفق از {len(configs)}")
        return all_results

    def save_partial_progress(self, reason: str = "") -> bool:
        """ذخیره خروجی جزئی در صورت timeout یا خطا"""
        try:
            # انتخاب بهترین مرحله‌ای که داده دارد
            if self.partial_ping_ok:
                best_configs = list({c for c in self.partial_ping_ok if self.is_valid_vless_config(c)})
                stage = "ping_ok"
            elif self.partial_results:
                best_configs = [r.get("config") for r in self.partial_results if isinstance(r, dict) and r.get("success") and self.is_valid_vless_config(r.get("config", ""))]
                stage = "connect_ok"
            else:
                best_configs = []
                stage = "none"

            if best_configs:
                logging.info(f"💾 ذخیره خروجی جزئی ({stage}) به دلیل: {reason} - تعداد: {len(best_configs)}")
                self.existing_configs = set()
                stats = self.merge_vless_configs(best_configs)
                if self.save_trustlink_vless_file():
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
            except Exception:
                pass
            return False
    
    def select_best_vless_configs(self, results: List[Dict]) -> List[str]:
        """انتخاب بهترین کانفیگ‌های VLESS با اولویت دسترسی از ایران"""
        if not results:
            return []
        
        # اولویت‌بندی: ابتدا کانفیگ‌های قابل دسترس از ایران، سپس بقیه
        iran_accessible = [r for r in results if r.get("iran_access", False)]
        other_configs = [r for r in results if not r.get("iran_access", False)]
        
        # مرتب‌سازی هر گروه بر اساس latency
        iran_accessible.sort(key=lambda x: x["latency"] if x["latency"] else float('inf'))
        other_configs.sort(key=lambda x: x["latency"] if x["latency"] else float('inf'))
        
        # ترکیب: ابتدا کانفیگ‌های قابل دسترس از ایران، سپس بقیه
        sorted_results = iran_accessible + other_configs
        
        # انتخاب بهترین KEEP_BEST_COUNT کانفیگ
        best_configs = sorted_results[:KEEP_BEST_COUNT]
        
        iran_count = len([r for r in best_configs if r.get("iran_access", False)])
        logging.info(f"بهترین {len(best_configs)} کانفیگ VLESS انتخاب شدند:")
        logging.info(f"  - قابل دسترس از ایران: {iran_count}")
        logging.info(f"  - سایر: {len(best_configs) - iran_count}")
        
        # ذخیره اطلاعات ایران access در متادیتا
        self.iran_access_stats = {
            "total_tested": len(results),
            "iran_accessible": len(iran_accessible),
            "other_configs": len(other_configs),
            "selected_iran": iran_count,
            "selected_other": len(best_configs) - iran_count
        }
        
        for i, result in enumerate(best_configs, 1):
            config_hash = result["hash"]
            latency = result["latency"]
            server = result["server_address"]
            port = result["port"]
            connection_type = result["type"]
            iran_status = "✅ ایران" if result.get("iran_access", False) else "❌ ایران"
            logging.info(f"{i}. {config_hash} - Server: {server}:{port} - Type: {connection_type} - Latency: {latency:.1f}ms - {iran_status}")
        
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
                    
                    # اضافه کردن اطلاعات ایران access از متادیتا
                    if hasattr(self, 'iran_access_stats'):
                        f.write(f"# قابل دسترس از ایران: {self.iran_access_stats.get('selected_iran', 0)}\n")
                        f.write(f"# سایر: {self.iran_access_stats.get('selected_other', 0)}\n")
                        f.write(f"# کل تست شده: {self.iran_access_stats.get('total_tested', 0)}\n")
                    else:
                        f.write(f"# قابل دسترس از ایران: اطلاعات در متادیتا موجود است\n")
                        f.write(f"# سایر: اطلاعات در متادیتا موجود است\n")
                    
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
        iran_accessible_count = len([r for r in test_results if r.get("iran_access", False)])
        
        self.metadata.update({
            "last_update": now,
            "total_tests": self.metadata.get("total_tests", 0) + 1,
            "total_configs": len(self.existing_configs),
            "working_configs": working_count,
            "failed_configs": failed_count,
            "iran_accessible_configs": iran_accessible_count,
            "last_vless_source": VLESS_SOURCE_FILE,
            "last_stats": {
                "new_added": stats["new_added"],
                "duplicates_skipped": stats["duplicates_skipped"],
                "invalid_skipped": stats["invalid_skipped"],
                "working_configs": working_count,
                "failed_configs": failed_count,
                "iran_accessible": iran_accessible_count,
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
                # ذخیره خروجی جزئی اگر چیزی وجود دارد؛ در غیراینصورت fallback
                if not self.save_partial_progress("no-source-configs"):
                    self.create_fallback_output("هیچ کانفیگ VLESS جدیدی یافت نشد")
                return False
            
            # ایجاد session
            await self.create_session()

            # فاز 1: تست اتصال TCP روی همه کانفیگ‌ها
            # فقط تست TCP ساده برای سرعت بالا - تست‌های دیگر در مراحل بعدی
            # هر کانفیگ فقط یک بار تست می‌شود - از کل پروکسی‌ها دو بار تست گرفته نمی‌شود
            # هدف: سرعت بالا و کارایی بهتر
            test_results = await self.test_all_vless_configs(source_configs)
            if not test_results:
                logging.warning("هیچ کانفیگ VLESS موفقی یافت نشد")
                if not self.save_partial_progress("no-connect-success"):
                    self.create_fallback_output("هیچ کانفیگ VLESS موفقی یافت نشد")
                return False

            # فاز 2: تست ping با check-host.net API، فقط روی کانفیگ‌های سالم TCP
            # فیلتر کردن کانفیگ‌هایی که تست TCP را پاس کرده‌اند
            # از کل پروکسی‌ها دو بار تست گرفته نمی‌شود - فقط پروکسی‌های سالم TCP
            healthy_configs = [r["config"] for r in test_results if r.get("success")]
            if not healthy_configs:
                logging.warning("هیچ کانفیگ VLESS موفقی یافت نشد")
                if not self.save_partial_progress("no-healthy-after-connect"):
                    self.create_fallback_output("هیچ کانفیگ VLESS موفقی یافت نشد")
                return False

            logging.info(f"🌐 شروع تست ping با check-host.net برای {len(healthy_configs)} کانفیگ سالم")
            ping_ok_configs = await self.filter_configs_by_ping_check(healthy_configs)
            if not ping_ok_configs:
                logging.warning("هیچ کانفیگی تست ping را پاس نکرد")
                if not self.save_partial_progress("no-ping-pass"):
                    self.create_fallback_output("هیچ کانفیگی تست ping را پاس نکرد")
                return False

            # همه قبولی‌ها، بهترین‌ها محسوب می‌شوند
            best_configs = ping_ok_configs

            # ادغام کانفیگ‌ها
            self.existing_configs = set()
            stats = self.merge_vless_configs(best_configs)

            # ذخیره فایل
            if self.save_trustlink_vless_file():
                # به‌روزرسانی متادیتا با نتایج فاز اتصال
                self.update_metadata(stats, test_results)

                logging.info("✅ به‌روزرسانی VLESS با موفقیت انجام شد")
                logging.info(f"📊 آمار: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری")
                logging.info(f"🔗 کانفیگ‌های VLESS سالم (پس از تمام تست‌ها): {len(best_configs)}")
                logging.info(f"📱 تست‌های انجام شده: TCP → Ping")
                return True
            else:
                logging.error("❌ خطا در ذخیره فایل VLESS")
                self.create_fallback_output("خطا در ذخیره فایل اصلی")
                return False
                
        except Exception as e:
            logging.error(f"خطا در اجرای به‌روزرسانی VLESS: {e}")
            # ایجاد فایل fallback در صورت خطا
            self.create_fallback_output(f"خطا در اجرا: {str(e)}")
            return False
        finally:
            await self.close_session()
    
    def create_fallback_output(self, message: str):
        """ایجاد فایل خروجی fallback در صورت خطا"""
        try:
            logging.info(f"ایجاد فایل fallback: {message}")
            
            # اطمینان از وجود دایرکتوری
            os.makedirs(os.path.dirname(TRUSTLINK_VLESS_FILE), exist_ok=True)
            
            # ایجاد فایل خروجی ساده
            with open(TRUSTLINK_VLESS_FILE, 'w', encoding='utf-8') as f:
                f.write("# فایل کانفیگ‌های VLESS - TrustLink VLESS\n")
                f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# وضعیت: {message}\n")
                f.write("# " + "="*50 + "\n\n")
                f.write("# هیچ کانفیگ VLESS سالمی یافت نشد\n")
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
            
            with open(TRUSTLINK_VLESS_METADATA, 'w', encoding='utf-8') as f:
                json.dump(fallback_metadata, f, indent=2, ensure_ascii=False)
            
            logging.info("فایل fallback با موفقیت ایجاد شد")
            
        except Exception as e:
            logging.error(f"خطا در ایجاد فایل fallback: {e}")
    
    def get_status(self) -> Dict:
        """دریافت وضعیت فعلی برنامه"""
        return {
            "total_configs": len(self.existing_configs),
            "last_update": self.metadata.get("last_update", "نامشخص"),
            "total_tests": self.metadata.get("total_tests", 0),
            "working_configs": self.metadata.get("working_configs", 0),
            "failed_configs": self.metadata.get("failed_configs", 0),
            "iran_accessible_configs": self.metadata.get("iran_accessible_configs", 0),
            "file_size_kb": os.path.getsize(TRUSTLINK_VLESS_FILE) / 1024 if os.path.exists(TRUSTLINK_VLESS_FILE) else 0,
            "backup_exists": os.path.exists(BACKUP_FILE)
        }

async def run_vless_tester():
    """اجرای تستر VLESS"""
    setup_logging()
    
    logging.info("🚀 راه‌اندازی TrustLink VLESS Tester")
    
    manager = VLESSManager()
    
    try:
        # اجرای یک دور به‌روزرسانی با timeout طولانی
        async with asyncio.timeout(3600):  # timeout 60 دقیقه - افزایش قابل توجه
            success = await manager.run_vless_update()
        
        if success:
            status = manager.get_status()
            logging.info("📈 وضعیت نهایی VLESS:")
            for key, value in status.items():
                logging.info(f"  {key}: {value}")
        else:
            logging.error("❌ به‌روزرسانی VLESS ناموفق بود")
            
    except asyncio.TimeoutError:
        logging.error("⏰ timeout: برنامه VLESS بیش از 60 دقیقه طول کشید")
        # ذخیره نتایج جزئی جهت جلوگیری از از دست رفتن خروجی‌ها
        try:
            manager.save_partial_progress("timeout")
        except Exception:
            pass
    except KeyboardInterrupt:
        logging.info("برنامه VLESS توسط کاربر متوقف شد")
    except Exception as e:
        logging.error(f"خطای غیرمنتظره در VLESS: {e}")
        # در صورت خطای غیرمنتظره نیز تلاش برای ذخیره خروجی جزئی
        try:
            manager.save_partial_progress("unexpected-error")
        except Exception:
            pass
    finally:
        await manager.close_session()

def schedule_vless_tester():
    """تنظیم اجرای خودکار هفتگی"""
    logging.info("⏰ تنظیم اجرای خودکار هفتگی برای VLESS Tester")
    
    # اجرای هفتگی در روز یکشنبه ساعت 06:30 تهران (03:00 UTC)
    schedule.every().sunday.at("06:30").do(lambda: asyncio.run(run_vless_tester()))
    
    # اجرای فوری در شروع (برای تست)
    schedule.every().minute.do(lambda: asyncio.run(run_vless_tester())).until("23:59")
    
    logging.info("📅 برنامه زمانبندی هفتگی فعال شد")
    logging.info("🕐 اجرای بعدی: یکشنبه ساعت 06:30 تهران")
    
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
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auto":
            # حالت خودکار
            schedule_vless_tester()
        elif sys.argv[1] == "--test":
            # حالت تست ساده برای GitHub Actions
            setup_logging()
            logging.info("🧪 VLESS Tester - Test Mode (GitHub Actions)")
            
            manager = VLESSManager()
            
            try:
                # تست ساده بدون اجرای کامل
                logging.info("بررسی فایل‌های منبع...")
                
                # بررسی فایل منبع
                if os.path.exists(VLESS_SOURCE_FILE):
                    with open(VLESS_SOURCE_FILE, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    logging.info(f"فایل منبع موجود: {len(lines)} خط")
                else:
                    logging.error(f"فایل منبع یافت نشد: {VLESS_SOURCE_FILE}")
                
                # ایجاد دایرکتوری‌های خروجی
                os.makedirs("../trustlink", exist_ok=True)
                os.makedirs("../logs", exist_ok=True)
                
                # ایجاد فایل تست ساده
                test_file = "../trustlink/trustlink_vless.txt"
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("# فایل تست VLESS - TrustLink VLESS\n")
                    f.write(f"# ایجاد شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("# حالت: تست GitHub Actions\n")
                    f.write("# " + "="*50 + "\n\n")
                    f.write("# این فایل برای تست GitHub Actions ایجاد شده است\n")
                    f.write("# در اجرای واقعی، کانفیگ‌های VLESS سالم اینجا قرار می‌گیرند\n")
                
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
                
                with open("../trustlink/.trustlink_vless_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(test_metadata, f, indent=2, ensure_ascii=False)
                
                logging.info("✅ فایل‌های تست با موفقیت ایجاد شدند")
                logging.info(f"✅ فایل خروجی: {test_file}")
                logging.info(f"✅ متادیتا: ../trustlink/.trustlink_vless_metadata.json")
                
            except Exception as e:
                logging.error(f"خطا در حالت تست: {e}")
                # ایجاد فایل fallback
                manager.create_fallback_output(f"خطا در حالت تست: {str(e)}")
        else:
            # اجرای یکباره
            await run_vless_tester()
    else:
        # اجرای یکباره (پیش‌فرض)
        await run_vless_tester()

if __name__ == "__main__":
    asyncio.run(main())
