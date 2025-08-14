import asyncio
import aiohttp
import json
import re
import logging
from bs4 import BeautifulSoup
import os
import shutil
from datetime import datetime
import pytz
import base64
from urllib.parse import parse_qs, unquote
import jdatetime  
import platform
import zipfile
import tempfile
import socket
import time
from urllib.parse import urlparse
from asyncio.subprocess import PIPE, STDOUT

URLS_FILE = 'Files/urls.txt'
KEYWORDS_FILE = 'Files/key.json'
OUTPUT_DIR = 'configs'
README_FILE = 'README.md'
REQUEST_TIMEOUT = 15
CONCURRENT_REQUESTS = 10
MAX_CONFIG_LENGTH = 1500
MIN_PERCENT25_COUNT = 15

# Health-check settings (tuned for CI/GitHub Actions)
ENABLE_HEALTH_CHECK = os.getenv('ENABLE_HEALTH_CHECK', '1') == '1'
HEALTH_CHECK_CONCURRENCY = int(os.getenv('HEALTH_CHECK_CONCURRENCY', '6'))
MAX_HEALTH_CHECKS_PER_PROTOCOL = int(os.getenv('MAX_HEALTH_CHECKS_PER_PROTOCOL', '25'))
MAX_HEALTH_CHECKS_TOTAL = int(os.getenv('MAX_HEALTH_CHECKS_TOTAL', '120'))
XRAY_TEST_TIMEOUT = int(os.getenv('XRAY_TEST_TIMEOUT', '6'))
HEALTH_CHECK_DEADLINE_SECONDS = int(os.getenv('HEALTH_CHECK_DEADLINE_SECONDS', '360'))
MAX_HEALTHY_PER_PROTOCOL = int(os.getenv('MAX_HEALTHY_PER_PROTOCOL', '1000000'))
GLOBAL_TEST_URLS = [
    u.strip() for u in os.getenv(
        'GLOBAL_TEST_URLS',
        'https://cloudflare.com/cdn-cgi/trace,https://example.com'
    ).split(',') if u.strip()
]
FIRST_PHASE_HEALTH_CHECK_CONCURRENCY = int(os.getenv('FIRST_PHASE_HEALTH_CHECK_CONCURRENCY', str(HEALTH_CHECK_CONCURRENCY)))
FIRST_PHASE_MAX_HEALTH_CHECKS_PER_PROTOCOL = int(os.getenv('FIRST_PHASE_MAX_HEALTH_CHECKS_PER_PROTOCOL', '15'))
FIRST_PHASE_MAX_HEALTH_CHECKS_TOTAL = int(os.getenv('FIRST_PHASE_MAX_HEALTH_CHECKS_TOTAL', '60'))
FIRST_PHASE_DEADLINE_SECONDS = int(os.getenv('FIRST_PHASE_DEADLINE_SECONDS', '180'))
HEALTHY_OUTPUT_FILE = os.getenv('HEALTHY_OUTPUT_FILE', os.path.join('configs', 'Healthy.txt'))
IRAN_TEST_URLS = [
    u.strip() for u in os.getenv(
        'IRAN_TEST_URLS',
        'https://www.aparat.com,https://divar.ir,https://www.cafebazaar.ir,https://www.digikala.com'
    ).split(',') if u.strip()
]
XRAY_DIR = os.path.join('Files', 'xray-bin')
XRAY_BIN = None  # will be resolved by ensure_xray_binary()
XRAY_VERSION = os.getenv('XRAY_VERSION', 'latest')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

PROTOCOL_CATEGORIES = [
    "Vmess", "Vless", "Trojan", "ShadowSocks", "ShadowSocksR",
    "Tuic", "Hysteria2", "WireGuard"
]
SUPPORTED_FOR_HEALTH = {"Vmess", "Vless", "Trojan", "ShadowSocks"}
SUPPORTED_PREFIXES = ('vmess://', 'vless://', 'trojan://', 'ss://')
UNSUPPORTED_PREFIXES = ('ssr://', 'hy2://', 'hysteria2://', 'tuic://', 'tuic5://', 'wireguard://')

def is_supported_link(link):
    l = (link or '').strip().lower()
    return l.startswith(SUPPORTED_PREFIXES)

