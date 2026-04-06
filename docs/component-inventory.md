# Mr.Holmes — Component Inventory

Danh sách chi tiết tất cả components theo nhóm chức năng.

---

## 1. Intelligence Plugins (`Core/plugins/`)

| Plugin | File | EMAIL | USERNAME | IP | DOMAIN | PHONE | Cần API Key |
|--------|------|-------|----------|----|--------|-------|-------------|
| HaveIBeenPwned | `hibp.py` | Y | — | — | — | — | Y (`HIBP_API_KEY`) |
| Shodan | `shodan.py` | — | — | Y | Y | — | Y (`SHODAN_API_KEY`) |
| LeakLookup | `leak_lookup.py` | Y | Y | — | — | — | Y (`LEAK_LOOKUP_KEY`) |
| SearxNG | `searxng.py` | Y | Y | Y | Y | Y | Không |

**`base.py`** — Định nghĩa `IntelligencePlugin` Protocol và `PluginResult` dataclass.

**`manager.py`** — `PluginManager`: auto-discover, register, và run all plugins concurrently.

---

## 2. Engine Components (`Core/engine/`)

| Component | File | Chức năng |
|-----------|------|-----------|
| `RecursiveProfiler` | `autonomous_agent.py` | BFS clue discovery — đọc kết quả plugin, extract EMAIL/IP clues, queue sang layer tiếp theo |
| `LLMSynthesizer` | `llm_synthesizer.py` | Gọi OpenAI-compatible API, nhận báo cáo Markdown tiếng Việt. Hỗ trợ primary + fallback endpoint |
| `MindmapGenerator` | `mindmap_generator.py` | Chuyển `ProfileGraph` → standalone HTML với vis-network interactive graph |
| `ScanPipeline` | `scan_pipeline.py` | Orchestrate toàn bộ username scan session: proxy → async search → scraper dispatch → report write |
| `RetryPolicy` | `retry.py` | Exponential backoff + jitter cho `TargetSiteTimeout` và `RateLimitExceeded` |
| `ScanResultCollector` | `result_collector.py` | Thread-safe accumulator cho concurrent scan results — thay thế 5 shared mutable lists |
| `ApifyScraper` | `apify_scraper.py` | Instagram deep scrape qua Apify Actor API — bypass anti-bot protections |
| `AsyncSearchEngine` | `async_search.py` | `search_site()` async function — một HTTP check cho một site config |

---

## 3. Platform Scrapers — Deep Profile (`Core/Support/Username/`)

Các scraper chạy sau khi async search tìm thấy profile. Lấy thêm thông tin: bio, follower count, profile pic, posts.

| Scraper | Platform | Phương thức | Trạng thái |
|---------|----------|-------------|------------|
| Instagram | instagram.com | Apify API / JSON endpoint | Hoạt động |
| Twitter | twitter.com | BeautifulSoup | Hoạt động |
| TikTok | tiktok.com | JSON API | Hoạt động |
| GitHub | github.com | JSON API (`api.github.com`) | Hoạt động |
| GitLab | gitlab.com | JSON API | Hoạt động |
| DockerHub | hub.docker.com | JSON API | Hoạt động |
| Imgur | imgur.com | BeautifulSoup | Hoạt động |
| Kik | kik.me | BeautifulSoup | Hoạt động |
| Wattpad | wattpad.com | BeautifulSoup | Hoạt động |
| MixCloud | mixcloud.com | JSON API | Hoạt động |
| Twitch | twitch.tv | BeautifulSoup | Hoạt động |
| Reddit | reddit.com | JSON API | Hoạt động |
| Steam | steamcommunity.com | BeautifulSoup | Hoạt động |
| PyPI | pypi.org | JSON API | Hoạt động |
| Vimeo | vimeo.com | BeautifulSoup | Hoạt động |
| Flickr | flickr.com | BeautifulSoup | Hoạt động |
| SoundCloud | soundcloud.com | BeautifulSoup | Hoạt động |
| DeviantArt | deviantart.com | BeautifulSoup | Hoạt động |
| Patreon | patreon.com | BeautifulSoup | Hoạt động |

`ScraperRegistry` (`Core/scrapers/registry.py`) dispatch tất cả scrapers này theo tên site — thêm scraper mới chỉ cần 1 lệnh `register()`.

