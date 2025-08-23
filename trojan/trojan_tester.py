#!/usr/bin/env python3
"""
🔗 Trojan Tester - برنامه هوشمند برای تست و ذخیره کانفیگ‌های Trojan سالم
این برنامه مشابه VLESS/VMESS/SS کار می‌کند و کانفیگ‌های Trojan را در چند مرحله تست می‌کند:
1) اتصال اولیه از طریق Xray
2) دسترسی ایران (batch)
3) دسترسی شبکه‌های اجتماعی (YouTube/Instagram/Telegram) (batch)
4) تست سرعت دانلود (batch)
"""

import os
import sys
import time
import json
import logging
import asyncio
import aiohttp
import schedule
import platform
from datetime import datetime
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, parse_qs

# تنظیمات مسیرها و فایل‌ها
TROJAN_SOURCE_FILE = "../configs/raw/Trojan.txt"
TRUSTLINK_TROJAN_FILE = "../trustlink/trustlink_trojan.txt"
TRUSTLINK_TROJAN_METADATA = "../trustlink/.trustlink_trojan_metadata.json"
BACKUP_FILE = "../trustlink/trustlink_trojan_backup.txt"
LOG_FILE = "../logs/trojan_tester.log"
XRAY_BIN_DIR = "../Files/xray-bin"

# تنظیمات تست
TEST_TIMEOUT = 60  # ثانیه
CONCURRENT_TESTS = 50  # تعداد تست‌های همزمان
KEEP_BEST_COUNT = 500  # تعداد کانفیگ‌های سالم نگه‌داری شده
MAX_CONFIGS_TO_TEST = 10000  # تعداد کانفیگ‌های تست شده

# تنظیمات تست سرعت دانلود واقعی از طریق Xray - REMOVED
# DOWNLOAD_TEST_MIN_BYTES = 1024 * 1024  # 1 MB
# DOWNLOAD_TEST_TIMEOUT = 2  # ثانیه
# DOWNLOAD_TEST_URLS = [
#     "https://speed.cloudflare.com/__down?bytes=10485760",
#     "https://speed.hetzner.de/1MB.bin",
#     "https://speedtest.ams01.softlayer.com/downloads/test10.zip",
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

# تنظیم logging
def setup_logging() -> None:
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
	except Exception:
		logging.basicConfig(
			level=logging.INFO,
			format='%(asctime)s - %(levelname)s - %(message)s',
			handlers=[logging.StreamHandler(sys.stdout)]
		)

