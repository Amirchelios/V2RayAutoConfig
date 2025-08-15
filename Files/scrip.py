import asyncio
import aiohttp
import json
import re
import logging
from bs4 import BeautifulSoup
import os
import shutil
from datetime import datetime, timedelta
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
RAW_OUTPUT_SUBDIR = 'raw'
README_FILE = 'README.md'
REQUEST_TIMEOUT = 15
CONCURRENT_REQUESTS = 10
MAX_CONFIG_LENGTH = 1500
MIN_PERCENT25_COUNT = 15
DISABLE_CONFIG_FILTERS = os.getenv('DISABLE_CONFIG_FILTERS', '1') == '1'

# Health-check settings (tuned for CI/GitHub Actions)
ENABLE_HEALTH_CHECK = os.getenv('ENABLE_HEALTH_CHECK', '1') == '1'
HEALTH_CHECK_CONCURRENCY = int(os.getenv('HEALTH_CHECK_CONCURRENCY', '6'))
MAX_HEALTH_CHECKS_PER_PROTOCOL = int(os.getenv('MAX_HEALTH_CHECKS_PER_PROTOCOL', '25'))
MAX_HEALTH_CHECKS_TOTAL = int(os.getenv('MAX_HEALTH_CHECKS_TOTAL', '120'))
XRAY_TEST_TIMEOUT = int(os.getenv('XRAY_TEST_TIMEOUT', '6'))
HEALTH_CHECK_DEADLINE_SECONDS = int(os.getenv('HEALTH_CHECK_DEADLINE_SECONDS', '360'))
MAX_HEALTHY_PER_PROTOCOL = int(os.getenv('MAX_HEALTHY_PER_PROTOCOL', '1000000'))
HEALTH_CHECK_ALL = os.getenv('HEALTH_CHECK_ALL', '1') == '1'
KEEP_UNTESTED_ON_HEALTH = os.getenv('KEEP_UNTESTED_ON_HEALTH', '1') == '1'
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

# Persistent healthy configs management
PERSISTENT_HEALTHY_FILE = os.path.join('configs', 'PersistentHealthy.txt')
PERSISTENT_HEALTHY_METADATA_FILE = os.path.join('configs', '.persistent_healthy_metadata.json')
CLEANUP_INTERVAL_DAYS = 10

# GitHub Actions specific settings
GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS', 'false').lower() == 'true'
GITHUB_SHA = os.getenv('GITHUB_SHA', '')
GITHUB_RUN_ID = os.getenv('GITHUB_RUN_ID', '')

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

def should_cleanup_persistent_healthy():
    """Check if it's time to cleanup the persistent healthy configs file"""
    # In GitHub Actions, we need to be more aggressive with cleanup since files don't persist between runs
    if GITHUB_ACTIONS:
        # Check if we have a different commit SHA (new deployment)
        if os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
            try:
                with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    last_sha = metadata.get('last_commit_sha', '')
                    if last_sha != GITHUB_SHA:
                        logging.info(f"New commit detected (SHA: {GITHUB_SHA[:8]}), triggering cleanup")
                        return True
            except Exception as e:
                logging.warning(f"Error reading persistent healthy metadata: {e}")
                return True
        return False  # Don't cleanup on first run in GitHub Actions
    
    # Local development: use time-based cleanup
    if not os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
        return True
    
    try:
        with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            last_cleanup = datetime.fromisoformat(metadata.get('last_cleanup', '1970-01-01T00:00:00'))
            days_since_cleanup = (datetime.now() - last_cleanup).days
            return days_since_cleanup >= CLEANUP_INTERVAL_DAYS
    except Exception as e:
        logging.warning(f"Error reading persistent healthy metadata: {e}")
        return True

