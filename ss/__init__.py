"""
🔗 TrustLink Shadowsocks Tester Package

این پکیج شامل برنامه تست کانفیگ‌های Shadowsocks است که دقیقاً مثل VLESS و VMESS tester عمل می‌کند.
"""

__version__ = "1.0.0"
__author__ = "TrustLink Team"
__description__ = "Shadowsocks Tester - برنامه هوشمند برای تست و ذخیره کانفیگ‌های SS سالم"

from .ss_tester import SSManager, setup_logging

__all__ = ["SSManager", "setup_logging"]