def is_persian_like(text):
    if not isinstance(text, str) or not text.strip():
        return False
    has_persian_char = False
    has_latin_char = False
    for char in text:
        if '\u0600' <= char <= '\u06FF' or char in ['\u200C', '\u200D']:
            has_persian_char = True
        elif 'a' <= char.lower() <= 'z':
            has_latin_char = True
    return has_persian_char and not has_latin_char

def decode_base64(data):
    try:
        data = data.replace('_', '/').replace('-', '+')
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.b64decode(data).decode('utf-8')
    except Exception:
        return None

def get_vmess_name(vmess_link):
    if not vmess_link.startswith("vmess://"):
        return None
    try:
        b64_part = vmess_link[8:]
        decoded_str = decode_base64(b64_part)
        if decoded_str:
            vmess_json = json.loads(decoded_str)
            return vmess_json.get('ps')
    except Exception as e:
        logging.warning(f"Failed to parse Vmess name from {vmess_link[:30]}...: {e}")
    return None

def get_ssr_name(ssr_link):
    if not ssr_link.startswith("ssr://"):
        return None
    try:
        b64_part = ssr_link[6:]
        decoded_str = decode_base64(b64_part)
        if not decoded_str:
            return None
        parts = decoded_str.split('/?')
        if len(parts) < 2:
            return None
        params_str = parts[1]
        params = parse_qs(params_str)
        if 'remarks' in params and params['remarks']:
            remarks_b64 = params['remarks'][0]
            return decode_base64(remarks_b64)
    except Exception as e:
        logging.warning(f"Failed to parse SSR name from {ssr_link[:30]}...: {e}")
    return None

def should_filter_config(config):
    if 'i_love_' in config.lower():
        return True
    percent25_count = config.count('%25')
    if percent25_count >= MIN_PERCENT25_COUNT:
        return True
    if len(config) >= MAX_CONFIG_LENGTH:
        return True
    if '%2525' in config:
        return True
    return False

async def fetch_url(session, url):
    try:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            text_content = ""
            for element in soup.find_all(['pre', 'code', 'p', 'div', 'li', 'span', 'td']):
                text_content += element.get_text(separator='\n', strip=True) + "\n"
            if not text_content:
                text_content = soup.get_text(separator=' ', strip=True)
            logging.info(f"Successfully fetched: {url}")
            return url, text_content
    except Exception as e:
        logging.warning(f"Failed to fetch or process {url}: {e}")
        return url, None

def find_matches(text, categories_data):
    matches = {category: set() for category in categories_data}
    for category, patterns in categories_data.items():
        for pattern_str in patterns:
            if not isinstance(pattern_str, str):
                continue
            try:
                is_protocol_pattern = any(proto_prefix in pattern_str for proto_prefix in [p.lower() + "://" for p in PROTOCOL_CATEGORIES])
                if category in PROTOCOL_CATEGORIES or is_protocol_pattern:
                    pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                    found = pattern.findall(text)
                    if found:
                        cleaned_found = {item.strip() for item in found if item.strip()}
                        matches[category].update(cleaned_found)
            except re.error as e:
                logging.error(f"Regex error for '{pattern_str}' in category '{category}': {e}")
    return {k: v for k, v in matches.items() if v}

