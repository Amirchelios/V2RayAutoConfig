"""
🔗 VMESS Tester Package

این پکیج شامل ابزارهای تست و مدیریت کانفیگ‌های VMESS است.

Modules:
    - vmess_tester: تستر اصلی کانفیگ‌های VMESS
    - run_vmess_tester_enhanced: اجراکننده پیشرفته

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "VMESS Tester Team"
__description__ = "تستر هوشمند کانفیگ‌های VMESS"

from .vmess_tester import VMESSManager, setup_logging

__all__ = ["VMESSManager", "setup_logging"]
