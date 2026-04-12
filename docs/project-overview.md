# Mr.Holmes — Tổng quan dự án

## Giới thiệu

**Mr.Holmes** là một OSINT (Open Source Intelligence) framework kết hợp Python CLI và PHP GUI, được thiết kế để thu thập thông tin công khai về một target từ nhiều nguồn khác nhau. Tool hỗ trợ 5 loại target: username, email, phone, website/domain, và IP address.

Project có xuất xứ từ tác giả Luca Garofalo (Lucksi), được phát triển tiếp với kiến trúc plugin và engine AI autonomous từ Epic 2 đến Epic 8.

---

## Mục tiêu

| Mục tiêu | Mô tả |
|-----------|-------|
| Thu thập thông tin công khai | Quét username trên 150+ site, lookup email breach, tra cứu IP/domain |
| Tự động hóa OSINT | Autonomous profiler BFS khám phá clue mới từ mỗi kết quả |
| Tổng hợp AI | LLM synthesis tạo báo cáo phân tích chuyên nghiệp bằng tiếng Việt |
| Visualization | Mindmap tương tác dạng HTML (vis-network.js) |
| Dual reporting | Ghi song song flat file (`.txt`/`.json`) + SQLite database |

---

## Đối tượng sử dụng

- **OSINT researchers** — thu thập thông tin từ nguồn mở có hệ thống
- **Cybersecurity analysts** — điều tra breach, exposed credentials, infrastructure
- **Ethical hackers** — reconnaissance giai đoạn đầu của penetration testing
- **Private investigators** — tra cứu danh tính, liên lạc xuyên platform

---

## Kiến trúc tổng quan

```
Input (username / email / phone / domain / IP)
        │
        ▼
   CLI Entry Points
   ├── MrHolmes.py          — Interactive menu + batch CLI flags
   └── Core/autonomous_cli.py — Option 16: Autonomous Profiler
        │
        ▼
   Core Engine
   ├── ScanPipeline          — Username scan pipeline (150+ sites, async)
   ├── RecursiveProfiler     — BFS clue discovery (multi-layer)
   ├── PluginManager         — Auto-discover & run Intelligence Plugins
   ├── LLMSynthesizer        — AI report generation (OpenAI-compatible API)
   └── MindmapGenerator      — vis-network HTML export
        │
        ▼
   Reporting Layer
   ├── ReportWriter          — Dual-write flat files + SQLite
   ├── PdfExporter           — PDF via Jinja2 + weasyprint
   └── CsvExporter           — CSV export cho investigations
        │
        ▼
   PHP GUI (GUI/)
   └── index.php             — Web dashboard đọc từ mrholmes.db + flat files
```

---

## Quy mô codebase

| Metric | Giá trị |
|--------|---------|
| Python files | ~248 files |
| Lines of code (Python) | ~74,000 LOC |
| PHP files (GUI) | 45 files |
| Supported username sites | 150+ sites |
| Intelligence plugins | 4 (HIBP, Shodan, LeakLookup, SearxNG) |
| Platform scrapers (deep) | 19 scrapers |
| Target types | 5 (USERNAME, EMAIL, PHONE, DOMAIN, IP) |

---

## Các tính năng chính

### Username OSINT
Quét username trên 150+ platform (Instagram, GitHub, Twitter, TikTok, Steam, v.v.) bằng async HTTP (`aiohttp` + `asyncio.gather` + `Semaphore`). Kết quả bao gồm profile URL, display name, bio, và profile picture.

### Email OSINT
- Lookup breach thông qua HaveIBeenPwned plugin
- Email-to-service mapping qua `holehe`
- Dork generation cho Google/Yandex search

### Phone OSINT
- Lookup carrier, region, line type qua `phonenumbers`
- Scrapers chuyên biệt cho số điện thoại

### Domain / IP OSINT
- Shodan plugin cho exposed services và vulnerabilities
- Port scanner tích hợp
- Reverse IP lookup, WHOIS

### Autonomous Profiler (Epic 8)
BFS engine khám phá clue mới từ kết quả của mỗi layer, tạo ra `ProfileGraph` gồm nodes + edges, sau đó tổng hợp bằng LLM và export mindmap HTML tương tác.

---

## Lịch sử phát triển (Epics)

| Epic | Nội dung |
|------|----------|
| Epic 1 | Refactor God Method → ScanPipeline, ScraperRegistry, ProxyManager |
| Epic 2 | Async engine với aiohttp, Semaphore, RetryPolicy |
| Epic 3 | Proxy pool rotation, health check |
| Epic 4 | Secrets management với python-dotenv |
| Epic 5 | CLI modernization với `rich`, batch mode, config wizard |
| Epic 6 | PDF/CSV export, Apify deep scraping, ReportWriter dual-write |
| Epic 7 | Plugin system (IntelligencePlugin Protocol, PluginManager) |
| Epic 8 | Autonomous Profiler: RecursiveProfiler + LLMSynthesizer + MindmapGenerator |
