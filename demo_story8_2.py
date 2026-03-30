import asyncio
import os
import dotenv

from Core.engine.autonomous_agent import RecursiveProfiler
from Core.engine.llm_synthesizer import LLMSynthesizer
from Core.plugins.manager import PluginManager

DIVIDER = "=" * 70

async def main():
    dotenv.load_dotenv(".env")
    print(DIVIDER)
    print("🧠 DEMO: RECURSIVE PROFILER + LLM SYNTHESIS (Stories 8.1 + 8.2)")
    print(DIVIDER)
    
    # 1. Init plugins
    manager = PluginManager()
    manager.discover_plugins()
    plugins = manager.plugins
    
    # Inject API Keys (Since demo bypasses CLI config loading)
    for p in plugins:
        if p.name == "LeakLookup":
            p.api_key = os.environ.get("MH_LEAKLOOKUP_API_KEY", "")
        elif p.name == "HaveIBeenPwned":
            p.api_key = os.environ.get("MH_HAVEIBEENPWNED_API_KEY", "")
        elif p.name == "Shodan":
            p.api_key = os.environ.get("MH_SHODAN_API_KEY", "")
            
    print(f"[*] Đã tải {len(plugins)} Intelligence Plugins: {', '.join([p.name for p in plugins])}")
    
    target = "admin@facebook.com"
    target_type = "EMAIL"
    max_depth = 1
    
    print(f"[*] Mồi câu ban đầu (Seed): {target} ({target_type})")
    print(f"[*] Chiều sâu quét đệ quy (Max Depth): {max_depth}")
    print("\n⏳ [Phase 1/2] Đang chạy lõi đệ quy thu thập dữ liệu (Takes ~10-20s)...")
    
    # 2. Run ReconEngine
    agent = RecursiveProfiler(max_depth=max_depth)
    graph_dict = await agent.run_profiler(
        seed_target=target,
        seed_type=target_type,
        plugins=plugins
    )
    
    nodes_count = len(graph_dict.get('nodes', []))
    edges_count = len(graph_dict.get('edges', []))
    print(f"✅ Thu thập hoàn tất: {nodes_count} Entities, {edges_count} Relationships.")
    
    # 3. Run LLM Synthesizer
    print("\n⏳ [Phase 2/2] Đang chuyển dữ liệu nguyên thủy cho LLM (v98store) tổng hợp Báo Cáo...")
    
    synth = LLMSynthesizer() 
    # Notice synth reads env vars: MH_LLM_BASE_URL, MH_LLM_API_KEY, MH_LLM_MODEL
    
    result = await synth.synthesize(graph_dict)
    
    print("\n" + DIVIDER)
    print(f"📜 LLM OSINT ANALYST REPORT (Model: {result.model_used} | Success: {result.is_success})")
    if not result.is_success:
        print(f"Lỗi: {result.error_message}")
        
    print(DIVIDER)
    print(result.report_markdown)
    print(DIVIDER)
    
    print("DEMO HOÀN TẤT.")

if __name__ == "__main__":
    asyncio.run(main())
