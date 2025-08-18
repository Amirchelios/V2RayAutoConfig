"""
🔗 VLESS Tester Package

این پکیج شامل تستر هوشمند برای کانفیگ‌های VLESS است.
"""

__version__ = "1.0.0"
__author__ = "TrustLink Team"
__description__ = "تستر هوشمند کانفیگ‌های VLESS با اجرای خودکار"

from .vless_tester import VLESSManager, run_vless_tester

__all__ = ["VLESSManager", "run_vless_tester"]