def choose_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def ensure_xray_binary():
    global XRAY_BIN
    if XRAY_BIN and os.path.exists(XRAY_BIN):
        return XRAY_BIN
    os.makedirs(XRAY_DIR, exist_ok=True)
    system = platform.system().lower()
    if system.startswith('linux'):
        asset = 'Xray-linux-64.zip'
        bin_name = 'xray'
    elif system.startswith('win'):
        asset = 'Xray-windows-64.zip'
        bin_name = 'xray.exe'
    elif system.startswith('darwin'):
        asset = 'Xray-macos-64.zip'
        bin_name = 'xray'
    else:
        raise RuntimeError(f"Unsupported OS for Xray: {platform.system()}")
    candidate = os.path.join(XRAY_DIR, bin_name)
    if os.path.exists(candidate):
        # Ensure executable bit when using an existing binary (e.g., from cache)
        try:
            if not system.startswith('win'):
                os.chmod(candidate, 0o755)
        except Exception:
            pass
        XRAY_BIN = candidate
        return XRAY_BIN
    if XRAY_VERSION and XRAY_VERSION != 'latest':
        download_url = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_VERSION}/{asset}"
    else:
        download_url = f"https://github.com/XTLS/Xray-core/releases/latest/download/{asset}"
    zip_path = os.path.join(XRAY_DIR, asset)
    try:
        import urllib.request
        logging.info(f"Downloading Xray core from {download_url}")
        urllib.request.urlretrieve(download_url, zip_path)
    except Exception as e:
        logging.error(f"Failed to download Xray core: {e}")
        raise
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(XRAY_DIR)
        os.remove(zip_path)
    except Exception as e:
        logging.error(f"Failed to extract Xray: {e}")
        raise
    # locate binary (some archives include subfolder)
    found = None
    for root, dirs, files in os.walk(XRAY_DIR):
        if bin_name in files:
            found = os.path.join(root, bin_name)
            break
    if not found:
        raise RuntimeError('Xray binary not found after extraction')
    try:
        if not system.startswith('win'):
            os.chmod(found, 0o755)
    except Exception:
        pass
    XRAY_BIN = found
    return XRAY_BIN

def parse_ss_uri(uri):
    try:
        parsed = urlparse(uri)
        if parsed.netloc:
            auth_host = parsed.netloc
            if '@' in auth_host:
                auth, hostport = auth_host.split('@', 1)
                if ':' in auth:
                    method, password = auth.split(':', 1)
                else:
                    decoded = decode_base64(auth)
                    method, password = decoded.split(':', 1)
            else:
                decoded = decode_base64(auth_host)
                auth, hostport = decoded.rsplit('@', 1)
                method, password = auth.split(':', 1)
            host, port = hostport.split(':', 1)
            return {'address': host, 'port': int(port), 'method': method, 'password': password}
        else:
            b64 = uri.split('://', 1)[1].split('#')[0]
            decoded = decode_base64(b64)
            auth, hostport = decoded.rsplit('@', 1)
            method, password = auth.split(':', 1)
            host, port = hostport.split(':', 1)
            return {'address': host, 'port': int(port), 'method': method, 'password': password}
    except Exception as e:
        logging.debug(f"Failed to parse ss uri: {e}")
        return None

def parse_vmess_uri(uri):
    try:
        b64 = uri.split('://', 1)[1]
        decoded = decode_base64(b64)
        if not decoded:
            return None
        return json.loads(decoded)
    except Exception as e:
        logging.debug(f"Failed to parse vmess uri: {e}")
        return None

def parse_url_userinfo(uri):
    parsed = urlparse(uri)
    host = parsed.hostname
    port = parsed.port
    username = parsed.username
    password = parsed.password
    query = parse_qs(parsed.query)
    fragment = parsed.fragment
    return parsed, host, port, username, password, query, fragment

