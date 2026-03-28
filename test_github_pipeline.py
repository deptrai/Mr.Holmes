import asyncio
from Core.engine.scan_pipeline import ScanPipeline
import logging
logging.getLogger("mrholmes").setLevel(logging.DEBUG)

def run():
    pipeline = ScanPipeline("john", "Desktop", batch_mode=True, nsfw_enabled=False)
    pipeline.setup()
    pipeline.cfg = pipeline._build_config()
    
    # Force only GitHub in the site list
    original_configs = pipeline._load_site_configs()
    github_configs = [c for c in original_configs if c.name == "GitHub"]
    print(f"Loaded config: {github_configs[0].__dict__}")
    
    res = asyncio.run(pipeline.scan_all_sites(github_configs, "john", concurrency_limit=1))
    print(f"Final result list: {res}")
    for r in res:
        print(r.status, r.site_name, r.url)

if __name__ == "__main__":
    run()
