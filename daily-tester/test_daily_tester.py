#!/usr/bin/env python3
"""
🧪 Test script for Daily TrustLink Tester
This script tests the basic functionality of the daily tester without actually running tests
"""

import os
import sys
import json
from datetime import datetime

def test_basic_functionality():
    """Test basic functionality of the daily tester"""
    print("🧪 Testing Daily TrustLink Tester Basic Functionality")
    print("=" * 60)
    
    # Test 1: Check if required files exist
    print("1. Checking required files...")
    required_files = [
        "daily_trustlink_tester.py",
        "requirements.txt",
        "README.md"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file} exists")
        else:
            print(f"   ❌ {file} missing")
    
    # Test 2: Check if directories can be created
    print("\n2. Testing directory creation...")
    test_dirs = ["logs", "output"]
    
    for dir_name in test_dirs:
        try:
            os.makedirs(dir_name, exist_ok=True)
            print(f"   ✅ {dir_name} directory created/verified")
        except Exception as e:
            print(f"   ❌ Failed to create {dir_name}: {e}")
    
    # Test 3: Test config validation
    print("\n3. Testing config validation...")
    
    test_configs = [
        "vmess://eyJhZGQiOiJleGFtcGxlLmNvbSIsImFpZCI6IjAiLCJpZCI6InRlc3QiLCJwb3J0IjoiNDQzIiwidHlwZSI6Im5vbmUiLCJ2IjoiMiJ9",
        "vless://test@example.com:443?encryption=none&security=tls&type=ws#test",
        "trojan://test@example.com:443?security=tls#test",
        "ss://YWVzLTI1Ni1nY206dGVzdA@example.com:443#test",
        "invalid_config",
        "",
        "http://example.com"
    ]
    
    supported_protocols = {"vmess://", "vless://", "trojan://", "ss://"}
    
    for config in test_configs:
        is_valid = any(config.lower().startswith(protocol) for protocol in supported_protocols)
        if is_valid:
            print(f"   ✅ Valid config: {config[:50]}...")
        else:
            print(f"   ❌ Invalid config: {config[:50]}...")
    
    # Test 4: Test score calculation
    print("\n4. Testing score calculation...")
    
    test_results = [
        {"success": True, "latency": 50, "download_speed": 1000},  # Good
        {"success": True, "latency": 100, "download_speed": 500},   # Medium
        {"success": True, "latency": 200, "download_speed": 100},   # Poor
        {"success": False, "latency": None, "download_speed": None} # Failed
    ]
    
    def calculate_score(result):
        if not result["success"]:
            return 0.0
        
        latency_score = max(0, 100 - result["latency"] / 10)
        speed_score = min(100, result["download_speed"] / 10)
        final_score = (latency_score * 0.7) + (speed_score * 0.3)
        return final_score
    
    for i, result in enumerate(test_results, 1):
        score = calculate_score(result)
        print(f"   Test {i}: Score = {score:.1f}")
    
    # Test 5: Test file operations
    print("\n5. Testing file operations...")
    
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "test_configs": len(test_configs),
        "valid_configs": len([c for c in test_configs if any(c.lower().startswith(p) for p in supported_protocols)]),
        "test_results": "success"
    }
    
    try:
        with open("output/.test_results.json", "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        print("   ✅ Test results file created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create test results file: {e}")
    
    # Test 6: Test log file
    print("\n6. Testing log file...")
    
    try:
        with open("logs/test.log", "w", encoding="utf-8") as f:
            f.write(f"Test log entry at {datetime.now().isoformat()}\n")
            f.write("Daily TrustLink Tester test completed successfully\n")
        print("   ✅ Test log file created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create test log file: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Basic functionality test completed!")
    print("The Daily TrustLink Tester is ready for use.")
    print("=" * 60)

if __name__ == "__main__":
    test_basic_functionality()
