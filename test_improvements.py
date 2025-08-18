#!/usr/bin/env python3
"""
🧪 Test Script for V2Ray AutoConfig Improvements
این اسکریپت تمام بهبودهای اعمال شده را تست می‌کند
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

def test_file_structure():
    """تست ساختار فایل‌ها"""
    print("🔍 Testing file structure...")
    
    required_files = [
        "vless/vless_tester.py",
        "vless/run_vless_tester_enhanced.py", 
        "scripts/fix_git_push.sh",
        ".github/workflows/scraper.yml",
        "V2RAY_IMPROVEMENTS.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_vless_tester_imports():
    """تست import های VLESS tester"""
    print("🔍 Testing VLESS tester imports...")
    
    try:
        sys.path.append('vless')
        from vless_tester import VLESSManager, setup_logging
        print("✅ VLESS tester imports successful")
        return True
    except Exception as e:
        print(f"❌ VLESS tester import failed: {e}")
        return False

def test_enhanced_tester_imports():
    """تست import های Enhanced tester"""
    print("🔍 Testing Enhanced tester imports...")
    
    try:
        sys.path.append('vless')
        from run_vless_tester_enhanced import run_enhanced_vless_tester
        print("✅ Enhanced tester imports successful")
        return True
    except Exception as e:
        print(f"❌ Enhanced tester import failed: {e}")
        return False

def test_config_values():
    """تست مقادیر تنظیمات"""
    print("🔍 Testing configuration values...")
    
    try:
        sys.path.append('vless')
        from vless_tester import CONCURRENT_TESTS, KEEP_BEST_COUNT, MAX_CONFIGS_TO_TEST
        
        # تست مقادیر جدید
        if CONCURRENT_TESTS >= 50:
            print(f"✅ CONCURRENT_TESTS: {CONCURRENT_TESTS}")
        else:
            print(f"❌ CONCURRENT_TESTS too low: {CONCURRENT_TESTS}")
            return False
            
        if KEEP_BEST_COUNT >= 500:
            print(f"✅ KEEP_BEST_COUNT: {KEEP_BEST_COUNT}")
        else:
            print(f"❌ KEEP_BEST_COUNT too low: {KEEP_BEST_COUNT}")
            return False
            
        if MAX_CONFIGS_TO_TEST >= 10000:
            print(f"✅ MAX_CONFIGS_TO_TEST: {MAX_CONFIGS_TO_TEST}")
        else:
            print(f"❌ MAX_CONFIGS_TO_TEST too low: {MAX_CONFIGS_TO_TEST}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_workflow_file():
    """تست فایل workflow"""
    print("🔍 Testing workflow file...")
    
    try:
        with open('.github/workflows/scraper.yml', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # تست وجود مراحل جدید
        if 'Enhanced VLESS tester' in content:
            print("✅ Enhanced VLESS tester step found")
        else:
            print("❌ Enhanced VLESS tester step not found")
            return False
            
        if 'fix_git_push.sh' in content:
            print("✅ Git fix script step found")
        else:
            print("❌ Git fix script step not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False

def test_git_script():
    """تست اسکریپت Git"""
    print("🔍 Testing Git fix script...")
    
    try:
        with open('scripts/fix_git_push.sh', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # تست وجود استراتژی‌های مختلف
        if 'rebase' in content and 'merge' in content:
            print("✅ Git strategies found")
        else:
            print("❌ Git strategies not found")
            return False
            
        if 'force-with-lease' in content:
            print("✅ Force push strategy found")
        else:
            print("❌ Force push strategy not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Git script test failed: {e}")
        return False

async def test_vless_functionality():
    """تست عملکرد VLESS tester"""
    print("🔍 Testing VLESS functionality...")
    
    try:
        sys.path.append('vless')
        from vless_tester import VLESSManager
        
        manager = VLESSManager()
        
        # تست بارگذاری متادیتا
        if hasattr(manager, 'metadata'):
            print("✅ Metadata loading successful")
        else:
            print("❌ Metadata loading failed")
            return False
            
        # تست بارگذاری کانفیگ‌ها
        configs = manager.load_vless_source_configs()
        print(f"✅ Loaded {len(configs)} configs")
        
        # تست validation
        if manager.is_valid_vless_config("vless://test@example.com:443?type=tcp&security=tls"):
            print("✅ VLESS validation working")
        else:
            print("❌ VLESS validation failed")
            return False
            
        await manager.close_session()
        return True
        
    except Exception as e:
        print(f"❌ VLESS functionality test failed: {e}")
        return False

def main():
    """تابع اصلی تست"""
    print("🧪 V2Ray AutoConfig Improvements Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("VLESS Tester Imports", test_vless_tester_imports),
        ("Enhanced Tester Imports", test_enhanced_tester_imports),
        ("Configuration Values", test_config_values),
        ("Workflow File", test_workflow_file),
        ("Git Script", test_git_script),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    # تست async
    print(f"\n📋 Running: VLESS Functionality")
    try:
        if asyncio.run(test_vless_functionality()):
            passed += 1
            print(f"✅ VLESS Functionality: PASSED")
        else:
            print(f"❌ VLESS Functionality: FAILED")
    except Exception as e:
        print(f"❌ VLESS Functionality: ERROR - {e}")
    
    total += 1
    
    # نتیجه نهایی
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Improvements are working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
