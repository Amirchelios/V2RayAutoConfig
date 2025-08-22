#!/usr/bin/env python3
"""
🧪 تست عملکرد جدید 4-ping requirement
این اسکریپت عملکرد جدید ping checking را تست می‌کند
"""

import asyncio
import aiohttp
import logging
from typing import Dict

# تنظیمات check-host.net API
CHECK_HOST_API_BASE = "https://check-host.net"
CHECK_HOST_PING_ENDPOINT = "/check-ping"
CHECK_HOST_RESULT_ENDPOINT = "/check-result"

# تنظیمات logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_4ping_requirement():
    """تست عملکرد جدید 4-ping requirement"""
    
    async with aiohttp.ClientSession() as session:
        # تست IP های مختلف
        test_ips = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
        
        for ip in test_ips:
            logging.info(f"🧪 تست IP: {ip}")
            
            try:
                # ارسال 4 درخواست ping
                ping_params = {
                    'host': ip,
                    'node': 'ir2.node.check-host.net',
                    'count': '4'  # ارسال 4 درخواست ping
                }
                
                headers = {'Accept': 'application/json'}
                
                logging.info(f"🌐 ارسال 4 درخواست ping برای {ip}")
                
                async with session.post(
                    f"{CHECK_HOST_API_BASE}{CHECK_HOST_PING_ENDPOINT}",
                    params=ping_params,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        logging.error(f"❌ خطا در درخواست ping: HTTP {response.status}")
                        continue
                    
                    ping_data = await response.json()
                    
                    if not ping_data.get('ok'):
                        logging.error(f"❌ خطا در پاسخ ping API: {ping_data}")
                        continue
                    
                    request_id = ping_data.get('request_id')
                    logging.info(f"✅ درخواست ping ارسال شد - Request ID: {request_id}")
                    
                    # انتظار برای نتایج
                    await asyncio.sleep(10)
                    
                    # بررسی نتایج
                    try:
                        async with session.get(
                            f"{CHECK_HOST_API_BASE}{CHECK_HOST_RESULT_ENDPOINT}/{request_id}",
                            headers=headers,
                            timeout=10
                        ) as result_response:
                            if result_response.status == 200:
                                result_data = await result_response.json()
                                
                                # تحلیل نتایج با روش جدید
                                ping_success = analyze_ping_results_4_required(result_data, ip)
                                
                                if ping_success:
                                    logging.info(f"✅ IP {ip}: همه 4 ping موفق (4/4)")
                                else:
                                    logging.info(f"❌ IP {ip}: حداقل یکی از 4 ping ناموفق")
                            else:
                                logging.error(f"❌ خطا در دریافت نتایج: HTTP {result_response.status}")
                                
                    except Exception as e:
                        logging.error(f"❌ خطا در بررسی نتایج: {e}")
                        
            except Exception as e:
                logging.error(f"❌ خطا در تست {ip}: {e}")
            
            # کمی صبر بین تست‌ها
            await asyncio.sleep(2)

def analyze_ping_results_4_required(result_data: Dict, server_ip: str) -> bool:
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
        
        logging.info(f"📊 IP {server_ip}: {ping_success_count}/4 ping موفق, کل: {total_ping_count}, traceroute: {traceroute_exists}")
        
        if is_healthy:
            logging.info(f"✅ IP {server_ip}: همه 4 ping موفق (4/4), بدون traceroute")
        else:
            if ping_success_count < 4:
                logging.info(f"❌ IP {server_ip}: فقط {ping_success_count}/4 ping موفق")
            if traceroute_exists:
                logging.info(f"❌ IP {server_ip}: traceroute موجود")
            if total_ping_count < 4:
                logging.info(f"❌ IP {server_ip}: تعداد کل ping کمتر از 4 ({total_ping_count})")
        
        return is_healthy
        
    except Exception as e:
        logging.error(f"❌ خطا در تحلیل نتایج ping برای {server_ip}: {e}")
        return False

async def main():
    """تابع اصلی"""
    logging.info("🚀 شروع تست عملکرد جدید 4-ping requirement")
    logging.info("=" * 60)
    
    await test_4ping_requirement()
    
    logging.info("=" * 60)
    logging.info("✅ تست کامل شد")

if __name__ == "__main__":
    asyncio.run(main())
