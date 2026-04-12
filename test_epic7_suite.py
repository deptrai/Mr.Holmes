import asyncio
import os
import sys
import dotenv
from Core.plugins.manager import PluginManager

DIVIDER = "=" * 70

async def run_live_test(target: str, target_type: str):
    print(f"\n{DIVIDER}")
    print(f"🎯 ĐANG KIỂM TRA MỤC TIÊU: {target} ({target_type})")
    print(f"{DIVIDER}")
    
    manager = PluginManager()
    manager.discover_plugins()
    available_plugins = [p for p in manager.plugins if target_type in p.SUPPORTED_TYPES or not p.SUPPORTED_TYPES]
    
    if not available_plugins:
        print(f"[!] Không có plugin nào hỗ trợ kiểm tra loại '{target_type}'.")
        return

    print(f"[*] Đã tìm thấy {len(available_plugins)} Plugin hỗ trợ: {', '.join([p.name for p in available_plugins])}")
    
    for plugin in available_plugins:
        print(f"\n▶ Đang chạy: [ {plugin.name} ]")
        if plugin.requires_api_key and not plugin.api_key:
            print(f"  [X] Lỗi: Yêu cầu API Key nhưng chưa được thiết lập trong .env")
            continue
            
        print(f"  [*] Đang truy vấn dữ liệu từ {plugin.name}...")
        result = await plugin.check(target, target_type)
        
        if result.is_success:
            print(f"  [+] THÀNH CÔNG!")
            if result.data.get('data_found'):
                print(f"      - Cảm biến báo hiệu: ĐÃ TÌM THẤY DẤU VẾT!")
                if 'total_breaches' in result.data.get('metadata', {}):
                     print(f"      - Số vụ rò rỉ (Breaches): {result.data['metadata']['total_breaches']}")
                if 'vulnerabilities' in result.data:
                    print(f"      - Chi tiết nguồn rò rỉ lộ diện (Top 5): {result.data['vulnerabilities'][:5]}")
                if 'osint_urls' in result.data:
                    print(f"      - URL tìm kiếm (Top 3): {result.data['osint_urls'][:3]}")
                if 'ports' in result.data:
                     print(f"      - Cổng mở (Open Ports): {result.data['ports']}")
                     print(f"      - Hệ điều hành (OS): {result.data.get('os', 'Unknown')}")
            else:
                 print(f"      - Không tìm thấy dữ liệu nào (Sạch).")
        else:
            print(f"  [-] LỖI API/MẠNG: {result.error_message}")

async def main():
    dotenv.load_dotenv(".env")
    print(DIVIDER)
    print("🚀 MR.HOLMES - EPIC 7 PLUGINS SUITE LIVE TEST 🚀")
    print(DIVIDER)
    
    # Check current registered Keys
    print("[*] API Keys đang có trong file .env:")
    keys_to_check = ['MH_HIBP_API_KEY', 'MH_SHODAN_API_KEY', 'MH_LEAKLOOKUP_API_KEY']
    for key in keys_to_check:
        val = os.environ.get(key, "").strip("'\"")
        status = "🟢 CÓ SẴN (" + val[:4] + "...)" if val else "🔴 TRỐNG"
        print(f"    - {key}: {status}")
    print("\nLưu ý: Bạn có thể cập nhật các Key này bằng tính năng Quản lý API Key (Wizard)")
    print("hoặc sửa trực tiếp file .env\n")
    
    # Test 1: Email (Will trigger HIBP, Leak-Lookup, SearxNG)
    await run_live_test("admin@facebook.com", "EMAIL")
    
    # Test 2: IP (Will trigger Shodan, SearxNG)
    await run_live_test("1.1.1.1", "IP")
    
    print(f"\n{DIVIDER}")
    print("🎉 KIỂM TRA TOÀN DIỆN KẾT THÚC.")

if __name__ == "__main__":
    asyncio.run(main())
