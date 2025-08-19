"""
🔗 TrustLink Trojan Tester Package

برنامه تست کانفیگ‌های Trojan مشابه VLESS/VMESS/SS.
"""

__version__ = "1.0.0"
__author__ = "TrustLink Team"
__description__ = "Trojan Tester - برنامه هوشمند برای تست و ذخیره کانفیگ‌های Trojan سالم"

from .trojan_tester import TrojanManager, setup_logging

__all__ = ["TrojanManager", "setup_logging"]