---

## 4. CLI Components (`Core/cli/`)

| Component | File | Chức năng |
|-----------|------|-----------|
| `parse_args()` | `parser.py` | Argument parser: `--username`, `--email`, `--phone`, `--export`, `--config`, `--investigation` |
| `BatchRunner` | `runner.py` | Chạy scan không cần interactive khi có batch flags |
| `OutputHandler` | `output.py` | Abstraction layer cho output — cho phép test without printing |
| `invoke_api_key_wizard()` | `config_wizard.py` | Interactive wizard nhập và lưu API keys vào `.env` |
| `RichOutput` | `rich_output.py` | Progress display với `rich` library: spinners, tables, colored output |

---

## 5. Reporting Components (`Core/reporting/`)

| Component | File | Chức năng |
|-----------|------|-----------|
| `Database` | `database.py` | Thread-safe SQLite singleton. Schema migration qua `schema.sql` |
| `ReportWriter` | `writer.py` | Dual-write: flat files (`.txt`/`.json`) + SQLite. SQLite failure không block flat files |
| `PdfExporter` | `pdf_export.py` | Jinja2 template → weasyprint/pdfkit → PDF. Template nằm trong `templates/` |
| `CsvExporter` | `csv_export.py` | Export investigation findings sang CSV |

Schema SQL: `Core/reporting/schema.sql`. PDF templates: `Core/reporting/templates/`.

---

## 6. Data Models (`Core/models/`)

| Model | File | Mô tả |
|-------|------|-------|
| `ScanContext` / `ScanConfig` | `scan_context.py` | Input data cho một scan session: username, mode, proxy config, output path |
| `ScanResult` / `ScanStatus` | `scan_result.py` | Kết quả một site check: status (FOUND/NOT_FOUND/ERROR), URL, name, tags |
| `sanitize_username()` | `validators.py` | Input validation: sanitize và validate username string |
| Exception classes | `exceptions.py` | `OSINTError`, `TargetSiteTimeout`, `RateLimitExceeded`, `ProxyDeadError`, `SiteCheckError` |

---

## 7. Proxy System (`Core/proxy/`)

`ProxyManager` (`manager.py`) — tập trung toàn bộ proxy lifecycle:

| Method | Mục đích |
|--------|----------|
| `configure(choice)` | Enable/disable proxy, resolve identity qua `ip-api.com` |
| `get_proxy()` | Trả về `{http, https}` dict hoặc `None` |
| `load_proxy_pool(path)` | Load danh sách proxy từ file |
| `rotate()` | Lấy proxy tiếp theo (strategy: round-robin hoặc random) |
| `mark_dead(url)` | Loại proxy khỏi pool |
| `health_check_pool()` | Kiểm tra toàn bộ pool → `HealthReport(total, healthy, dead, dead_urls)` |
| `reset()` | Disable proxy hoàn toàn |

---

## 8. Configuration (`Core/config/`)

| Component | File | Chức năng |
|-----------|------|-----------|
| `Settings` singleton | `settings.py` | Đọc `.env` (secrets) + `Configuration.ini` (non-secrets). Properties: `smtp_*`, `api_key`, `language`, `database_enabled`, v.v. |
| `get_plugin_key()` | `settings.py` | Lấy API key theo tên plugin (e.g., `settings.get_plugin_key("HIBP")`) |
| `get_logger()` | `logging_config.py` | Centralized logger factory |

---

## 9. Legacy OSINT Modules (`Core/`)

| Module | File | Chức năng |
|--------|------|-----------|
| Username Searcher | `Searcher.py` | Entry point cho username scan — khởi tạo `ScanPipeline` |
| Website Searcher | `Searcher_website.py` | Domain reconnaissance: WHOIS, subdomain, portscan |
| Phone Searcher | `Searcher_phone.py` | OSINT phone: carrier, region, reverse lookup |
| Person Searcher | `Searcher_person.py` | Person profiling |
| Email Module | `E_Mail.py` | Email verification, breach lookup, dork generation |
| Dork Generator | `Dork.py` | Google/Yandex dork orchestration |
| Port Scanner | `Port_Scanner.py` | Active port scanning |
| PDF Converter | `PDF_Converter.py` | Legacy PDF conversion |
| Decoder | `Decoder.py` | Encoding/decoding utilities |
