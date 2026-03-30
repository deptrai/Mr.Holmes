import asyncio
from Core.engine.scan_pipeline import ScanPipeline
from Core.engine.async_search import SiteConfig
from Core.models import ErrorStrategy
import aiohttp
import logging
logging.getLogger("mrholmes").setLevel(logging.DEBUG)

class FakeOutput:
    def progress(self, cur, tot, msg=""): pass
    def found(self, *args, **kwargs): pass
    def summary(self, *args, **kwargs): pass
    def begin_progress(self, *args): pass
    def end_progress(self, *args): pass
    def error(self, *args): pass
    def not_found(self, *args): pass

async def main():
    pipeline = ScanPipeline("john", "Desktop", batch_mode=True, nsfw_enabled=False, output_handler=FakeOutput())
    pipeline.setup()

    original_configs = pipeline._load_site_configs('Site_lists/Username/site_list.json')
    github_configs = [c for c in original_configs if c.name == "GitHub"]
    print(f"Loaded config: {github_configs[0].__dict__}")
    
    res = await pipeline.scan_all_sites(github_configs, "john", concurrency_limit=1)
    print(f"Final result list: {res}")
    for r in res:
        print(r.status, r.site_name, r.url, r.error_message)

if __name__ == "__main__":
    asyncio.run(main())
