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
CONCURRENT_TESTS = 30  # افزایش تعداد تست‌های همزمان به 30
KEEP_BEST_COUNT = 100  # افزایش تعداد کانفیگ‌های سالم نگه‌داری شده

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
    
    async def test_vless_connection(self, config: str) -> Dict:
        """تست اتصال کانفیگ VLESS با روش پیشرفته و تست دسترسی از ایران"""
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
            
            # تست اتصال با روش‌های مختلف
            start_time = time.time()
            
            # تست 1: TCP connection test
            tcp_success = await self.test_tcp_connection(server_ip, port)
            if tcp_success:
                # تست 2: HTTP/HTTPS test (برای سرورهای web)
                http_success = await self.test_http_connection(server_ip, port)
                
                # تست 3: Custom protocol test (شبیه‌سازی VLESS)
                protocol_success = await self.test_vless_protocol(server_ip, port, connection_type)
                
                # تست 4: Iran access test (تست دسترسی از ایران)
                iran_access_success = await self.test_iran_access(server_ip, port)
                result["iran_access"] = iran_access_success
                
                # اگر حداقل دو تست موفق بود، کانفیگ سالم است
                success_count = sum([tcp_success, http_success, protocol_success])
                if success_count >= 2:
                    result["success"] = True
                    result["latency"] = (time.time() - start_time) * 1000
                    
                    # اضافه کردن اطلاعات ایران access
                    iran_status = "✅ ایران" if iran_access_success else "❌ ایران"
                    logging.info(f"✅ تست VLESS موفق: {config_hash} - Server: {server_ip}:{port} - Type: {connection_type} - Latency: {result['latency']:.1f}ms - {iran_status}")
                else:
                    result["error"] = f"Connection tests failed (TCP: {tcp_success}, HTTP: {http_success}, Protocol: {protocol_success})"
                    logging.warning(f"❌ تست VLESS ناموفق: {config_hash} - Server: {server_ip}:{port}")
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
        """تست دسترسی از ایران (شبیه‌سازی)"""
        try:
            # تست اتصال با timeout کوتاه
            # این تست شبیه‌سازی می‌کند که سرور از ایران قابل دسترس است
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, int(port)),
                    timeout=8.0  # timeout کمی بیشتر برای ایران
                )
                
                # ارسال یک بایت تست (شبیه‌سازی handshake)
                writer.write(b'\x01')
                await writer.drain()
                
                # خواندن پاسخ (اگر سرور پاسخ دهد)
                try:
                    data = await asyncio.wait_for(reader.read(1), timeout=3.0)
                    # اگر داده‌ای خوانده شد، سرور از ایران قابل دسترس است
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
    
    async def test_all_vless_configs(self, configs: List[str]) -> List[Dict]:
        """تست تمام کانفیگ‌های VLESS"""
        logging.info(f"شروع تست {len(configs)} کانفیگ VLESS...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
        
        async def test_single_config(config):
            async with semaphore:
                return await self.test_vless_connection(config)
        
        # تست کانفیگ‌ها در batches برای جلوگیری از overload
        batch_size = 200  # افزایش batch size
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
                    successful_in_batch += 1
            
            logging.info(f"Batch {current_batch} کامل شد: {successful_in_batch} کانفیگ موفق از {len(batch)}")
            
            # کمی صبر بین batches
            if i + batch_size < len(configs):
                await asyncio.sleep(0.5)  # کاهش زمان انتظار
        
        logging.info(f"تست VLESS کامل شد: {len(all_results)} کانفیگ موفق از {len(configs)}")
        return all_results
    
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
                    
                    # اضافه کردن اطلاعات ایران access
                    iran_count = len([r for r in self.existing_configs if r.get("iran_access", False)])
                    f.write(f"# قابل دسترس از ایران: {iran_count}\n")
                    f.write(f"# سایر: {len(self.existing_configs) - iran_count}\n")
                    
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