def build_outbound_from_link(link):
    l = link.strip()
    if l.startswith('ss://'):
        ss = parse_ss_uri(l)
        if not ss:
            return None
        return {
            'protocol': 'shadowsocks',
            'settings': {
                'servers': [{
                    'address': ss['address'],
                    'port': ss['port'],
                    'method': ss['method'],
                    'password': ss['password'],
                    'udp': True
                }]
            }
        }
    if l.startswith('trojan://'):
        parsed, host, port, username, password, query, fragment = parse_url_userinfo(l)
        sni = query.get('sni', [query.get('host', [''])[0]])[0] if query else ''
        network = query.get('type', ['tcp'])[0] if query else 'tcp'
        outbound = {
            'protocol': 'trojan',
            'settings': {
                'servers': [{
                    'address': host,
                    'port': int(port),
                    'password': username or password or ''
                }]
            },
            'streamSettings': {
                'network': network
            }
        }
        security = query.get('security', [''])[0] if query else ''
        if security == 'tls':
            outbound['streamSettings']['security'] = 'tls'
            if sni:
                outbound['streamSettings']['tlsSettings'] = {'serverName': sni}
        if network == 'ws':
            path = query.get('path', ['/'])[0]
            host_header = query.get('host', [''])[0]
            outbound['streamSettings']['wsSettings'] = {
                'path': path,
                'headers': {'Host': host_header} if host_header else {}
            }
        return outbound
    if l.startswith('vless://'):
        parsed, host, port, username, password, query, fragment = parse_url_userinfo(l)
        user_id = username or ''
        security = query.get('security', [''])[0] if query else ''
        network = query.get('type', ['tcp'])[0] if query else 'tcp'
        sni = query.get('sni', [''])[0] if query else ''
        flow = query.get('flow', [''])[0] if query else ''
        host_header = query.get('host', [''])[0] if query else ''
        path = query.get('path', ['/'])[0] if query else '/'
        outbound = {
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
                'path': path,
                'headers': {'Host': host_header} if host_header else {}
            }
        if network == 'grpc':
            outbound['streamSettings']['grpcSettings'] = {'serviceName': path.lstrip('/')} if path else {}
        return outbound
    if l.startswith('vmess://'):
        data = parse_vmess_uri(l)
        if not data:
            return None
        address = data.get('add') or data.get('address')
        port = int(data.get('port') or 0)
        user_id = data.get('id') or data.get('uuid')
        security = (data.get('tls') or '').lower()
        sni = data.get('sni') or data.get('host') or ''
        net = data.get('net') or 'tcp'
        path = data.get('path') or '/'
        host_header = data.get('host') or ''
        scy = data.get('scy') or 'auto'
        outbound = {
            'protocol': 'vmess',
            'settings': {
                'vnext': [{
                    'address': address,
                    'port': port,
                    'users': [{
                        'id': user_id,
                        'alterId': 0,
                        'security': scy
                    }]
                }]
            },
            'streamSettings': {
                'network': net
            }
        }
        if security == 'tls':
            outbound['streamSettings']['security'] = 'tls'
            if sni:
                outbound['streamSettings']['tlsSettings'] = {'serverName': sni}
        if net == 'ws':
            outbound['streamSettings']['wsSettings'] = {
                'path': path,
                'headers': {'Host': host_header} if host_header else {}
            }
        if net == 'grpc':
            outbound['streamSettings']['grpcSettings'] = {'serviceName': path.lstrip('/')} if path else {}
        return outbound
    # Unsupported for health-check: ssr, hy2, tuic, wireguard
    return None

def build_xray_config(link, local_http_port):
    outbound = build_outbound_from_link(link)
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

async def test_proxy_via_xray(link, test_urls, overall_timeout=None):
    if overall_timeout is None:
        overall_timeout = XRAY_TEST_TIMEOUT
    try:
        xray_path = ensure_xray_binary()
    except Exception:
        return False, None, None
    port = choose_free_port()
    cfg = build_xray_config(link, port)
    if not cfg:
        return False, None, None
    tmp_dir = tempfile.mkdtemp(prefix='xraycfg_')
    cfg_path = os.path.join(tmp_dir, 'config.json')
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False)
    proc = await asyncio.create_subprocess_exec(
        ensure_xray_binary(), '-config', cfg_path, stdout=PIPE, stderr=STDOUT
    )
    await asyncio.sleep(0.4)
    timeout = aiohttp.ClientTimeout(total=min(8, overall_timeout))
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            for url in test_urls:
                try:
                    t0 = time.perf_counter()
                    async with session.get(url, proxy=f'http://127.0.0.1:{port}') as resp:
                        if resp.status < 400:
                            latency = (time.perf_counter() - t0) * 1000.0
                            return True, latency, url
                except Exception:
                    continue
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
    return False, None, None

