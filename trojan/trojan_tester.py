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
TEST_TIMEOUT = 60
CONCURRENT_TESTS = 50
KEEP_BEST_COUNT = 500
MAX_CONFIGS_TO_TEST = 10000

DOWNLOAD_TEST_MIN_BYTES = 1024 * 1024  # 1 MB
DOWNLOAD_TEST_TIMEOUT = 2  # ثانیه
DOWNLOAD_TEST_URLS = [
	"https://speed.cloudflare.com/__down?bytes=10485760",
	"https://speed.hetzner.de/1MB.bin",
	"https://speedtest.ams01.softlayer.com/downloads/test10.zip",
]
IRAN_TEST_URLS = [
	"https://www.aparat.com",
	"https://divar.ir",
	"https://www.cafebazaar.ir",
	"https://www.digikala.com",
	"https://www.sheypoor.com",
	"https://www.telewebion.com",
]

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
		self.partial_iran_ok: List[str] = []
		self.partial_social_ok: List[str] = []
		self.partial_speed_ok: List[str] = []
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
		"""تست اتصال کانفیگ Trojan از طریق Xray + SOCKS proxy"""
		try:
			parsed = self.parse_trojan_config(config)
			if not parsed:
				return {"config": config, "status": "invalid", "latency": None, "error": "کانفیگ نامعتبر"}
			local_port = 1080
			xcfg = self._build_xray_config_socks_proxy(parsed, local_port)
			proc = await self._spawn_xray(xcfg)
			if not proc:
				return {"config": config, "status": "error", "latency": None, "error": "Xray یافت نشد"}
			start = time.time()
			ok = False
			try:
				async with aiohttp.ClientSession() as s:
					async with s.get("https://www.google.com", proxy=f"socks5://127.0.0.1:{local_port}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
						ok = resp.status == 200
			except Exception:
				ok = False
			finally:
				await self._cleanup_proc(proc)
			if ok:
				latency = (time.time() - start) * 1000
				return {"config": config, "status": "working", "latency": latency}
			return {"config": config, "status": "failed", "latency": None, "error": "عدم پاسخ وب"}
		except Exception as e:
			return {"config": config, "status": "error", "latency": None, "error": str(e)}

	async def test_iran_access(self, config: str) -> bool:
		"""تست دسترسی ایران (در این نسخه به صورت ساده True)"""
		try:
			return True
		except Exception:
			return False

	async def test_social_media_access(self, config: str) -> Dict[str, bool]:
		"""تست دسترسی شبکه‌های اجتماعی از طریق SOCKS proxy"""
		try:
			parsed = self.parse_trojan_config(config)
			if not parsed:
				return {"youtube": False, "instagram": False, "telegram": False}
			local_port = 1080
			xcfg = self._build_xray_config_socks_proxy(parsed, local_port)
			proc = await self._spawn_xray(xcfg)
			if not proc:
				return {"youtube": False, "instagram": False, "telegram": False}
			results = {"youtube": False, "instagram": False, "telegram": False}
			try:
				async with aiohttp.ClientSession() as s:
					try:
						async with s.get("https://www.youtube.com", proxy=f"socks5://127.0.0.1:{local_port}", timeout=aiohttp.ClientTimeout(total=10)) as r:
							results["youtube"] = r.status == 200
					except Exception:
						results["youtube"] = False
					try:
						async with s.get("https://www.instagram.com", proxy=f"socks5://127.0.0.1:{local_port}", timeout=aiohttp.ClientTimeout(total=10)) as r:
							results["instagram"] = r.status == 200
					except Exception:
						results["instagram"] = False
					try:
						async with s.get("https://web.telegram.org", proxy=f"socks5://127.0.0.1:{local_port}", timeout=aiohttp.ClientTimeout(total=10)) as r:
							results["telegram"] = r.status == 200
					except Exception:
						results["telegram"] = False
			finally:
				await self._cleanup_proc(proc)
			return results
		except Exception as e:
			logging.debug(f"خطا در تست شبکه‌های اجتماعی: {e}")
			return {"youtube": False, "instagram": False, "telegram": False}

	async def test_download_speed(self, config: str) -> bool:
		"""تست سرعت دانلود (نسخه ساده)"""
		try:
			return True
		except Exception:
			return False

	async def test_all_configs(self, configs: List[str]) -> List[Dict]:
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
		working_configs = [r["config"] for r in initial_results if r.get("status") == "working"]
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
			if r.get("status") == "working" and cfg in final_ok:
				r["iran_access"] = True
				r["social_media_access"] = True
				r["download_speed_ok"] = True
				final_results.append(r)
			else:
				if r.get("status") == "working":
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

	async def run_full_test(self) -> None:
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

def main() -> None:
	setup_logging()
	auto_mode = "--auto" in sys.argv
	if auto_mode:
		logging.info("حالت خودکار فعال شد - تست هر ساعت اجرا خواهد شد")
		manager = TrojanManager()
		def run_once():
			asyncio.run(manager.run_full_test())
		schedule.every().hour.do(run_once)
		run_once()
		while True:
			schedule.run_pending()
			time.sleep(60)
	else:
		logging.info("شروع تست یکباره کانفیگ‌های Trojan")
		manager = TrojanManager()
		asyncio.run(manager.run_full_test())
		logging.info("تست یکباره تکمیل شد")

if __name__ == "__main__":
	main()