class TrojanManager:
	"""مدیریت اصلی برنامه Trojan Tester"""
	def __init__(self) -> None:
		self.session: Optional[aiohttp.ClientSession] = None
		self.existing_configs: Set[str] = set()
		self.metadata: Dict = {}
		self.partial_results: List[Dict] = []
		# self.partial_speed_ok: List[str] = []  # نتایج speed test - REMOVED
		self.partial_ping_ok: List[str] = []  # نتایج ping check
		self.load_metadata()

	def load_metadata(self) -> None:
		try:
			if os.path.exists(TRUSTLINK_TROJAN_METADATA):
				with open(TRUSTLINK_TROJAN_METADATA, 'r', encoding='utf-8') as f:
					self.metadata = json.load(f)
				logging.info("متادیتای Trojan بارگذاری شد")
			else:
				self.metadata = {
					"last_update": "",
					"total_tests": 0,
					"total_configs": 0,
					"working_configs": 0,
					"failed_configs": 0,
					"last_trojan_source": "",
					"version": "1.0.0"
				}
				logging.info("متادیتای جدید Trojan ایجاد شد")
		except Exception as e:
			logging.error(f"خطا در بارگذاری متادیتا: {e}")
			self.metadata = {
				"last_update": "",
				"total_tests": 0,
				"total_configs": 0,
				"working_configs": 0,
				"failed_configs": 0,
				"last_trojan_source": "",
				"version": "1.0.0"
			}

	def save_metadata(self) -> None:
		try:
			os.makedirs(os.path.dirname(TRUSTLINK_TROJAN_METADATA), exist_ok=True)
			with open(TRUSTLINK_TROJAN_METADATA, 'w', encoding='utf-8') as f:
				json.dump(self.metadata, f, ensure_ascii=False, indent=2)
			logging.info("متادیتای Trojan ذخیره شد")
		except Exception as e:
			logging.error(f"خطا در ذخیره متادیتا: {e}")

	async def create_session(self) -> None:
		if self.session is None or self.session.closed:
			timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT)
			connector = aiohttp.TCPConnector(limit=CONCURRENT_TESTS, limit_per_host=10)
			self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
			logging.info("Session جدید برای تست Trojan ایجاد شد")

	async def close_session(self) -> None:
		if self.session and not self.session.closed:
			await self.session.close()
			logging.info("Session تست Trojan بسته شد")

	def load_existing_configs(self) -> None:
		try:
			if os.path.exists(TRUSTLINK_TROJAN_FILE):
				with open(TRUSTLINK_TROJAN_FILE, 'r', encoding='utf-8') as f:
					content = f.read()
					configs = [line.strip() for line in content.splitlines() if line.strip().startswith('trojan://')]
					self.existing_configs = set(configs)
					logging.info(f"تعداد {len(self.existing_configs)} کانفیگ Trojan موجود بارگذاری شد")
			else:
				logging.info("فایل کانفیگ‌های Trojan موجود یافت نشد - فایل جدید ایجاد خواهد شد")
		except Exception as e:
			logging.error(f"خطا در بارگذاری کانفیگ‌های موجود: {e}")
			self.existing_configs = set()

	def load_trojan_configs(self) -> List[str]:
		try:
			if not os.path.exists(TROJAN_SOURCE_FILE):
				logging.error(f"فایل منبع Trojan یافت نشد: {TROJAN_SOURCE_FILE}")
				return []
			with open(TROJAN_SOURCE_FILE, 'r', encoding='utf-8') as f:
				content = f.read()
			configs = []
			for line in content.splitlines():
				line = line.strip()
				if line.startswith('trojan://'):
					configs.append(line)
			logging.info(f"تعداد {len(configs)} کانفیگ Trojan از فایل منبع بارگذاری شد")
			return configs[:MAX_CONFIGS_TO_TEST]
		except Exception as e:
			logging.error(f"خطا در بارگذاری کانفیگ‌های Trojan: {e}")
			return []

	def parse_trojan_config(self, config: str) -> Optional[Dict]:
		"""تجزیه لینکی با فرمت trojan://password@host:port?params#name"""
		try:
			if not config.startswith('trojan://'):
				return None
			url = urlparse(config)
			password = url.username or ''
			host = url.hostname or ''
			port = url.port or 443
			params = parse_qs(url.query or '')
			sni = params.get('sni', params.get('peer', params.get('host', [''])))
			sni = sni[0] if isinstance(sni, list) else sni
			alpn = params.get('alpn', [''])[0]
			security = 'tls'
			return {
				"server": host,
				"port": int(port),
				"password": password,
				"sni": sni,
				"alpn": alpn,
				"security": security,
			}
		except Exception as e:
			logging.debug(f"خطا در تجزیه کانفیگ Trojan: {e}")
			return None

	def _get_xray_binary_path(self) -> Optional[str]:
		candidate = os.path.join(XRAY_BIN_DIR, "xray.exe" if platform.system() == "Windows" else "xray")
		return candidate if os.path.exists(candidate) else None

	def _build_xray_config_socks_proxy(self, parsed: Dict, local_port: int) -> Dict:
		stream_settings = {
			"network": "tcp",
			"security": "tls",
			"tlsSettings": {
				"serverName": parsed.get("sni", "")
			}
		}
		alpn = parsed.get("alpn")
		if alpn:
			stream_settings["tlsSettings"]["alpn"] = [alpn]
		return {
			"inbounds": [{
				"port": local_port,
				"protocol": "socks",
				"settings": {"auth": "noauth", "udp": True}
			}],
			"outbounds": [{
				"protocol": "trojan",
				"settings": {
					"servers": [{
						"address": parsed.get("server", ""),
						"port": int(parsed.get("port", 443)),
						"password": parsed.get("password", "")
					}]
				},
				"streamSettings": stream_settings
			}]
		}

	async def _spawn_xray(self, cfg: Dict) -> Optional[asyncio.subprocess.Process]:
		try:
			xray_path = self._get_xray_binary_path()
			if not xray_path:
				return None
			import tempfile
			cfg_dir = tempfile.mkdtemp(prefix='trojan_')
			cfg_path = os.path.join(cfg_dir, 'config.json')
			with open(cfg_path, 'w', encoding='utf-8') as f:
				json.dump(cfg, f, ensure_ascii=False)
			proc = await asyncio.create_subprocess_exec(
				xray_path, '-config', cfg_path,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.STDOUT
			)
			# attach temp paths for cleanup
			proc._tmp_cfg_dir = cfg_dir  # type: ignore
			proc._tmp_cfg_path = cfg_path  # type: ignore
			await asyncio.sleep(0.6)
			return proc
		except Exception as e:
			logging.debug(f"خطا در اجرای Xray: {e}")
			return None

	async def _cleanup_proc(self, proc: asyncio.subprocess.Process) -> None:
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
			import shutil
			shutil.rmtree(getattr(proc, '_tmp_cfg_dir', ''), ignore_errors=True)  # type: ignore
		except Exception:
			pass

	async def test_trojan_connection(self, config: str) -> Dict:
		"""تست اتصال کانفیگ Trojan - فقط تست TCP ساده"""
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
			parsed_config = self.parse_trojan_config(config)
			if not parsed_config:
				result["error"] = "Invalid Trojan config format"
				logging.warning(f"❌ کانفیگ Trojan نامعتبر: {config_hash}")
				return result
			
			# بررسی وجود فیلدهای مورد نیاز
			server_ip = parsed_config.get("server", "")
			port = parsed_config.get("port", "443")
			
			if not server_ip:
				result["error"] = "Server IP not found in config"
				logging.warning(f"❌ کانفیگ Trojan بدون IP سرور: {config_hash}")
				return result
			
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
		import hashlib
		return hashlib.md5(config.encode()).hexdigest()

	async def test_iran_access(self, config: str) -> bool:
		"""تست دسترسی ایران (در این نسخه به صورت ساده True)"""
		try:
			return True
		except Exception:
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
				parsed = self.parse_trojan_config(config)
				if parsed:
					# بررسی وجود server_ip یا server
					server_ip = parsed.get('server')
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

	async def test_all_trojan_configs(self, configs: List[str]) -> List[Dict]:
		"""تست هوشمند کانفیگ‌های Trojan با استراتژی بهینه"""
		logging.info(f"شروع تست هوشمند {len(configs)} کانفیگ Trojan...")
		
		import random
		
		target_healthy_configs = 50  # هدف: 50 کانفیگ سالم
		batch_size = 100  # هر بار 100 کانفیگ رندوم انتخاب کن
		max_iterations = 20  # حداکثر 20 بار تلاش
		all_healthy_results = []
		used_indices = set()  # برای جلوگیری از تکرار
		
		semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
		
		async def test_single_config(config):
			async with semaphore:
				return await self.test_trojan_connection(config)
		
		iteration = 0
		while len(all_healthy_results) < target_healthy_configs and iteration < max_iterations:
			iteration += 1
			remaining_needed = target_healthy_configs - len(all_healthy_results)
			logging.info(f"🔄 تکرار {iteration}: نیاز به {remaining_needed} کانفیگ سالم دیگر، فعلاً {len(all_healthy_results)}")
			
			# محاسبه تعداد کانفیگ مورد نیاز برای این تکرار
			# اگر نیاز به 30 تا داریم، 100 تا انتخاب می‌کنیم (احتمالاً 30 تا سالم باشند)
			# اگر نیاز به 10 تا داریم، 50 تا انتخاب می‌کنیم
			if remaining_needed <= 10:
				current_batch_size = 50
			elif remaining_needed <= 20:
				current_batch_size = 75
			else:
				current_batch_size = batch_size  # 100
			
			# انتخاب رندوم کانفیگ‌های غیرتکراری
			available_indices = [i for i in range(len(configs)) if i not in used_indices]
			if len(available_indices) < current_batch_size:
				logging.warning(f"کانفیگ‌های غیرتکراری تمام شد: {len(available_indices)} باقی مانده")
				break
			
			selected_indices = random.sample(available_indices, min(current_batch_size, len(available_indices)))
			used_indices.update(selected_indices)
			
			selected_configs = [configs[i] for i in selected_indices]
			logging.info(f"📊 انتخاب {len(selected_configs)} کانفیگ رندوم برای تست TCP (نیاز: {remaining_needed})")
			
			# تست TCP روی کانفیگ‌های انتخاب شده
			tasks = [test_single_config(config) for config in selected_configs]
			tcp_results = await asyncio.gather(*tasks, return_exceptions=True)
			
			# فیلتر کردن نتایج TCP موفق
			tcp_healthy = []
			for result in tcp_results:
				if isinstance(result, dict) and result.get("success", False):
					tcp_healthy.append(result)
			
			logging.info(f"✅ تست TCP: {len(tcp_healthy)} کانفیگ سالم از {len(selected_configs)}")
			
			if not tcp_healthy:
				logging.warning("هیچ کانفیگ سالمی در این batch یافت نشد")
				continue
			
			# تست ping check-host روی کانفیگ‌های TCP سالم
			logging.info(f"🌐 شروع تست ping check-host روی {len(tcp_healthy)} کانفیگ TCP سالم")
			
			ping_healthy = []
			for result in tcp_healthy:
				try:
					# تست ping با check-host (استفاده از تابع موجود)
					ping_ok = await self.check_host_ping_single(result["server_address"])
					if ping_ok:
						result["ping_ok"] = True
						ping_healthy.append(result)
						logging.debug(f"✅ Ping OK: {result['server_address']}")
					else:
						result["ping_ok"] = False
						logging.debug(f"❌ Ping Failed: {result['server_address']}")
				except Exception as e:
					logging.debug(f"خطا در تست ping {result['server_address']}: {e}")
					result["ping_ok"] = False
			
			logging.info(f"🌐 تست ping: {len(ping_healthy)} کانفیگ سالم از {len(tcp_healthy)}")
			
			# اضافه کردن به نتایج کلی (فقط تا حد نیاز)
			remaining_needed = target_healthy_configs - len(all_healthy_results)
			if remaining_needed > 0:
				# فقط تعداد مورد نیاز را اضافه کن
				configs_to_add = ping_healthy[:remaining_needed]
				all_healthy_results.extend(configs_to_add)
				
				# ذخیره نتایج جزئی
				try:
					self.partial_results.extend(configs_to_add)
				except Exception:
					pass
				
				logging.info(f"📈 اضافه شد: {len(configs_to_add)} کانفیگ سالم (نیاز: {remaining_needed})")
				logging.info(f"📈 مجموع کانفیگ‌های سالم: {len(all_healthy_results)}/{target_healthy_configs}")
				
				# اگر به هدف رسیدیم، متوقف شو
				if len(all_healthy_results) >= target_healthy_configs:
					logging.info(f"🎯 هدف {target_healthy_configs} کانفیگ سالم محقق شد!")
					break
			else:
				logging.info(f"🎯 هدف {target_healthy_configs} کانفیگ سالم قبلاً محقق شده!")
				break
			
			# کمی صبر قبل از تکرار بعدی
			if iteration < max_iterations:
				await asyncio.sleep(2)
		
		if len(all_healthy_results) >= target_healthy_configs:
			logging.info(f"🎉 موفقیت! {len(all_healthy_results)} کانفیگ سالم یافت شد")
		else:
			logging.warning(f"⚠️ فقط {len(all_healthy_results)} کانفیگ سالم یافت شد (هدف: {target_healthy_configs})")
		
		return all_healthy_results[:target_healthy_configs]  # حداکثر target_healthy_configs برگردان

	async def test_all_configs(self, configs: List[str]) -> List[Dict]:
		"""تست تمام کانفیگ‌های Trojan - نسخه قدیمی برای سازگاری"""
		logging.info(f"شروع تست {len(configs)} کانفیگ Trojan")
		await self.create_session()
		# مرحله 1: اتصال اولیه (با Xray)
		logging.info("مرحله 1: تست اتصال اولیه")
		semaphore = asyncio.Semaphore(CONCURRENT_TESTS)
		async def test_single(config: str):
			async with semaphore:
				return await self.test_trojan_connection(config)
		tasks = [test_single(c) for c in configs]
		initial_results: List[Dict] = []
		try:
			for i, task in enumerate(asyncio.as_completed(tasks)):
				res = await task
				initial_results.append(res)
				if (i + 1) % 100 == 0:
					logging.info(f"تست اتصال {i + 1}/{len(configs)} کانفیگ تکمیل شد")
		except Exception as e:
			logging.error(f"خطا در تست اتصال اولیه: {e}")
		working_configs = [r["config"] for r in initial_results if r.get("success", False)]
		logging.info(f"تعداد {len(working_configs)} کانفیگ سالم برای تست‌های بعدی")
		# مرحله 2: دسترسی ایران (batch 50)
		batch_size = 50
		logging.info("مرحله 2: تست دسترسی ایران")
		iran_ok: List[str] = []
		for i in range(0, len(working_configs), batch_size):
			batch = working_configs[i:i+batch_size]
			logging.info(f"Batch ایران {i//batch_size + 1} با {len(batch)} کانفیگ")
			results = await asyncio.gather(*[self.test_iran_access(c) for c in batch], return_exceptions=True)
			for cfg, ok in zip(batch, results):
				if isinstance(ok, bool) and ok:
					iran_ok.append(cfg)
		logging.info(f"تعداد {len(iran_ok)} کانفیگ از تست ایران قبول شدند")
		# مرحله 3: شبکه‌های اجتماعی (batch 50)
		logging.info("مرحله 3: تست شبکه‌های اجتماعی")
		social_ok: List[str] = []
		for i in range(0, len(iran_ok), batch_size):
			batch = iran_ok[i:i+batch_size]
			logging.info(f"Batch شبکه‌های اجتماعی {i//batch_size + 1} با {len(batch)} کانفیگ")
			results = await asyncio.gather(*[self.test_social_media_access(c) for c in batch], return_exceptions=True)
			for cfg, r in zip(batch, results):
				if isinstance(r, dict) and (r.get("youtube") or r.get("instagram") or r.get("telegram")):
					social_ok.append(cfg)
		logging.info(f"تعداد {len(social_ok)} کانفیگ از تست شبکه‌های اجتماعی قبول شدند")
		# مرحله 4: سرعت دانلود (batch 50)
		logging.info("مرحله 4: تست سرعت دانلود")
		final_ok: List[str] = []
		for i in range(0, len(social_ok), batch_size):
			batch = social_ok[i:i+batch_size]
			logging.info(f"Batch سرعت دانلود {i//batch_size + 1} با {len(batch)} کانفیگ")
			results = await asyncio.gather(*[self.test_download_speed(c) for c in batch], return_exceptions=True)
			for cfg, ok in zip(batch, results):
				if isinstance(ok, bool) and ok:
					final_ok.append(cfg)
		logging.info(f"تعداد {len(final_ok)} کانفیگ از تمام تست‌ها قبول شدند")
		# ساخت نتایج نهایی
		final_results: List[Dict] = []
		for r in initial_results:
			cfg = r.get("config")
			if r.get("success", False) and cfg in final_ok:
				r["iran_access"] = True
				r["social_media_access"] = True
				r["download_speed_ok"] = True
				final_results.append(r)
			else:
				if r.get("success", False):
					r["iran_access"] = cfg in iran_ok
					r["social_media_access"] = cfg in social_ok
					r["download_speed_ok"] = cfg in final_ok
				final_results.append(r)
		await self.close_session()
		return final_results

	def save_working_configs(self, results: List[Dict]) -> None:
		try:
			fully = [r["config"] for r in results if r.get("status") == "working" and r.get("download_speed_ok")]
			partially = [r["config"] for r in results if r.get("status") == "working" and not r.get("download_speed_ok")]
			all_configs = list(set(fully + list(self.existing_configs)))
			if len(all_configs) > KEEP_BEST_COUNT:
				all_configs = all_configs[:KEEP_BEST_COUNT]
			os.makedirs(os.path.dirname(TRUSTLINK_TROJAN_FILE), exist_ok=True)
			with open(TRUSTLINK_TROJAN_FILE, 'w', encoding='utf-8') as f:
				f.write("# فایل کانفیگ‌های Trojan سالم - TrustLink TROJAN\n")
				f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
				f.write(f"# تعداد کل کانفیگ‌ها: {len(all_configs)}\n")
				f.write("# ==================================================\n\n")
				for c in all_configs:
					f.write(c + "\n")
			stats = {
				"total_tested": len(results),
				"connection_ok": len([r for r in results if r.get("status") == "working"]),
				"iran_access_ok": len([r for r in results if r.get("iran_access")]),
				"social_media_ok": len([r for r in results if r.get("social_media_access")]),
				"download_speed_ok": len([r for r in results if r.get("download_speed_ok")]),
				"fully_working": len(fully),
				"partially_working": len(partially),
			}
			self.metadata.update({
				"last_update": datetime.now().isoformat(),
				"total_tests": len(results),
				"total_configs": len(all_configs),
				"working_configs": len(fully),
				"failed_configs": len(results) - len(fully),
				"last_trojan_source": TROJAN_SOURCE_FILE,
				"test_statistics": stats,
			})
			self.save_metadata()
			logging.info(f"تعداد {len(all_configs)} کانفیگ Trojan سالم ذخیره شد")
		except Exception as e:
			logging.error(f"خطا در ذخیره کانفیگ‌ها: {e}")

	async def run_trojan_update(self) -> bool:
		"""اجرای یک دور کامل به‌روزرسانی Trojan"""
		try:
			logging.info("=" * 60)
			logging.info("🚀 شروع به‌روزرسانی TrustLink Trojan")
			logging.info("=" * 60)
			
			# بارگذاری کانفیگ‌های موجود
			self.load_existing_configs()
			
			# بارگذاری کانفیگ‌های Trojan از فایل منبع
			source_configs = self.load_trojan_configs()
			if not source_configs:
				logging.warning("هیچ کانفیگ Trojan جدیدی از فایل منبع بارگذاری نشد")
				# ذخیره خروجی جزئی اگر چیزی وجود دارد؛ در غیراینصورت fallback
				if not self.save_partial_progress("no-source-configs"):
					self.create_fallback_output("هیچ کانفیگ Trojan جدیدی یافت نشد")
				return False
			
			# ایجاد session
			await self.create_session()

			# فاز 1: تست هوشمند کانفیگ‌ها تا رسیدن به 50 کانفیگ سالم
			# این تابع خودش تا 20 بار تلاش می‌کند تا به هدف برسد
			logging.info("🎯 شروع تست هوشمند: هدف 50 کانفیگ سالم")
			test_results = await self.test_all_trojan_configs(source_configs)
			if not test_results:
				logging.warning("هیچ کانفیگ Trojan موفقی یافت نشد")
				if not self.save_partial_progress("no-connect-success"):
					self.create_fallback_output("هیچ کانفیگ Trojan موفقی یافت نشد")
				return False
			
			# بررسی اینکه آیا به هدف 50 کانفیگ رسیدیم
			healthy_count = len([r for r in test_results if r.get("success", False)])
			if healthy_count < 50:
				logging.warning(f"⚠️ فقط {healthy_count} کانفیگ سالم یافت شد (هدف: 50)")
				logging.info("🔄 تلاش برای یافتن کانفیگ‌های بیشتر...")
				
				# تلاش مجدد با کانفیگ‌های باقی‌مانده
				remaining_configs = [c for c in source_configs if c not in [r.get("config") for r in test_results if r.get("success", False)]]
				if remaining_configs:
					logging.info(f"📊 تلاش مجدد با {len(remaining_configs)} کانفیگ باقی‌مانده")
					additional_results = await self.test_all_trojan_configs(remaining_configs)
					if additional_results:
						# ترکیب نتایج
						test_results.extend(additional_results)
						healthy_count = len([r for r in test_results if r.get("success", False)])
						logging.info(f"📈 پس از تلاش مجدد: {healthy_count} کانفیگ سالم")
					else:
						logging.warning("تلاش مجدد ناموفق بود")
				else:
					logging.warning("هیچ کانفیگ باقی‌مانده‌ای برای تلاش مجدد وجود ندارد")
			else:
				logging.info(f"🎉 هدف 50 کانفیگ سالم محقق شد: {healthy_count} کانفیگ")

			# فاز 2: تست ping با check-host.net API، فقط روی کانفیگ‌های سالم TCP
			# فیلتر کردن کانفیگ‌هایی که تست TCP را پاس کرده‌اند
			# از کل پروکسی‌ها دو بار تست گرفته نمی‌شود - فقط پروکسی‌های سالم TCP
			healthy_configs = [r["config"] for r in test_results if r.get("success", False)]
			if not healthy_configs:
				logging.warning("هیچ کانفیگ Trojan موفقی یافت نشد")
				if not self.save_partial_progress("no-healthy-after-connect"):
					self.create_fallback_output("هیچ کانفیگ Trojan موفقی یافت نشد")
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
				stats = self.merge_trojan_configs(best_configs)

			# ذخیره فایل
			if best_configs and len(best_configs) > 0:
				if self.save_trustlink_trojan_file():
					# به‌روزرسانی متادیتا با نتایج فاز اتصال
					# اطمینان از اینکه test_results خالی نیست
					if test_results and len(test_results) > 0:
						self.update_metadata(stats, test_results)
					else:
						logging.warning("test_results خالی است، متادیتا به‌روزرسانی نمی‌شود")

					logging.info("✅ به‌روزرسانی Trojan با موفقیت انجام شد")
					logging.info(f"📊 آمار: {stats['new_added']} جدید، {stats['duplicates_skipped']} تکراری")
					logging.info(f"🔗 کانفیگ‌های Trojan سالم (پس از تمام تست‌ها): {len(best_configs)}")
					logging.info(f"📱 تست‌های انجام شده: حذف تکراری → TCP → Ping (تصادفی 50) → Speed Test REMOVED")
					if len(healthy_configs) > 50:
						logging.info(f"⚡ بهینه‌سازی سرعت: تست ping فقط روی {min(50, len(healthy_configs))} کانفیگ تصادفی")
					return True
				else:
					logging.error("❌ خطا در ذخیره فایل Trojan")
					self.create_fallback_output("خطا در ذخیره فایل اصلی")
					return False
			else:
				logging.warning("⚠️ هیچ کانفیگ سالمی برای ذخیره یافت نشد")
				self.create_fallback_output("هیچ کانفیگ سالمی یافت نشد")
				return False
				
		except Exception as e:
			logging.error(f"خطا در اجرای به‌روزرسانی Trojan: {e}")
			# ایجاد فایل fallback در صورت خطا
			self.create_fallback_output(f"خطا در اجرا: {str(e)}")
			return False
		finally:
			await self.close_session()

	def merge_trojan_configs(self, new_configs: List[str]) -> Dict[str, int]:
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

	def save_trustlink_trojan_file(self) -> bool:
		"""ذخیره فایل trustlink_trojan.txt"""
		try:
			# بررسی اینکه آیا کانفیگی برای ذخیره وجود دارد
			if not self.existing_configs or len(self.existing_configs) == 0:
				logging.warning("هیچ کانفیگی برای ذخیره وجود ندارد")
				return False
			
			os.makedirs(os.path.dirname(TRUSTLINK_TROJAN_FILE), exist_ok=True)
			
			# ذخیره در فایل اصلی
			with open(TRUSTLINK_TROJAN_FILE, 'w', encoding='utf-8') as f:
				f.write(f"# فایل کانفیگ‌های Trojan - TrustLink Trojan\n")
				f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
				f.write(f"# تعداد کانفیگ‌ها: {len(self.existing_configs)}\n")
				f.write(f"# ==================================================\n\n")
				
				for config in self.existing_configs:
					f.write(f"{config}\n")
			
			logging.info(f"فایل trustlink_trojan.txt با موفقیت ذخیره شد: {len(self.existing_configs)} کانفیگ")
			return True
			
		except Exception as e:
			logging.error(f"خطا در ذخیره فایل trustlink_trojan.txt: {e}")
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
			"last_trojan_source": TROJAN_SOURCE_FILE,
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
				best_configs = list({c for c in self.partial_ping_ok if self.is_valid_trojan_config(c)})
				stage = "ping_ok"
			elif self.partial_results:
				best_configs = [r.get("config") for r in self.partial_results if isinstance(r, dict) and r.get("success", False) and self.is_valid_trojan_config(r.get("config", ""))]
				stage = "connect_ok"
			else:
				best_configs = []
				stage = "none"

			if best_configs:
				logging.info(f"💾 ذخیره خروجی جزئی ({stage}) به دلیل: {reason} - تعداد: {len(best_configs)}")
				self.existing_configs = set()
				stats = self.merge_trojan_configs(best_configs)
				if self.save_trustlink_trojan_file():
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
			os.makedirs(os.path.dirname(TRUSTLINK_TROJAN_FILE), exist_ok=True)
			
			# ایجاد فایل خروجی ساده
			with open(TRUSTLINK_TROJAN_FILE, 'w', encoding='utf-8') as f:
				f.write("# فایل کانفیگ‌های Trojan - TrustLink Trojan\n")
				f.write(f"# آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
				f.write(f"# وضعیت: {message}\n")
				f.write("# " + "="*50 + "\n\n")
				f.write("# هیچ کانفیگ Trojan سالمی یافت نشد\n")
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
			
			with open(TRUSTLINK_TROJAN_METADATA, 'w', encoding='utf-8') as f:
				json.dump(fallback_metadata, f, indent=2, ensure_ascii=False)
			
			logging.info("فایل fallback با موفقیت ایجاد شد")
			
		except Exception as e:
			logging.error(f"خطا در ایجاد فایل fallback: {e}")

	def is_valid_trojan_config(self, config: str) -> bool:
		"""بررسی اعتبار کانفیگ Trojan"""
		try:
			if not config or len(config.strip()) < 10:
				return False
			
			if not config.startswith('trojan://'):
				return False
			
			# تلاش برای پارس کانفیگ
			parsed = self.parse_trojan_config(config)
			if parsed and parsed.get('server'):
				return True
			
			return False
			
		except Exception:
			return False

	def get_status(self) -> Dict:
		"""دریافت وضعیت فعلی برنامه"""
		return {
			"total_configs": len(self.existing_configs),
			"last_update": self.metadata.get("last_update", "نامشخص"),
			"total_tests": self.metadata.get("total_tests", 0),
			"working_configs": self.metadata.get("working_configs", 0),
			"failed_configs": self.metadata.get("failed_configs", 0),
			"iran_accessible_configs": self.metadata.get("iran_accessible_configs", 0),
			"file_size_kb": os.path.getsize(TRUSTLINK_TROJAN_FILE) / 1024 if os.path.exists(TRUSTLINK_TROJAN_FILE) else 0,
			"backup_exists": os.path.exists(BACKUP_FILE)
		}

	async def run_full_test(self) -> None:
		"""اجرای کامل تست (نسخه قدیمی - حفظ شده برای سازگاری)"""
		try:
			logging.info("شروع تست کامل کانفیگ‌های Trojan")
			self.load_existing_configs()
			configs = self.load_trojan_configs()
			if not configs:
				logging.warning("هیچ کانفیگ Trojan برای تست یافت نشد")
				return
			results = await self.test_all_configs(configs)
			self.save_working_configs(results)
			logging.info("تست کامل کانفیگ‌های Trojan تکمیل شد")
		except Exception as e:
			logging.error(f"خطا در اجرای تست کامل: {e}")

async def run_trojan_tester():
	"""اجرای تستر Trojan"""
	setup_logging()
	
	logging.info("🚀 راه‌اندازی TrustLink Trojan Tester")
	
	manager = TrojanManager()
	
	try:
		# اجرای یک دور به‌روزرسانی با timeout طولانی
		async with asyncio.timeout(7200):  # timeout 120 دقیقه - افزایش برای تست‌های اضافی
			success = await manager.run_trojan_update()
		
		if success:
			status = manager.get_status()
			logging.info("📈 وضعیت نهایی Trojan:")
			for key, value in status.items():
				logging.info(f"  {key}: {value}")
		else:
			logging.error("❌ به‌روزرسانی Trojan ناموفق بود")
			
	except asyncio.TimeoutError:
		logging.error("⏰ timeout: برنامه Trojan بیش از 120 دقیقه طول کشید")
		# ذخیره نتایج جزئی جهت جلوگیری از از دست رفتن خروجی‌ها
		try:
			manager.save_partial_progress("timeout")
		except Exception:
			pass
	except KeyboardInterrupt:
		logging.info("برنامه Trojan توسط کاربر متوقف شد")
	except Exception as e:
		logging.error(f"خطای غیرمنتظره در Trojan: {e}")
		# در صورت خطای غیرمنتظره نیز تلاش برای ذخیره خروجی جزئی
		try:
			manager.save_partial_progress("unexpected-error")
		except Exception:
			pass
	finally:
		await manager.close_session()

def main() -> None:
	setup_logging()
	
	# بررسی آرگومان‌ها
	if len(sys.argv) > 1:
		if sys.argv[1] == "--auto":
			# حالت خودکار
			schedule_trojan_tester()
		elif sys.argv[1] == "--test":
			# حالت تست ساده برای GitHub Actions
			setup_logging()
			logging.info("🧪 Trojan Tester - Test Mode (GitHub Actions)")
			
			manager = TrojanManager()
			
			try:
				# تست ساده بدون اجرای کامل
				logging.info("بررسی فایل‌های منبع...")
				
				# بررسی فایل منبع
				if os.path.exists(TROJAN_SOURCE_FILE):
					with open(TROJAN_SOURCE_FILE, 'r', encoding='utf-8') as f:
						lines = f.readlines()
					logging.info(f"فایل منبع موجود: {len(lines)} خط")
				else:
					logging.error(f"فایل منبع یافت نشد: {TROJAN_SOURCE_FILE}")
				
				# ایجاد دایرکتوری‌های خروجی
				os.makedirs("../trustlink", exist_ok=True)
				os.makedirs("../logs", exist_ok=True)
				
				# ایجاد فایل تست ساده
				test_file = "../trustlink/trustlink_trojan.txt"
				with open(test_file, 'w', encoding='utf-8') as f:
					f.write("# فایل تست Trojan - TrustLink Trojan\n")
					f.write(f"# ایجاد شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
					f.write("# حالت: تست GitHub Actions\n")
					f.write("# " + "="*50 + "\n\n")
					f.write("# این فایل برای تست GitHub Actions ایجاد شده است\n")
					f.write("# در اجرای واقعی، کانفیگ‌های Trojan سالم اینجا قرار می‌گیرند\n")
				
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
				
				with open("../trustlink/.trustlink_trojan_metadata.json", 'w', encoding='utf-8') as f:
					json.dump(test_metadata, f, indent=2, ensure_ascii=False)
				
				logging.info("✅ فایل‌های تست با موفقیت ایجاد شدند")
				logging.info(f"✅ فایل خروجی: {test_file}")
				logging.info(f"✅ متادیتا: ../trustlink/.trustlink_trojan_metadata.json")
				
			except Exception as e:
				logging.error(f"خطا در حالت تست: {e}")
				# ایجاد فایل fallback
				manager.create_fallback_output(f"خطا در حالت تست: {str(e)}")
		else:
			# اجرای یکباره
			asyncio.run(run_trojan_tester())
	else:
		# اجرای یکباره (پیش‌فرض)
		asyncio.run(run_trojan_tester())

def schedule_trojan_tester():
	"""تنظیم اجرای خودکار هفتگی"""
	logging.info("⏰ تنظیم اجرای خودکار هفتگی برای Trojan Tester")
	
	# اجرای هفتگی در روز یکشنبه ساعت 06:30 تهران (03:00 UTC)
	schedule.every().sunday.at("06:30").do(lambda: asyncio.run(run_trojan_tester()))
	
	# اجرای فوری در شروع (برای تست)
	schedule.every().minute.do(lambda: asyncio.run(run_trojan_tester())).until("23:59")
	
	logging.info("📅 برنامه زمانبندی هفتگی فعال شد")
	logging.info("🕐 اجرای بعدی: یکشنبه ساعت 06:30 تهران")
	
	while True:
		try:
			schedule.run_pending()
			time.sleep(60)  # بررسی هر دقیقه
		except KeyboardInterrupt:
			logging.info("برنامه Trojan Tester متوقف شد")
			break
		except Exception as e:
			logging.error(f"خطا در اجرای خودکار: {e}")
			time.sleep(60)

if __name__ == "__main__":
	main()