async def health_filter_configs(protocol_to_configs_map):
    if not ENABLE_HEALTH_CHECK:
        all_configs = set()
        for items in protocol_to_configs_map.values():
            all_configs.update(items)
        return all_configs, {k: set(v) for k, v in protocol_to_configs_map.items()}

    # Budget per protocol and total to keep runtime bounded in CI
    limited = {}
    total_budget = MAX_HEALTH_CHECKS_TOTAL
    protos = [p for p in PROTOCOL_CATEGORIES if p in protocol_to_configs_map and p in SUPPORTED_FOR_HEALTH]
    per_proto_budget = max(1, min(MAX_HEALTH_CHECKS_PER_PROTOCOL, total_budget // max(1, len(protos))))
    for proto in protos:
        items = list(protocol_to_configs_map.get(proto, []))
        limited[proto] = items[:per_proto_budget]
    selected = sum(len(v) for v in limited.values())
    remaining = max(0, total_budget - selected)
    if remaining > 0 and protos:
        extra = list(protocol_to_configs_map.get(protos[0], []))
        limited[protos[0]] = list(limited[protos[0]]) + extra[per_proto_budget:per_proto_budget+remaining]

    semaphore = asyncio.Semaphore(HEALTH_CHECK_CONCURRENCY)
    healthy_all = set()
    healthy_by_proto = {p: set() for p in protos}

    async def run_check(p, link):
        async with semaphore:
            ok, latency_ms, ok_url = await test_proxy_via_xray(link, IRAN_TEST_URLS)
            if ok:
                healthy_all.add(link)
                healthy_by_proto[p].add(link)

    tasks = []
    for p in protos:
        for link in limited.get(p, []):
            tasks.append(asyncio.create_task(run_check(p, link)))
    if tasks:
        # bounded wait with deadline so workflow doesn't hang
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=HEALTH_CHECK_DEADLINE_SECONDS)
        except asyncio.TimeoutError:
            logging.warning("Health check deadline reached; continuing with results so far.")
    return healthy_all, healthy_by_proto

async def two_phase_health_filter(protocol_to_configs_map):
    if not ENABLE_HEALTH_CHECK:
        all_configs = set()
        for items in protocol_to_configs_map.values():
            all_configs.update(items)
        return all_configs, {k: set(v) for k, v in protocol_to_configs_map.items()}

    # Phase 1: connectivity to global endpoints (quick liveness)
    protos = [p for p in PROTOCOL_CATEGORIES if p in protocol_to_configs_map and p in SUPPORTED_FOR_HEALTH]
    limited_phase1 = {}
    total_budget1 = FIRST_PHASE_MAX_HEALTH_CHECKS_TOTAL
    per_proto_budget1 = max(1, min(FIRST_PHASE_MAX_HEALTH_CHECKS_PER_PROTOCOL, total_budget1 // max(1, len(protos))))
    for proto in protos:
        items = list(protocol_to_configs_map.get(proto, []))
        limited_phase1[proto] = items[:per_proto_budget1]
    selected1 = sum(len(v) for v in limited_phase1.values())
    remaining1 = max(0, total_budget1 - selected1)
    if remaining1 > 0 and protos:
        extra = list(protocol_to_configs_map.get(protos[0], []))
        limited_phase1[protos[0]] = list(limited_phase1[protos[0]]) + extra[per_proto_budget1:per_proto_budget1+remaining1]

    sem1 = asyncio.Semaphore(FIRST_PHASE_HEALTH_CHECK_CONCURRENCY)
    phase1_ok_all = set()
    phase1_ok_by_proto = {p: set() for p in protos}

    async def run_check_phase1(p, link):
        async with sem1:
            ok, latency_ms, ok_url = await test_proxy_via_xray(link, GLOBAL_TEST_URLS)
            if ok:
                phase1_ok_all.add(link)
                phase1_ok_by_proto[p].add(link)

    tasks1 = []
    for p in protos:
        for link in limited_phase1.get(p, []):
            tasks1.append(asyncio.create_task(run_check_phase1(p, link)))
    if tasks1:
        try:
            await asyncio.wait_for(asyncio.gather(*tasks1), timeout=FIRST_PHASE_DEADLINE_SECONDS)
        except asyncio.TimeoutError:
            logging.warning("Phase 1 health check deadline reached; moving on.")

    # Phase 2: only those that passed phase 1 → test Iranian endpoints
    phase2_input = {p: [l for l in phase1_ok_by_proto.get(p, set())] for p in protos}
    return await health_filter_configs(phase2_input)

def save_to_file(directory, category_name, items_set):
    if not items_set:
        return False, 0
    file_path = os.path.join(directory, f"{category_name}.txt")
    count = len(items_set)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in sorted(list(items_set)):
                f.write(f"{item}\n")
        logging.info(f"Saved {count} items to {file_path}")
        return True, count
    except Exception as e:
        logging.error(f"Failed to write file {file_path}: {e}")
        return False, 0

def generate_simple_readme(protocol_counts, country_counts, all_keywords_data, github_repo_path="Argh94/V2RayAutoConfig", github_branch="main"):
    tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tz)
    jalali_date = jdatetime.datetime.fromgregorian(datetime=now)
    time_str = jalali_date.strftime("%H:%M")
    date_str = jalali_date.strftime("%d-%m-%Y")
    timestamp = f"آخرین به‌روزرسانی: {time_str} {date_str}"

    raw_github_base_url = f"https://raw.githubusercontent.com/{github_repo_path}/refs/heads/{github_branch}/{OUTPUT_DIR}"

    total_configs = sum(protocol_counts.values())

    md_content = f"""# 🚀 V2Ray AutoConfig

<p align="center">
  <img src="https://img.shields.io/github/license/{github_repo_path}?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python" alt="Python 3.9+" />
  <img src="https://img.shields.io/github/actions/workflow/status/{github_repo_path}/scraper.yml?style=flat-square" alt="GitHub Workflow Status" />
  <img src="https://img.shields.io/github/last-commit/{github_repo_path}?style=flat-square" alt="Last Commit" />
  <br>
  <img src="https://img.shields.io/github/issues/{github_repo_path}?style=flat-square" alt="GitHub Issues" />
  <img src="https://img.shields.io/badge/Configs-{total_configs}-blue?style=flat-square" alt="Total Configs" />
  <img src="https://img.shields.io/github/stars/{github_repo_path}?style=social" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Project Status" />
  <img src="https://img.shields.io/badge/language-فارسی%20%26%20English-007EC6?style=flat-square" alt="Language" />
</p>

## {timestamp}

---

## 📖 درباره پروژه
این پروژه به‌صورت خودکار کانفیگ‌های VPN (پروتکل‌های مختلف مانند V2Ray، Trojan و Shadowsocks) را از منابع مختلف جمع‌آوری و دسته‌بندی می‌کند. هدف ما ارائه کانفیگ‌های به‌روز و قابل اعتماد برای کاربران است.

> **نکته:** کانفیگ‌هایی که بیش از حد طولانی یا حاوی کاراکترهای غیرضروری (مانند تعداد زیاد `%25`) باشند، برای اطمینان از کیفیت، فیلتر می‌شوند.

---

## 📁 کانفیگ‌های پروتکل‌ها
{f'در حال حاضر {total_configs} کانفیگ در دسترس است.' if total_configs else 'هیچ کانفیگ پروتکلی یافت نشد.'}

<div align="center">

| پروتکل | تعداد | لینک دانلود |
|:-------:|:-----:|:------------:|
"""
    if protocol_counts:
        for category_name, count in sorted(protocol_counts.items()):
            file_link = f"{raw_github_base_url}/{category_name}.txt"
            md_content += f"| {category_name} | {count} | [`{category_name}.txt`]({file_link}) |\n"
    else:
        md_content += "| - | - | - |\n"

    md_content += "</div>\n\n---\n\n"

    md_content += f"""
## 🌍 کانفیگ‌های کشورها
{f'کانفیگ‌ها بر اساس نام کشورها دسته‌بندی شده‌اند.' if country_counts else 'هیچ کانفیگ مرتبط با کشوری یافت نشد.'}

<div align="center">

| کشور | تعداد | لینک دانلود |
|:----:|:-----:|:------------:|
"""
    if country_counts:
        for country_category_name, count in sorted(country_counts.items()):
            flag_image_markdown = ""
            persian_name_str = ""
            iso_code_original_case = ""

            if country_category_name in all_keywords_data:
                keywords_list = all_keywords_data[country_category_name]
                if keywords_list and isinstance(keywords_list, list):
                    iso_code_lowercase_for_url = ""
                    for item in keywords_list:
                        if isinstance(item, str) and len(item) == 2 and item.isupper() and item.isalpha():
                            iso_code_lowercase_for_url = item.lower()
                            iso_code_original_case = item
                            break
                    if iso_code_lowercase_for_url:
                        flag_image_url = f"https://flagcdn.com/w20/{iso_code_lowercase_for_url}.png"
                        flag_image_markdown = f'<img src="{flag_image_url}" width="20" alt="{country_category_name} flag"> '
                    for item in keywords_list:
                        if isinstance(item, str):
                            if iso_code_original_case and item == iso_code_original_case:
                                continue
                            if item.lower() == country_category_name.lower() and not is_persian_like(item):
                                continue
                            if len(item) in [2, 3] and item.isupper() and item.isalpha() and item != iso_code_original_case:
                                continue
                            if is_persian_like(item):
                                persian_name_str = item
                                break
            display_parts = []
            if flag_image_markdown:
                display_parts.append(flag_image_markdown)
            display_parts.append(country_category_name)
            if persian_name_str:
                display_parts.append(f"({persian_name_str})")
            country_display_text = " ".join(display_parts)
            file_link = f"{raw_github_base_url}/{country_category_name}.txt"
            md_content += f"| {country_display_text} | {count} | [`{country_category_name}.txt`]({file_link}) |\n"
    else:
        md_content += "| - | - | - |\n"

    md_content += "</div>\n\n---\n\n"

    md_content += """
## 🛠️ نحوه استفاده
1. **دانلود کانفیگ‌ها**: از جدول‌های بالا، فایل موردنظر خود (بر اساس پروتکل یا کشور) را دانلود کنید.
2. **کلاینت‌های پیشنهادی**:
   - **V2Ray**: [v2rayNG](https://github.com/2dust/v2rayNG) (اندروید)، [V2RayX](https://github.com/Cenmrev/V2RayX) (مک)، [V2RayW](https://github.com/Cenmrev/V2RayW) (ویندوز)
   - **Shadowsocks**: [ShadowsocksX-NG](https://github.com/shadowsocks/ShadowsocksX-NG) (مک)، [Shadowsocks-Android](https://github.com/shadowsocks/shadowsocks-android)
   - **Trojan**: [Trojan-Qt5](https://github.com/Trojan-Qt5/Trojan-Qt5)
3. فایل کانفیگ را در کلاینت خود وارد کنید و اتصال را تست کنید.

> **توصیه**: برای بهترین عملکرد، کانفیگ‌ها را به‌صورت دوره‌ای بررسی و به‌روزرسانی کنید.

---

## 🤝 مشارکت
اگر مایل به مشارکت در پروژه هستید، می‌توانید:
- منابع جدید برای جمع‌آوری کانفیگ‌ها پیشنهاد دهید (فایل `urls.txt`).
- الگوهای جدید برای پروتکل‌ها یا کشورها اضافه کنید (فایل `key.json`).
- با ارسال Pull Request یا Issue در [گیت‌هاب](https://github.com/Argh94/V2RayAutoConfig) به بهبود پروژه کمک کنید.

---

## 📢 توجه
- این پروژه صرفاً برای اهداف آموزشی و تحقیقاتی ارائه شده است.
- لطفاً از کانفیگ‌ها به‌صورت مسئولانه و مطابق با قوانین کشور خود استفاده کنید.
- برای گزارش مشکلات یا پیشنهادات، از بخش [Issues](https://github.com/Argh94/V2RayAutoConfig/issues) استفاده کنید.
"""

    try:
        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(md_content)
        logging.info(f"Successfully generated {README_FILE}")
    except Exception as e:
        logging.error(f"Failed to write {README_FILE}: {e}")

async def main():
    if not os.path.exists(URLS_FILE) or not os.path.exists(KEYWORDS_FILE):
        logging.critical("Input files not found.")
        return

    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
        categories_data = json.load(f)

    protocol_patterns_for_matching = {
        cat: patterns for cat, patterns in categories_data.items() if cat in PROTOCOL_CATEGORIES
    }
    country_keywords_for_naming = {
        cat: patterns for cat, patterns in categories_data.items() if cat not in PROTOCOL_CATEGORIES
    }
    country_category_names = list(country_keywords_for_naming.keys())

    logging.info(f"Loaded {len(urls)} URLs and "
                 f"{len(categories_data)} total categories from key.json.")

    tasks = []
    sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
    async def fetch_with_sem(session, url_to_fetch):
        async with sem:
            return await fetch_url(session, url_to_fetch)
    async with aiohttp.ClientSession() as session:
        fetched_pages = await asyncio.gather(*[fetch_with_sem(session, u) for u in urls])

    final_configs_by_country = {cat: set() for cat in country_category_names}
    final_all_protocols = {cat: set() for cat in PROTOCOL_CATEGORIES}

    logging.info("Processing pages for config name association...")
    for url, text in fetched_pages:
        if not text:
            continue

        page_protocol_matches = find_matches(text, protocol_patterns_for_matching)
        all_page_configs_after_filter = set()
        for protocol_cat_name, configs_found in page_protocol_matches.items():
            if protocol_cat_name in PROTOCOL_CATEGORIES:
                for config in configs_found:
                    if should_filter_config(config):
                        continue
                    all_page_configs_after_filter.add(config)
                    final_all_protocols[protocol_cat_name].add(config)

        for config in all_page_configs_after_filter:
            name_to_check = None
            if '#' in config:
                try:
                    potential_name = config.split('#', 1)[1]
                    name_to_check = unquote(potential_name).strip()
                    if not name_to_check:
                        name_to_check = None
                except IndexError:
                    pass

            if not name_to_check:
                if config.startswith('ssr://'):
                    name_to_check = get_ssr_name(config)
                elif config.startswith('vmess://'):
                    name_to_check = get_vmess_name(config)

            if not name_to_check:
                continue

            current_name_to_check_str = name_to_check if isinstance(name_to_check, str) else ""

            for country_name_key, keywords_for_country_list in country_keywords_for_naming.items():
                text_keywords_for_country = []
                if isinstance(keywords_for_country_list, list):
                    for kw in keywords_for_country_list:
                        if isinstance(kw, str):
                            is_potential_emoji_or_short_code = (1 <= len(kw) <= 7)
                            is_alphanumeric = kw.isalnum()
                            if not (is_potential_emoji_or_short_code and not is_alphanumeric):
                                if not is_persian_like(kw):
                                    text_keywords_for_country.append(kw)
                                elif kw.lower() == country_name_key.lower():
                                    if kw not in text_keywords_for_country:
                                        text_keywords_for_country.append(kw)
                for keyword in text_keywords_for_country:
                    match_found = False
                    if not isinstance(keyword, str):
                        continue
                    is_abbr = (len(keyword) == 2 or len(keyword) == 3) and re.match(r'^[A-Z]+$', keyword)
                    if is_abbr:
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, current_name_to_check_str, re.IGNORECASE):
                            match_found = True
                    else:
                        if keyword.lower() in current_name_to_check_str.lower():
                            match_found = True
                    if match_found:
                        final_configs_by_country[country_name_key].add(config)
                        break
                if match_found:
                    break

    # Optional two-phase health-check & filtering
    logging.info("Starting health checks via Xray (two-phase)..." if ENABLE_HEALTH_CHECK else "Health checks disabled.")
    # Keep only parsable/supported links for health checks to avoid wasting time
    filtered_for_health = {p: {l for l in items if is_supported_link(l)} for p, items in final_all_protocols.items()}
    healthy_union, healthy_by_protocol = await two_phase_health_filter(filtered_for_health)

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logging.info(f"Saving files to directory: {OUTPUT_DIR}")

    protocol_counts = {}
    country_counts = {}

    # Save protocol files (filtered to healthy if health-check enabled)
    for category, items in final_all_protocols.items():
        items_to_save = items if not ENABLE_HEALTH_CHECK else healthy_by_protocol.get(category, set())
        if ENABLE_HEALTH_CHECK and MAX_HEALTHY_PER_PROTOCOL:
            items_to_save = set(list(items_to_save)[:MAX_HEALTHY_PER_PROTOCOL])
        saved, count = save_to_file(OUTPUT_DIR, category, items_to_save)
        if saved:
            protocol_counts[category] = count
    # Save country files (filtered to healthy if health-check enabled)
    for category, items in final_configs_by_country.items():
        if ENABLE_HEALTH_CHECK:
            items = {x for x in items if x in healthy_union}
        saved, count = save_to_file(OUTPUT_DIR, category, items)
        if saved:
            country_counts[category] = count

    # Save global healthy file
    if ENABLE_HEALTH_CHECK:
        saved, count = save_to_file(
            OUTPUT_DIR,
            os.path.splitext(os.path.basename(HEALTHY_OUTPUT_FILE))[0],
            healthy_union
        )
        if saved:
            protocol_counts['Healthy'] = count

    generate_simple_readme(protocol_counts, country_counts, categories_data,
                          github_repo_path="Argh94/V2RayAutoConfig",
                          github_branch="main")

    logging.info("--- Script Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
