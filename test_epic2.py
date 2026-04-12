import asyncio
import time
import json
import logging
from Core.engine.scan_pipeline import ScanPipeline
from Core.engine.async_search import SiteConfig
from Core.models import ScanStatus, ErrorStrategy

# Bật logging để xem retry/backoff rõ ràng
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("MrHolmes")

async def main():
    print("🚀 Bắt đầu test E2E Epic 2: Async Scanning Engine")
    
    # Load 50 sites từ file Username_sites.json
    try:
        with open("Site_lists/Username/site_list.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    sites = []
    # Lấy 50 sites đầu
    for site_name, site_data in list(data[0].items())[:50]:
        try:
            config = SiteConfig(
                name=site_name,
                url_template=site_data["user"],
                display_url=site_data["main"],
                error_strategy=ErrorStrategy(site_data["Error"]),
                error_text=site_data.get("text", "")
            )
            sites.append(config)
        except (KeyError, ValueError) as e:
            continue

    print(f"📦 Đã load {len(sites)} sites...")
    # Thêm 1 site giả để test ProxyDeadError hoặc Timeout/RateLimit nếu cần
    # Ở đây cứ scan username nonexistent để thấy NOT FOUND và ERROR
    test_user = "admin_test_123456789_epic2"
    print(f"⏳ Scanning username '{test_user}' với concurrency=10, chờ chút...")
    
    start_time = time.time()
    
    # Gọi trực tiếp scan_all_sites (đã handle gather + semaphore + retry)
    results = await ScanPipeline.scan_all_sites(
        site_configs=sites,
        username=test_user,
        proxy=None,
        concurrency_limit=10
    )
    
    duration = time.time() - start_time
    print(f"\n✅ Hoàn thành 50 sites trong {duration:.2f} giây! (Tốc độ cực nhanh nhờ asyncio.gather + semaphore)")
    
    # Thống kê
    found = [r for r in results if r.status == ScanStatus.FOUND]
    not_found = [r for r in results if r.status == ScanStatus.NOT_FOUND]
    errors = [r for r in results if r.status == ScanStatus.ERROR]
    
    print("\n📊 THỐNG KÊ KẾT QUẢ:")
    print(f"  [{len(found):>2}] FOUND")
    print(f"  [{len(not_found):>2}] NOT FOUND")
    print(f"  [{len(errors):>2}] ERRORS")
    
    if errors:
        print("\n⚠️ Một số lỗi gặp phải (demonstrating custom exceptions):")
        for r in errors[:5]:
            print(f"  - [{r.site_name}]: {r.error_message}")
            
    if found:
        print("\n🔍 Dù test nonexistent nhưng site nào đó lại FOUND (False Positive do site update):")
        for r in found[:3]:
            print(f"  - [{r.site_name}]: {r.url}")

if __name__ == "__main__":
    asyncio.run(main())
