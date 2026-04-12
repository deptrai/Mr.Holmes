# Mr.Holmes — Kiến trúc hệ thống

## Entry Points

### `MrHolmes.py` — Interactive + Batch CLI
File entry point chính. Khởi động theo hai chế độ:

- **Interactive mode**: Hiển thị menu (option 1–16), người dùng chọn loại scan
- **Batch mode**: Nhận flags CLI (`--username`, `--email`, `--phone`, `--export pdf`, `--config api-keys`) để chạy không cần tương tác

```bash
# Interactive
python3 MrHolmes.py

# Batch — scan username và export CSV
python3 MrHolmes.py --username johndoe --export csv --investigation 1
```

### `Core/autonomous_cli.py` — Option 16: Autonomous Profiler
Entry point cho Autonomous Profiler được gọi từ menu dispatcher. Thực hiện tuần tự:
1. Nhận `Target`, `Type`, `Max Depth` từ user
2. Gọi `RecursiveProfiler` (BFS discovery)
3. Gọi `MindmapGenerator` (HTML export)
4. Gọi `LLMSynthesizer` (AI report)
5. Lưu artifacts vào `GUI/Reports/Autonomous/<target>/`

---

## Core Engine

### `ScanPipeline` — `Core/engine/scan_pipeline.py`
Thay thế God Method `MrHolmes.search()` (500 LOC) thành các pipeline stage riêng biệt. Chịu trách nhiệm scan username trên 150+ site.

```
ScanPipeline.run()
    └── _resolve_proxy_identity()
    └── asyncio.gather() + Semaphore(SEMAPHORE_LIMIT)
        └── async_search.search_site() × N sites
    └── ScanResultCollector.add_many()
    └── ScraperRegistry.dispatch()    — deep scrapers cho matched sites
    └── ReportWriter.write()          — dual-write flat + SQLite
```

Giới hạn concurrency configurable qua biến môi trường `MR_HOLMES_CONCURRENCY` (default: 20).

### `RecursiveProfiler` — `Core/engine/autonomous_agent.py`
BFS engine khám phá clue mới từ kết quả plugin. Mỗi "layer" là một tập target được scan bởi tất cả plugin đã đăng ký.

```
RecursiveProfiler.run_profiler(seed_target, seed_type, max_depth)
    Layer 0: scan seed target với tất cả plugins
    Layer 1: extract EMAIL/IP clues từ kết quả layer 0 → scan tiếp
    Layer N: tiếp tục đến max_depth hoặc không còn clue mới
    Return: ProfileGraph(nodes, edges, plugin_results)
```

Regex patterns dùng để extract clues: `_EMAIL_RE`, `_IP_RE` từ raw plugin output.

### `LLMSynthesizer` — `Core/engine/llm_synthesizer.py`
Gửi `ProfileGraph` serialized JSON đến OpenAI-compatible API và nhận báo cáo Markdown tiếng Việt. Hỗ trợ primary + fallback endpoint.

```python
result: SynthesisResult = await synthesizer.synthesize(graph_dict)
# result.report_markdown — báo cáo Markdown
# result.model_used      — model đã dùng
# result.is_success      — thành công hay không
```

Báo cáo gồm 4 section bắt buộc: Tóm tắt điều hành, Các thực thể được phát hiện, Mối quan hệ quan trọng, Đánh giá rủi ro.

### `MindmapGenerator` — `Core/engine/mindmap_generator.py`
Chuyển `ProfileGraph` dict thành file HTML standalone chứa vis-network interactive graph.

- Nodes có màu theo `target_type` (EMAIL=đỏ, IP=xanh dương, DOMAIN=xanh lá, v.v.)
- Node depth 0 (seed) có màu crimson nổi bật
- Edges được label bằng tên plugin đã discover relationship
- HTML fully self-contained — embed data inline, không cần server

---

## Plugin System

### `IntelligencePlugin` Protocol — `Core/plugins/base.py`
Giao tiếp chuẩn bắt buộc cho mọi external OSINT plugin:

```python
class IntelligencePlugin(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def requires_api_key(self) -> bool: ...
    async def check(self, target: str, target_type: str) -> PluginResult: ...
```

Bất kỳ class nào implement đủ 3 attribute này đều được `PluginManager` nhận diện tự động (duck-typing, không cần kế thừa).

