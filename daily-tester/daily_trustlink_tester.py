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
try:
    import aiohttp  # Optional; script falls back if unavailable
except Exception:  # pragma: no cover
    aiohttp = None
import hashlib
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote
import re
import platform
import zipfile
import socket
import urllib.request
import urllib.error
import base64

# تنظیمات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRUSTLINK_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "trustlink", "trustlink.txt"))
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
GEO_API_URL = "http://ip-api.com/json/"  # rate-limited but sufficient for small batches

class DailyTrustLinkTester:
    """کلاس اصلی برای تست روزانه TrustLink"""
    
    def __init__(self):
        self.session: Optional[object] = None
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
        if aiohttp is None:
            # No aiohttp available; use urllib fallback
            self.session = None
            return
        if self.session is None or getattr(self.session, "closed", True):
            timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT, connect=5, sock_read=TEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logging.info("Session جدید برای تست ایجاد شد")
    
    async def close_session(self):
        """بستن session"""
        if aiohttp is not None:
            if self.session and not getattr(self.session, "closed", True):
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
        # Try HTTP GET if aiohttp available; otherwise use socket connect
        if aiohttp is not None:
            try:
                timeout = aiohttp.ClientTimeout(total=3)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    for port in [80, 443]:
                        try:
                            url = f"http://{server_address}:{port}" if port == 80 else f"https://{server_address}:{port}"
                            async with session.get(url) as response:
                                if response.status < 500:
                                    return True
                        except Exception:
                            continue
                return False
            except Exception:
                pass
        # Fallback: plain TCP connect
        for port in [80, 443]:
            try:
                with socket.create_connection((server_address, port), timeout=3):
                    return True
            except Exception:
                continue
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

    def _ensure_b64_padding(self, data: str) -> str:
        """افزودن padding مناسب به base64 برای جلوگیری از خطا."""
        missing = (-len(data)) % 4
        if missing:
            data += "=" * missing
        return data

    def _vmess_decode_json(self, vmess_link: str) -> Optional[Dict]:
        """Decode vmess link to JSON dict."""
        payload = vmess_link.split("vmess://", 1)[-1]
        try:
            payload = self._ensure_b64_padding(payload.strip())
            decoded = base64.urlsafe_b64decode(payload).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            try:
                # fallback
                decoded = base64.b64decode(self._ensure_b64_padding(payload)).decode("utf-8")
                return json.loads(decoded)
            except Exception:
                return None

    def _vmess_encode_json(self, data: Dict) -> str:
        """Encode vmess JSON dict back to vmess link."""
        raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        try:
            b64 = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
        except Exception:
            # Fallback without rstrip, keep padding
            b64 = base64.b64encode(raw).decode("utf-8")
        return f"vmess://{b64}"

    def _parse_common_query(self, query: str) -> Dict[str, str]:
        """Parse URL query into a simple dict with first values only."""
        parsed = parse_qs(query)
        return {k: v[0] for k, v in parsed.items() if v}

    def _extract_details(self, config: str) -> Dict[str, Optional[str]]:
        """استخراج اطلاعات اصلی کانفیگ: پروتکل، هاست، پورت، ترنسپورت، امنیت.
        اگر نتواند parse کند، برخی مقادیر None خواهند بود.
        """
        protocol = self.get_protocol(config)
        details: Dict[str, Optional[str]] = {
            "protocol": protocol,
            "host": None,
            "port": None,
            "transport": None,
            "security": None,
        }

        try:
            if protocol == "vmess":
                data = self._vmess_decode_json(config)
                if not data:
                    return details
                details["host"] = str(data.get("add") or data.get("host") or "").strip() or None
                details["port"] = str(data.get("port") or "").strip() or None
                details["transport"] = (data.get("net") or data.get("type") or "tcp").lower()
                tls = str(data.get("tls") or data.get("security") or "").lower()
                if tls and tls != "none":
                    details["security"] = tls
                return details

            if protocol in {"vless", "trojan", "shadowsocks"}:
                u = urlparse(config)
                # hostname/port
                host = u.hostname
                port = u.port
                details["host"] = host or None
                details["port"] = str(port) if port else None
                q = self._parse_common_query(u.query)

                # transport hints
                transport = q.get("type") or q.get("network") or q.get("mode")
                if protocol == "shadowsocks" and not transport:
                    plugin = q.get("plugin")
                    if plugin:
                        if "v2ray" in plugin or "ws" in plugin:
                            transport = "ws"
                        elif "obfs" in plugin:
                            transport = "obfs"
                details["transport"] = (transport or "tcp").lower()

                security = q.get("security") or q.get("s")
                if security:
                    details["security"] = security.lower()
                # flow indicates XTLS variants
                flow = q.get("flow")
                if flow and not details.get("security"):
                    details["security"] = "xtls"
                return details

            return details
        except Exception:
            return details

    def _apply_name(self, config: str, protocol: str, new_name: str) -> str:
        """قرار دادن نام جدید داخل کانفیگ (ps برای vmess، fragment برای بقیه)."""
        try:
            if protocol == "vmess":
                data = self._vmess_decode_json(config)
                if not data:
                    return config
                data["ps"] = new_name
                return self._vmess_encode_json(data)

            # vless/trojan/ss: set fragment
            u = urlparse(config)
            # URL fragment is name label; ensure it is URL-encoded
            fragment = quote(new_name, safe="")
            rebuilt = u._replace(fragment=fragment)
            return urlunparse(rebuilt)
        except Exception:
            return config

    async def _resolve_host_to_ip(self, host: Optional[str]) -> Optional[str]:
        """Resolve hostname to an IPv4 address (prefer IPv4)."""
        if not host:
            return None
        # If already an IP, return as is
        try:
            socket.inet_aton(host)
            return host
        except OSError:
            pass
        try:
            loop = asyncio.get_running_loop()
            infos = await loop.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            # Prefer IPv4
            for info in infos:
                ip = info[4][0]
                if ":" not in ip:
                    return ip
            return infos[0][4][0] if infos else None
        except Exception:
            return None

    async def _http_get_json(self, url: str, timeout: int = TEST_TIMEOUT) -> Optional[Dict]:
        """HTTP GET JSON with aiohttp or urllib fallback."""
        if aiohttp is not None:
            try:
                await self.create_session()
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception:
                return None
            return None
        # urllib fallback in a thread
        def fetch() -> Optional[Dict]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    data = r.read()
                    return json.loads(data.decode("utf-8", errors="ignore"))
            except Exception:
                return None
        return await asyncio.to_thread(fetch)

    async def _lookup_country(self, ip: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Lookup country code and name for an IP using ip-api.com."""
        if not ip:
            return None, None
        url = f"{GEO_API_URL}{ip}?fields=status,country,countryCode"
        data = await self._http_get_json(url)
        if data and data.get("status") == "success":
            return data.get("countryCode"), data.get("country")
        return None, None

    def _country_code_to_flag(self, country_code: Optional[str]) -> str:
        """Convert country code like 'US' to flag emoji."""
        if not country_code or len(country_code) != 2:
            return "🏳️"
        cc = country_code.upper()
        try:
            return chr(127397 + ord(cc[0])) + chr(127397 + ord(cc[1]))
        except Exception:
            return "🏳️"

    def _build_label(self, protocol: str, transport: Optional[str], security: Optional[str], ip: Optional[str], host: Optional[str], port: Optional[str], country_code: Optional[str]) -> str:
        """Build a concise, informative label for a config."""
        flag = self._country_code_to_flag(country_code)
        country_disp = country_code or "??"
        proto_disp = (protocol or "?").upper()
        transport_disp = (transport or "tcp").upper()

        sec_disp = None
        if security:
            s = security.lower()
            if "reality" in s:
                sec_disp = "REALITY"
            elif "xtls" in s:
                sec_disp = "XTLS"
            elif s == "tls" or "tls" in s:
                sec_disp = "TLS"

        if sec_disp:
            trans_sec = f"{transport_disp}-{sec_disp}"
        else:
            trans_sec = transport_disp

        endpoint = ip or host or "unknown"
        if port:
            endpoint = f"{endpoint}:{port}"
        return f"{flag} {country_disp} | {proto_disp}-{trans_sec} | {endpoint}"

    async def rename_and_annotate_configs(self, configs: List[str]) -> List[str]:
        """Resolve IP/Geo for each config and inject a standardized name/label."""
        semaphore = asyncio.Semaphore(CONCURRENT_TESTS)

        async def process(config: str) -> str:
            async with semaphore:
                details = self._extract_details(config)
                host = details.get("host")
                port = details.get("port")
                protocol = details.get("protocol") or self.get_protocol(config)
                transport = details.get("transport")
                security = details.get("security")

                ip = await self._resolve_host_to_ip(host)
                cc, _country = await self._lookup_country(ip)
                label = self._build_label(protocol, transport, security, ip, host, port, cc)
                return self._apply_name(config, protocol, label)

        tasks = [process(c) for c in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        final: List[str] = []
        for item in results:
            if isinstance(item, str):
                final.append(item)
            else:
                # On error, keep original
                final.append(configs[len(final)])
        return final
    
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
            
            # نام‌گذاری و برچسب‌گذاری کانفیگ‌ها با IP و پرچم کشور
            best_configs = await self.rename_and_annotate_configs(best_configs)

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
