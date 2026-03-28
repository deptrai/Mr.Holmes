import asyncio
import aiohttp
from Core.engine.async_search import search_site, SiteConfig
from Core.models import ErrorStrategy

async def main():
    config = SiteConfig(
        name="GitHub",
        url_template="https://github.com/{}",
        display_url="https://github.com/john",
        error_strategy=ErrorStrategy.STATUS_CODE,
        error_text="",
        response_url="",
        tags=[],
        is_scrapable=True
    )
    async with aiohttp.ClientSession() as session:
        res = await search_site(session, config, "john")
        print(f"Status: {res.status}")
        print(f"Error: {res.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