def should_cleanup_persistent_healthy_github_actions():
    """Special cleanup logic for GitHub Actions - only cleanup on major changes"""
    if not GITHUB_ACTIONS:
        return False
    
    # Only cleanup if:
    # 1. We have a completely different commit (major change)
    # 2. The file is corrupted or invalid
    # 3. It's been more than 30 days since last cleanup
    
    if os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
        try:
            with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                last_sha = metadata.get('last_commit_sha', '')
                last_cleanup = metadata.get('last_cleanup', '1970-01-01T00:00:00')
                
                # Check if it's a completely different branch/commit
                if last_sha and GITHUB_SHA:
                    # If commit SHA is completely different (not just a small change)
                    if not GITHUB_SHA.startswith(last_sha[:6]):
                        logging.info(f"Major commit change detected - triggering cleanup")
                        return True
                
                # Check if it's been too long since last cleanup
                try:
                    last_cleanup_date = datetime.fromisoformat(last_cleanup)
                    days_since_cleanup = (datetime.now() - last_cleanup_date).days
                    if days_since_cleanup >= 30:  # 30 days for GitHub Actions
                        logging.info(f"Long time since last cleanup ({days_since_cleanup} days) - triggering cleanup")
                        return True
                except:
                    pass
                    
        except Exception as e:
            logging.warning(f"Error reading metadata, triggering cleanup: {e}")
            return True
    
    return False

