import asyncio
import json
import os
import sys
import dotenv

from Core.engine.autonomous_agent import RecursiveProfiler
from Core.plugins.manager import PluginManager

DIVIDER = "=" * 70

async def main():
    dotenv.load_dotenv(".env")
    print(DIVIDER)
    print("🧠 DEMO: HOLMES RECURSIVE PROFILER ENGINE (Story 8.1)")
    print(DIVIDER)
    
    manager = PluginManager()
    manager.discover_plugins()
    plugins = manager.plugins
    
    print(f"[*] Đã tải {len(plugins)} Intelligence Plugins: {', '.join([p.name for p in plugins])}")
    
    # Inject API Keys
    for p in plugins:
        if p.name == "LeakLookup":
            p.api_key = os.environ.get("MH_LEAKLOOKUP_API_KEY", "")
        elif p.name == "HaveIBeenPwned":
            p.api_key = os.environ.get("MH_HAVEIBEENPWNED_API_KEY", "")
        elif p.name == "Shodan":
            p.api_key = os.environ.get("MH_SHODAN_API_KEY", "")
    
    target = "admin@facebook.com"
    target_type = "EMAIL"
    max_depth = 2
    
    print(f"[*] Mồi câu ban đầu (Seed): {target} ({target_type})")
    print(f"[*] Chiều sâu quét đệ quy (Max Depth): {max_depth}")
    print("\n⏳ Đang thả đặc vụ AI chạy ngầm. Quá trình này có thể tốn 10-30 giây để thu thập vòi rồng dữ liệu qua nhiều lớp...\n")
    
    agent = RecursiveProfiler(max_depth=max_depth)
    
    result = await agent.run_profiler(
        seed_target=target,
        seed_type=target_type,
        plugins=plugins
    )
    
    print(DIVIDER)
    print("✅ KẾT QUẢ ĐÃ TRẢ VỀ TỪ LÕI ĐỆ QUY")
    print(DIVIDER)
    
    nodes = result.get('nodes', [])
    edges = result.get('edges', [])
    plugin_results = result.get('plugin_results', [])
    
    print(f"📊 TỔNG KẾT ĐỒ THỊ (GRAPH):")
    print(f"  - Số Entities (Nodes) bị lộ diện : {len(nodes)}")
    print(f"  - Số mối liên hệ (Edges) móc nối: {len(edges)}")
    print(f"  - Tổng số queries đã bắn APIs    : {len(plugin_results)}")
    
    print("\n🔗 CÁC THỰC THỂ (NODES) ĐÃ TÓM ĐƯỢC:")
    for i, node in enumerate(nodes[:10]):
         print(f"  [{i+1}] Lớp (Depth) {node['depth']} | {node['target_type']}: {node['target']}")
    if len(nodes) > 10:
         print(f"  ... và {len(nodes) - 10} thực thể khác.")
         
    print("\n🔍 QUERIES THỰC TẾ (Chi tiết kết quả): ")
    for pr in plugin_results:
        print(f"  -> Plugin: {pr['plugin']} (Success: {pr['is_success']})")
        if not pr['is_success']:
            print(f"     Error: {pr['error']}")
        else:
            print(f"     Data Keys: {', '.join(pr['data'].keys())}")
            if "emails" in pr['data']:
                print(f"     Emails: {pr['data']['emails']}")
            if "hostnames" in pr['data']:
                print(f"     Hostnames: {pr['data']['hostnames']}")
            if "data_found" in pr['data']:
                print(f"     Data Found: {pr['data']['data_found']}")
         
    print("\n🖇️ CÁC SỢI DÂY LIÊN KẾT (EDGES) MỚI TÌM THẤY:")
    for i, edge in enumerate(edges[:10]):
         print(f"  [{i+1}] {edge['source']} --->(via {edge['via_plugin']})---> {edge['discovered']}")
    if len(edges) > 10:
         print(f"  ... và {len(edges) - 10} liên kết khác.")
         
    print(DIVIDER)
    print("DEMO HOÀN TẤT.")

if __name__ == "__main__":
    asyncio.run(main())