### `PluginManager` — `Core/plugins/manager.py`
Auto-discover tất cả plugin classes trong package `Core.plugins` khi gọi `discover_plugins()`. Chạy tất cả plugin concurrently:

```python
manager = PluginManager()
manager.discover_plugins()
results: list[PluginResult] = await manager.run_all(target, target_type)
```

### 4 Intelligence Plugins

| Plugin | File | Supported Types | API Key |
|--------|------|----------------|---------|
| HaveIBeenPwned | `hibp.py` | EMAIL | Có (`HIBP_API_KEY`) |
| Shodan | `shodan.py` | IP, DOMAIN | Có (`SHODAN_API_KEY`) |
| LeakLookup | `leak_lookup.py` | EMAIL, USERNAME | Có (`LEAK_LOOKUP_KEY`) |
| SearxNG | `searxng.py` | EMAIL, USERNAME, IP, DOMAIN, PHONE | Không |

---

## Data Flow

```
Input (target + type)
        │
        ▼
   PluginManager.run_all()
   [HIBP, Shodan, LeakLookup, SearxNG] — asyncio.gather()
        │
        ▼
   Clue Extraction (regex: EMAIL, IP)
        │
        ▼
   BFS Queue → next layer targets
        │
        ▼
   ProfileGraph(nodes, edges, plugin_results)
        │
        ├──→ MindmapGenerator → output_mindmap.html
        └──→ LLMSynthesizer → report.md
                │
                └──→ ReportWriter → flat files + SQLite
```

---

## Reporting Layer

### Dual-Write Strategy
`ReportWriter` ghi song song hai đích:
- **Flat files** (`.txt` + `.json`): backward compatibility với PHP GUI
- **SQLite** (`GUI/Reports/mrholmes.db`): advanced querying

SQLite failure KHÔNG block flat file output (atomic degradation — AC5).

### Database Schema
`Database` singleton thread-safe, schema migration qua `Core/reporting/schema.sql`. Path mặc định: `GUI/Reports/mrholmes.db`.

### Export
- `PdfExporter`: render Jinja2 template → weasyprint/pdfkit → PDF file
- `CsvExporter`: export investigation findings sang CSV

---

## Async Patterns

| Pattern | Implementation | Mục đích |
|---------|---------------|----------|
| Concurrency | `asyncio.gather()` | Scan nhiều site đồng thời |
| Throttling | `asyncio.Semaphore(20)` | Giới hạn concurrent connections |
| Retry | `RetryPolicy` exponential backoff + jitter | Xử lý timeout, rate limit |
| HTTP client | `aiohttp.ClientSession` | Connection pooling |

`RetryPolicy` phân biệt 3 loại exception: `TargetSiteTimeout` (retry với backoff), `RateLimitExceeded` (retry với `retry_after`), `ProxyDeadError` (re-raise ngay — proxy switching là nhiệm vụ của `ProxyManager`).

---

## Proxy System

`ProxyManager` encapsulate toàn bộ proxy lifecycle:
- `configure(choice)` — enable/disable proxy
- `load_proxy_pool(path)` — load danh sách proxy từ file
- `rotate()` — lấy proxy tiếp theo (round-robin hoặc random)
- `mark_dead(url)` — loại proxy khỏi pool
- `health_check_pool()` — kiểm tra toàn bộ pool, trả về `HealthReport`

---

## Scraping Architecture

### `ScraperRegistry` — `Core/scrapers/registry.py`
Thay thế 250 LOC copy-paste dispatch (48 `Scraper.info.*` calls). Registry pattern:

```python
registry.register("Instagram", lambda proxy: Scraper.info.Instagram(...))
registry.dispatch(matched_sites, http_proxy)
```

Khi thêm scraper mới, chỉ cần 1 dòng `register()` — không cần sửa dispatch logic.

### 19 Platform Scrapers (Core/Support/Username/)
Deep scrapers cho các platform có profile page: Instagram, Twitter, TikTok, GitHub, GitLab, DockerHub, Imgur, Kik, Wattpad, MixCloud, và các platform khác. Sử dụng `BeautifulSoup` + JSON API tùy platform.

`ApifyScraper` (`Core/engine/apify_scraper.py`) xử lý Instagram deep scrape qua Apify Actor API để bypass anti-bot.
