#!/usr/bin/env python3
"""
🧪 تست ساده برای عملکرد ping check با check-host.net API
"""

import asyncio
import aiohttp
import logging

# تنظیمات logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# تنظیمات check-host.net API
CHECK_HOST_API_BASE = "https://check-host.net"
CHECK_HOST_PING_ENDPOINT = "/check-ping"
CHECK_HOST_RESULT_ENDPOINT = "/check-result"

async def test_ping_single_ip(ip: str):
    """تست ping برای یک IP واحد"""
    try:
        async with aiohttp.ClientSession() as session:
            # ارسال درخواست ping - فقط از نود ایران مشهد
            ping_params = {
                'host': ip,
                'node': 'ir2.node.check-host.net'
            }
            
            headers = {'Accept': 'application/json'}
            
            logging.info(f"🌐 ارسال درخواست ping برای IP: {ip}")
            
            async with session.post(
                f"{CHECK_HOST_API_BASE}{CHECK_HOST_PING_ENDPOINT}",
                params=ping_params,
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    logging.error(f"خطا در درخواست ping: HTTP {response.status}")
                    return False
                
                ping_data = await response.json()
                
                if not ping_data.get('ok'):
                    logging.error(f"خطا در پاسخ ping API: {ping_data}")
                    return False
                
                request_id = ping_data.get('request_id')
                nodes = ping_data.get('nodes', {})
                
                logging.info(f"✅ درخواست ping ارسال شد - Request ID: {request_id}")
                logging.info(f"🌍 نودهای تست: {list(nodes.keys())}")
                
                # انتظار برای نتایج (حداکثر 30 ثانیه)
                max_wait_time = 30
                wait_interval = 2
                waited_time = 0
                
                while waited_time < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    waited_time += wait_interval
                    
                    # بررسی نتایج
                    try:
                        async with session.get(
                            f"{CHECK_HOST_API_BASE}{CHECK_HOST_RESULT_ENDPOINT}/{request_id}",
                            headers=headers,
                            timeout=10
                        ) as result_response:
                            if result_response.status != 200:
                                continue
                            
                            result_data = await result_response.json()
                            
                            # بررسی اینکه آیا همه نتایج آماده هستند
                            all_ready = True
                            for node_name, node_result in result_data.items():
                                if node_result is None:
                                    all_ready = False
                                    break
                            
                            if all_ready:
                                logging.info(f"✅ نتایج ping آماده شدند - زمان انتظار: {waited_time} ثانیه")
                                break
                            
                    except Exception as e:
                        logging.debug(f"خطا در بررسی نتایج ping: {e}")
                        continue
                
                # پردازش نتایج نهایی
                try:
                    async with session.get(
                        f"{CHECK_HOST_API_BASE}{CHECK_HOST_RESULT_ENDPOINT}/{request_id}",
                        headers=headers,
                        timeout=10
                    ) as final_response:
                        if final_response.status == 200:
                            final_data = await final_response.json()
                            
                            # تحلیل نتایج
                            ping_success = analyze_ping_results(final_data, ip)
                            
                            if ping_success:
                                logging.info(f"✅ IP {ip}: Ping موفق")
                            else:
                                logging.info(f"❌ IP {ip}: Ping ناموفق")
                            
                            return ping_success
                        else:
                            logging.error(f"خطا در دریافت نتایج نهایی ping: HTTP {final_response.status}")
                            return False
                            
                except Exception as e:
                    logging.error(f"خطا در پردازش نتایج نهایی ping: {e}")
                    return False
                
    except Exception as e:
        logging.error(f"خطا در تست ping: {e}")
        return False

def analyze_ping_results(result_data: dict, server_ip: str) -> bool:
    """
    تحلیل نتایج ping برای یک IP خاص
    سرور سالم در نظر گرفته می‌شود اگر:
    1. حداقل یک نود ping موفق داشته باشد
    2. هیچ نودی traceroute نداشته باشد (null یا empty)
    """
    try:
        ping_success_count = 0
        traceroute_exists = False
        
        logging.info(f"🔍 تحلیل نتایج برای {server_ip}: {result_data}")
        
        for node_name, node_result in result_data.items():
            if node_result is None:
                logging.info(f"  نود {node_name}: null")
                continue
            
            logging.info(f"  نود {node_name}: {node_result}")
            
            # بررسی ping results
            if isinstance(node_result, list) and len(node_result) > 0:
                for ping_result in node_result:
                    if isinstance(ping_result, list) and len(ping_result) > 0:
                        # هر ping_result یک لیست از نتایج ping است
                        for individual_ping in ping_result:
                            if isinstance(individual_ping, list) and len(individual_ping) >= 2:
                                status = individual_ping[0]
                                logging.info(f"    Individual ping: {individual_ping}")
                                if status == "OK":
                                    ping_success_count += 1
                                    logging.info(f"    ✅ Ping موفق شمارش شد")
                                else:
                                    logging.info(f"    ❌ Ping ناموفق: {status}")
            
            # بررسی traceroute (اگر وجود داشته باشد)
            if isinstance(node_result, dict) and 'traceroute' in node_result:
                traceroute_data = node_result['traceroute']
                if traceroute_data and len(traceroute_data) > 0:
                    traceroute_exists = True
                    logging.info(f"    Traceroute found: {traceroute_data}")
        
        # سرور سالم: ping موفق + بدون traceroute
        is_healthy = ping_success_count > 0 and not traceroute_exists
        
        if is_healthy:
            logging.info(f"✅ IP {server_ip}: Ping موفق ({ping_success_count} نود), بدون traceroute")
        else:
            if ping_success_count == 0:
                logging.info(f"❌ IP {server_ip}: هیچ ping موفقی")
            if traceroute_exists:
                logging.info(f"❌ IP {server_ip}: traceroute موجود")
        
        return is_healthy
        
    except Exception as e:
        logging.error(f"خطا در تحلیل نتایج ping برای {server_ip}: {e}")
        return False

async def test_ping_batch(server_ips: list):
    """تست ping برای batch از IP ها"""
    logging.info(f"🌐 شروع تست ping برای {len(server_ips)} IP")
    
    results = {}
    
    for i, ip in enumerate(server_ips, 1):
        logging.info(f"📦 تست IP {i}/{len(server_ips)}: {ip}")
        
        try:
            success = await test_ping_single_ip(ip)
            results[ip] = success
            
            # کمی صبر بین تست‌ها
            if i < len(server_ips):
                await asyncio.sleep(1)
                
        except Exception as e:
            logging.error(f"خطا در تست IP {ip}: {e}")
            results[ip] = False
    
    # خلاصه نتایج
    successful_ips = [ip for ip, success in results.items() if success]
    failed_ips = [ip for ip, success in results.items() if not success]
    
    logging.info(f"✅ تست ping کامل شد:")
    logging.info(f"  - موفق: {len(successful_ips)} IP")
    logging.info(f"  - ناموفق: {len(failed_ips)} IP")
    
    if successful_ips:
        logging.info(f"  - IP های موفق: {', '.join(successful_ips)}")
    
    return results

async def main():
    """تابع اصلی"""
    # تست با چند IP نمونه
    test_ips = [
        "8.8.8.8",      # Google DNS
        "1.1.1.1",      # Cloudflare DNS
        "208.67.222.222" # OpenDNS
    ]
    
    logging.info("🚀 شروع تست ping check با check-host.net API")
    logging.info("=" * 60)
    
    try:
        results = await test_ping_batch(test_ips)
        
        logging.info("=" * 60)
        logging.info("📊 خلاصه نتایج:")
        for ip, success in results.items():
            status = "✅ موفق" if success else "❌ ناموفق"
            logging.info(f"  {ip}: {status}")
            
    except Exception as e:
        logging.error(f"خطا در اجرای تست: {e}")

if __name__ == "__main__":
    asyncio.run(main())