def cleanup_persistent_healthy():
    """Clean up the persistent healthy configs file and reset metadata"""
    try:
        if os.path.exists(PERSISTENT_HEALTHY_FILE):
            os.remove(PERSISTENT_HEALTHY_FILE)
            logging.info(f"Cleaned up persistent healthy configs file: {PERSISTENT_HEALTHY_FILE}")
        
        # Reset metadata with GitHub Actions specific info
        metadata = {
            'last_cleanup': datetime.now().isoformat(),
            'total_cleanups': 0,
            'github_actions': GITHUB_ACTIONS,
            'last_commit_sha': GITHUB_SHA,
            'last_run_id': GITHUB_RUN_ID
        }
        
        if os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
            with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
                metadata['total_cleanups'] = existing_metadata.get('total_cleanups', 0) + 1
        
        os.makedirs(os.path.dirname(PERSISTENT_HEALTHY_METADATA_FILE), exist_ok=True)
        with open(PERSISTENT_HEALTHY_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        if GITHUB_ACTIONS:
            logging.info(f"GitHub Actions cleanup completed. Commit SHA: {GITHUB_SHA[:8]}, Run ID: {GITHUB_RUN_ID}")
        else:
            logging.info(f"Local cleanup completed. Total cleanups: {metadata['total_cleanups']}")
        
        return True
    except Exception as e:
        logging.error(f"Error during persistent healthy cleanup: {e}")
        return False

def load_existing_persistent_healthy():
    """Load existing persistent healthy configs from file"""
    if not os.path.exists(PERSISTENT_HEALTHY_FILE):
        return set()
    
    try:
        with open(PERSISTENT_HEALTHY_FILE, 'r', encoding='utf-8') as f:
            configs = {line.strip() for line in f if line.strip()}
        
        if GITHUB_ACTIONS:
            logging.info(f"GitHub Actions: Loaded {len(configs)} existing persistent healthy configs from repository")
        else:
            logging.info(f"Loaded {len(configs)} existing persistent healthy configs")
        
        return configs
    except Exception as e:
        logging.error(f"Error loading persistent healthy configs: {e}")
        return set()

def save_persistent_healthy_configs(configs_set):
    """Save persistent healthy configs to file"""
    try:
        os.makedirs(os.path.dirname(PERSISTENT_HEALTHY_FILE), exist_ok=True)
        
        # Filter out any invalid configs before saving
        valid_configs = set()
        for config in configs_set:
            if config and isinstance(config, str) and config.strip():
                valid_configs.add(config.strip())
        
        with open(PERSISTENT_HEALTHY_FILE, 'w', encoding='utf-8') as f:
            for config in sorted(list(valid_configs)):
                f.write(f"{config}\n")
        
        logging.info(f"Saved {len(valid_configs)} persistent healthy configs to {PERSISTENT_HEALTHY_FILE}")
        return True
    except Exception as e:
        logging.error(f"Error saving persistent healthy configs: {e}")
        return False

def validate_persistent_healthy_file():
    """Validate the persistent healthy configs file and return count of valid configs"""
    if not os.path.exists(PERSISTENT_HEALTHY_FILE):
        return 0
    
    try:
        valid_configs = []
        with open(PERSISTENT_HEALTHY_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                config = line.strip()
                if config and len(config) > 10:  # Basic validation
                    valid_configs.append(config)
                elif config:  # Log invalid configs
                    logging.warning(f"Invalid config at line {line_num}: {config[:50]}...")
        
        # If there are invalid configs, rewrite the file with only valid ones
        if len(valid_configs) != len([line.strip() for line in open(PERSISTENT_HEALTHY_FILE, 'r', encoding='utf-8') if line.strip()]):
            logging.info("Rewriting persistent healthy file to remove invalid configs")
            save_persistent_healthy_configs(set(valid_configs))
        
        return len(valid_configs)
    except Exception as e:
        logging.error(f"Error validating persistent healthy configs file: {e}")
        return 0

def merge_and_update_persistent_healthy(new_healthy_configs):
    """Merge new healthy configs with existing persistent ones and save"""
    # Check if cleanup is needed
    if GITHUB_ACTIONS:
        # Use special GitHub Actions logic
        if should_cleanup_persistent_healthy_github_actions():
            logging.info("Major change detected in GitHub Actions - performing cleanup")
            cleanup_persistent_healthy()
            existing_configs = set()
        else:
            logging.info("No major changes detected - preserving existing configs")
            existing_configs = load_existing_persistent_healthy()
    else:
        # Local development logic
        if should_cleanup_persistent_healthy():
            logging.info("Performing scheduled cleanup of persistent healthy configs (every 10 days)")
            cleanup_persistent_healthy()
            existing_configs = set()
        else:
            existing_configs = load_existing_persistent_healthy()
    
    # Merge new configs with existing ones
    all_configs = existing_configs.union(new_healthy_configs)
    
    # Save the merged configs
    if save_persistent_healthy_configs(all_configs):
        if GITHUB_ACTIONS:
            logging.info(f"GitHub Actions: Successfully merged configs. Total: {len(all_configs)} (existing: {len(existing_configs)}, new: {len(new_healthy_configs)})")
        else:
            logging.info(f"Successfully merged configs. Total persistent healthy: {len(all_configs)} (existing: {len(existing_configs)}, new: {len(new_healthy_configs)})")
        return True
    else:
        logging.error("Failed to save merged persistent healthy configs")
        return False

def get_next_cleanup_date():
    """Get the next scheduled cleanup date for persistent healthy configs"""
    if GITHUB_ACTIONS:
        # In GitHub Actions, cleanup happens only on major changes
        if os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
            try:
                with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    last_cleanup = metadata.get('last_cleanup', '1970-01-01T00:00:00')
                    
                    # Check if it's been too long since last cleanup
                    try:
                        last_cleanup_date = datetime.fromisoformat(last_cleanup)
                        days_since_cleanup = (datetime.now() - last_cleanup_date).days
                        if days_since_cleanup >= 30:  # 30 days for GitHub Actions
                            return datetime.now()  # Cleanup needed now
                        else:
                            return last_cleanup_date + timedelta(days=30)  # Next cleanup in 30 days
                    except:
                        return datetime.now() + timedelta(days=30)
            except Exception:
                pass
        return datetime.now() + timedelta(days=30)  # Default: 30 days
    
    # Local development: use time-based cleanup
    if not os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
        return datetime.now() + timedelta(days=CLEANUP_INTERVAL_DAYS)
    
    try:
        with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            last_cleanup = datetime.fromisoformat(metadata.get('last_cleanup', '1970-01-01T00:00:00'))
            next_cleanup = last_cleanup + timedelta(days=CLEANUP_INTERVAL_DAYS)
            return next_cleanup
    except Exception:
        return datetime.now() + timedelta(days=CLEANUP_INTERVAL_DAYS)

def get_github_actions_status():
    """Get GitHub Actions specific status information"""
    if not GITHUB_ACTIONS:
        return None
    
    status = {
        'commit_sha': GITHUB_SHA[:8] if GITHUB_SHA else 'Unknown',
        'run_id': GITHUB_RUN_ID if GITHUB_RUN_ID else 'Unknown',
        'is_new_commit': False,
        'will_cleanup': False
    }
    
    if os.path.exists(PERSISTENT_HEALTHY_METADATA_FILE):
        try:
            with open(PERSISTENT_HEALTHY_METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                last_sha = metadata.get('last_commit_sha', '')
                status['is_new_commit'] = (last_sha != GITHUB_SHA)
                status['will_cleanup'] = should_cleanup_persistent_healthy_github_actions()
        except Exception:
            pass
    
    return status

def load_persistent_healthy_from_repository():
    """Try to load persistent healthy configs from the repository (for GitHub Actions)"""
    if not GITHUB_ACTIONS:
        return set()
    
    # In GitHub Actions, the file might exist from previous commits
    if os.path.exists(PERSISTENT_HEALTHY_FILE):
        try:
            with open(PERSISTENT_HEALTHY_FILE, 'r', encoding='utf-8') as f:
                configs = {line.strip() for line in f if line.strip()}
            logging.info(f"Found {len(configs)} existing configs in repository")
            return configs
        except Exception as e:
            logging.warning(f"Error reading existing configs from repository: {e}")
    
    return set()

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

def extract_remote_port_from_link(link):
    try:
        l = (link or '').strip()
        if l.startswith('ss://'):
            ss = parse_ss_uri(l)
            return ss.get('port') if ss else None
        if l.startswith('trojan://') or l.startswith('vless://'):
            parsed = urlparse(l)
            return int(parsed.port) if parsed and parsed.port else None
        if l.startswith('vmess://'):
            data = parse_vmess_uri(l)
            if data and (data.get('port') or data.get('port') == 0):
                try:
                    return int(data.get('port'))
                except Exception:
                    return None
            return None
    except Exception:
        return None
    return None

def apply_explicit_port_to_url(url, port):
    try:
        if not port:
            return url
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return url
        hostname = parsed.hostname
        new_netloc = f"{hostname}:{int(port)}"
        if parsed.username or parsed.password:
            userinfo = ''
            if parsed.username:
                userinfo += parsed.username
            if parsed.password:
                userinfo += f":{parsed.password}"
            new_netloc = f"{userinfo}@{new_netloc}"
        rebuilt = parsed._replace(netloc=new_netloc)
        return rebuilt.geturl()
    except Exception:
        return url

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
            remote_port = extract_remote_port_from_link(link)
            candidate_urls = []
            for base_url in test_urls:
                # Try the default URL first, then the explicit remote port variant
                candidate_urls.append(base_url)
                if remote_port:
                    candidate_urls.append(apply_explicit_port_to_url(base_url, remote_port))
            # Preserve order while removing duplicates
            seen = set()
            ordered_candidates = []
            for u in candidate_urls:
                if u not in seen:
                    seen.add(u)
                    ordered_candidates.append(u)
            for url in ordered_candidates:
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
    protos = [p for p in PROTOCOL_CATEGORIES if p in protocol_to_configs_map and p in SUPPORTED_FOR_HEALTH]
    if HEALTH_CHECK_ALL:
        for proto in protos:
            limited[proto] = list(protocol_to_configs_map.get(proto, []))
    else:
        total_budget = MAX_HEALTH_CHECKS_TOTAL
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
    if HEALTH_CHECK_ALL:
        for proto in protos:
            limited_phase1[proto] = list(protocol_to_configs_map.get(proto, []))
    else:
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

def generate_simple_readme(protocol_counts, country_counts, all_keywords_data, github_repo_path="Argh94/V2RayAutoConfig", github_branch="main", raw_protocol_counts=None, raw_country_counts=None):
    tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tz)
    jalali_date = jdatetime.datetime.fromgregorian(datetime=now)
    time_str = jalali_date.strftime("%H:%M")
    date_str = jalali_date.strftime("%d-%m-%Y")
    timestamp = f"آخرین به‌روزرسانی: {time_str} {date_str}"

    raw_github_base_url = f"https://raw.githubusercontent.com/{github_repo_path}/refs/heads/{github_branch}/{OUTPUT_DIR}"
    raw_box_base_url = f"{raw_github_base_url}/{RAW_OUTPUT_SUBDIR}"

    # Exclude synthetic 'Healthy' bucket from total count
    total_configs = sum(count for name, count in protocol_counts.items() if name != 'Healthy')

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

> **سیستم کانفیگ‌های سالم پایدار:** کانفیگ‌هایی که تست شده و سالم تشخیص داده می‌شوند، در فایل جداگانه‌ای ذخیره می‌شوند که {f'فقط در تغییرات عمده پاک‌سازی می‌شود (GitHub Actions)' if GITHUB_ACTIONS else 'هر 10 روز پاک‌سازی می‌شود'} تا کیفیت حفظ شود و تعداد زیادی کانفیگ سالم در طول زمان جمع‌آوری شود. **کانفیگ‌های قبلی حفظ می‌شوند و کانفیگ‌های جدید به آن‌ها اضافه می‌شوند.**

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

    # Add persistent healthy configs information
    persistent_healthy_count = validate_persistent_healthy_file()
    
    if persistent_healthy_count > 0:
        # Get next cleanup date
        next_cleanup = get_next_cleanup_date()
        days_until_cleanup = (next_cleanup - datetime.now()).days
        
        if GITHUB_ACTIONS:
            cleanup_info = "پاک‌سازی فقط در تغییرات عمده"
            cleanup_schedule = f"پاک‌سازی: فقط در تغییرات عمده"
        else:
            cleanup_info = f"{days_until_cleanup} روز دیگر"
            cleanup_schedule = f"پاک‌سازی بعدی در {days_until_cleanup} روز دیگر"
        
        md_content += f"""
## 🗂️ کانفیگ‌های سالم پایدار
کانفیگ‌هایی که در طول زمان تست شده‌اند و سالم تشخیص داده شده‌اند. {f'در GitHub Actions، این فایل فقط در تغییرات عمده پاک‌سازی می‌شود تا کانفیگ‌های قبلی حفظ شوند.' if GITHUB_ACTIONS else f'این فایل هر 10 روز پاک‌سازی می‌شود تا کیفیت حفظ شود.'}

<div align="center">

| نوع | تعداد | لینک دانلود | پاک‌سازی بعدی |
|:----:|:-----:|:------------:|:-------------:|
| کانفیگ‌های سالم پایدار | {persistent_healthy_count} | [`PersistentHealthy.txt`]({raw_github_base_url}/PersistentHealthy.txt) | {cleanup_info} |

</div>

> **📅 برنامه پاک‌سازی:** {cleanup_schedule}

---
"""
    else:
        if GITHUB_ACTIONS:
            cleanup_note = "در GitHub Actions، این فایل فقط در تغییرات عمده پاک‌سازی می‌شود تا کانفیگ‌های قبلی حفظ شوند."
        else:
            cleanup_note = "این فایل هر 10 روز پاک‌سازی می‌شود تا کیفیت حفظ شود."
        
        md_content += f"""
## 🗂️ کانفیگ‌های سالم پایدار
کانفیگ‌هایی که در طول زمان تست شده‌اند و سالم تشخیص داده شده‌اند. {cleanup_note}

> **توجه:** هنوز کانفیگ سالم پایداری جمع‌آوری نشده است. پس از اولین اجرای اسکریپت، این بخش به‌روزرسانی خواهد شد.

---

"""

    # Raw categorized boxes (protocols and countries)
    if raw_protocol_counts or raw_country_counts:
        md_content += "## کانفیگ‌های خام\n\n"
        # Raw protocols table
        md_content += "<div align=\"center\">\n\n"
        md_content += "| پروتکل | تعداد | لینک دانلود |\n"
        md_content += "|:-------:|:-----:|:------------:|\n"
        if raw_protocol_counts:
            for category_name, count in sorted(raw_protocol_counts.items()):
                file_link = f"{raw_box_base_url}/{category_name}.txt"
                md_content += f"| {category_name} | {count} | [`{category_name}.txt`]({file_link}) |\n"
        else:
            md_content += "| - | - | - |\n"
        md_content += "</div>\n\n"
        # Raw countries table
        md_content += "<div align=\"center\">\n\n"
        md_content += "| کشور | تعداد | لینک دانلود |\n"
        md_content += "|:----:|:-----:|:------------:|\n"
        if raw_country_counts:
            for country_category_name, count in sorted(raw_country_counts.items()):
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
                file_link = f"{raw_box_base_url}/{country_category_name}.txt"
                md_content += f"| {country_display_text} | {count} | [`{country_category_name}.txt`]({file_link}) |\n"
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

### 🗂️ کانفیگ‌های سالم پایدار
- **فایل `PersistentHealthy.txt`**: شامل تمام کانفیگ‌هایی است که در طول زمان تست شده و سالم تشخیص داده شده‌اند
- **پاک‌سازی خودکار**: {f'فقط در تغییرات عمده (GitHub Actions)' if GITHUB_ACTIONS else 'هر 10 روز'} این فایل پاک‌سازی می‌شود تا کیفیت حفظ شود
- **تجمع تدریجی**: با هر اجرای اسکریپت، کانفیگ‌های سالم جدید به این فایل اضافه می‌شوند
- **حفظ کانفیگ‌های قبلی**: کانفیگ‌های قبلی حفظ می‌شوند و کانفیگ‌های جدید به آن‌ها اضافه می‌شوند
- **مزایا**: تعداد زیادی کانفیگ سالم در طول زمان جمع‌آوری می‌شود که می‌تواند به عنوان منبع قابل اعتماد استفاده شود

---

## 🤝 مشارکت
اگر مایل به مشارکت در پروژه هستید، می‌توانید:
- منابع جدید برای جمع‌آوری کانفیگ‌ها پیشنهاد دهید (فایل `urls.txt`).
- الگوهای جدید برای پروتکل‌ها یا کشورها اضافه کنید (فایل `key.json`).
- با ارسال Pull Request یا Issue در [گیت‌هاب](https://github.com/{github_repo_path}) به بهبود پروژه کمک کنید.

---

## 📢 توجه
- این پروژه صرفاً برای اهداف آموزشی و تحقیقاتی ارائه شده است.
- لطفاً از کانفیگ‌ها به‌صورت مسئولانه و مطابق با قوانین کشور خود استفاده کنید.
- برای گزارش مشکلات یا پیشنهادات، از بخش [Issues](https://github.com/{github_repo_path}/issues) استفاده کنید.
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
    
    # Log persistent healthy system status
    if GITHUB_ACTIONS:
        github_status = get_github_actions_status()
        logging.info(f"Running in GitHub Actions environment (Commit: {github_status['commit_sha']}, Run: {github_status['run_id']})")
        if github_status['will_cleanup']:
            logging.info("Major change detected - will cleanup persistent healthy configs")
        else:
            logging.info("No major changes - preserving existing configs")
    
    if os.path.exists(PERSISTENT_HEALTHY_FILE):
        persistent_count = validate_persistent_healthy_file()
        logging.info(f"Found existing persistent healthy configs file with {persistent_count} configurations")
        
        if GITHUB_ACTIONS:
            if should_cleanup_persistent_healthy_github_actions():
                logging.info("GitHub Actions: Major change detected - will cleanup persistent healthy configs")
            else:
                logging.info("GitHub Actions: No major changes - preserving existing configs")
        else:
            if should_cleanup_persistent_healthy():
                next_cleanup = get_next_cleanup_date()
                days_until_cleanup = (next_cleanup - datetime.now()).days
                logging.info(f"Local: Persistent healthy configs cleanup scheduled in {days_until_cleanup} days")
            else:
                logging.info("Local: Persistent healthy configs cleanup not due yet")
    else:
        logging.info("No existing persistent healthy configs file found - will create new one")

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
                    if not DISABLE_CONFIG_FILTERS and should_filter_config(config):
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

    # Update persistent healthy configs with new healthy configurations
    if ENABLE_HEALTH_CHECK and healthy_union:
        logging.info("Updating persistent healthy configs with new healthy configurations...")
        merge_and_update_persistent_healthy(healthy_union)
        
        # Log persistent healthy status
        persistent_count = validate_persistent_healthy_file()
        if GITHUB_ACTIONS:
            logging.info(f"GitHub Actions: Persistent healthy configs file now contains {persistent_count} configurations")
        else:
            logging.info(f"Persistent healthy configs file now contains {persistent_count} configurations")
    else:
        if GITHUB_ACTIONS:
            logging.info("GitHub Actions: No new healthy configs to add to persistent storage")
        else:
            logging.info("No new healthy configs to add to persistent storage")

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_output_dir = os.path.join(OUTPUT_DIR, RAW_OUTPUT_SUBDIR)
    if os.path.exists(raw_output_dir):
        shutil.rmtree(raw_output_dir)
    os.makedirs(raw_output_dir, exist_ok=True)
    logging.info(f"Saving files to directory: {OUTPUT_DIR}")

    protocol_counts = {}
    country_counts = {}
    raw_protocol_counts = {}
    raw_country_counts = {}

    # Save raw protocol and country files (unfiltered)
    for category, items in final_all_protocols.items():
        saved, count = save_to_file(raw_output_dir, category, items)
        if saved:
            raw_protocol_counts[category] = count
    for category, items in final_configs_by_country.items():
        saved, count = save_to_file(raw_output_dir, category, items)
        if saved:
            raw_country_counts[category] = count

    # Save protocol files (filtered to healthy if health-check enabled). Keep untestable protocols if configured.
    for category, items in final_all_protocols.items():
        if not ENABLE_HEALTH_CHECK:
            items_to_save = items
        else:
            if category in healthy_by_protocol:
                items_to_save = healthy_by_protocol.get(category, set())
            else:
                items_to_save = items if KEEP_UNTESTED_ON_HEALTH else set()
        if ENABLE_HEALTH_CHECK and MAX_HEALTHY_PER_PROTOCOL:
            items_to_save = set(list(items_to_save)[:MAX_HEALTHY_PER_PROTOCOL])
        saved, count = save_to_file(OUTPUT_DIR, category, items_to_save)
        if saved:
            protocol_counts[category] = count
    # Save country files (filtered to healthy if health-check enabled)
    for category, items in final_configs_by_country.items():
        if ENABLE_HEALTH_CHECK:
            items = {x for x in items if (x in healthy_union) or (KEEP_UNTESTED_ON_HEALTH and not is_supported_link(x))}
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

    repo_path_env = os.getenv('GITHUB_REPOSITORY') or os.getenv('GITHUB_REPO') or os.getenv('REPO_PATH') or "Amirchelios/V2RayAutoConfig"
    branch_name_env = os.getenv('GITHUB_REF_NAME') or os.getenv('GITHUB_BRANCH') or "main"
    # Build unions for README "boxes"
    raw_union = set()
    for _p, _items in final_all_protocols.items():
        raw_union.update(_items)
    generate_simple_readme(
        protocol_counts,
        country_counts,
        categories_data,
        github_repo_path=repo_path_env,
        github_branch=branch_name_env,
        raw_protocol_counts=raw_protocol_counts,
        raw_country_counts=raw_country_counts
    )

    logging.info("--- Script Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
