# Mr.Holmes — Source Tree Analysis

Cây thư mục có chú thích mục đích cho từng directory quan trọng.

---

## Cây thư mục đầy đủ

```text
Mr.Holmes/
│
├── MrHolmes.py                     # Entry point chính: interactive menu + batch CLI flags
│
├── Core/                           # Toàn bộ Python application logic
│   │
│   ├── autonomous_cli.py           # Option 16: Autonomous Profiler flow (Story 8.4)
│   │
│   ├── Searcher.py                 # Username scan entry — khởi tạo ScanPipeline
│   ├── Searcher_phone.py           # Phone OSINT entry
│   ├── Searcher_website.py         # Domain/Website OSINT entry
│   ├── Searcher_person.py          # Person profiling entry
│   ├── E_Mail.py                   # Email OSINT entry
│   ├── Dork.py                     # Google/Yandex dork generation
│   ├── Port_Scanner.py             # Active port scanner
│   ├── PDF_Converter.py            # Legacy PDF conversion
│   ├── Decoder.py                  # Encoding/decoding utilities
│   ├── Session.py                  # Session management
│   ├── Transfer.py                 # File transfer utilities
│   ├── Update.py                   # Self-update mechanism
│   │
│   ├── engine/                     # Core async engine (Epic 2–8)
│   │   ├── scan_pipeline.py        # ScanPipeline: orchestrate username scan (150+ sites)
│   │   ├── async_search.py         # search_site() async HTTP check per site
│   │   ├── result_collector.py     # ScanResultCollector: thread-safe accumulator
│   │   ├── retry.py                # RetryPolicy: exponential backoff + jitter
│   │   ├── autonomous_agent.py     # RecursiveProfiler: BFS clue discovery engine
│   │   ├── llm_synthesizer.py      # LLMSynthesizer: OpenAI-compatible AI report
│   │   ├── mindmap_generator.py    # MindmapGenerator: vis-network HTML export
│   │   └── apify_scraper.py        # ApifyScraper: Instagram deep scrape via Apify
│   │
│   ├── plugins/                    # Intelligence Plugin system (Epic 7)
│   │   ├── base.py                 # IntelligencePlugin Protocol + PluginResult dataclass
│   │   ├── manager.py              # PluginManager: auto-discover, register, run all
│   │   ├── hibp.py                 # HaveIBeenPwned plugin (EMAIL breach check)
│   │   ├── shodan.py               # Shodan plugin (IP/DOMAIN exposed services)
│   │   ├── leak_lookup.py          # LeakLookup plugin (EMAIL/USERNAME breach)
│   │   └── searxng.py              # SearxNG plugin (web search, all target types)
│   │
│   ├── cli/                        # CLI modernization layer (Epic 5)
│   │   ├── parser.py               # argparse: --username, --email, --export, --config
│   │   ├── runner.py               # BatchRunner: non-interactive scan execution
│   │   ├── output.py               # OutputHandler abstraction
│   │   ├── config_wizard.py        # Interactive API key wizard
│   │   └── rich_output.py          # rich: spinners, tables, colored progress
│   │
│   ├── models/                     # Data models (Epic 1)
│   │   ├── scan_context.py         # ScanContext, ScanConfig dataclasses
│   │   ├── scan_result.py          # ScanResult, ScanStatus enum
│   │   ├── validators.py           # sanitize_username(), safe_int_input()
│   │   └── exceptions.py           # OSINTError, TargetSiteTimeout, RateLimitExceeded, etc.
│   │
│   ├── reporting/                  # Reporting layer (Epic 6)
│   │   ├── database.py             # Database singleton (SQLite, thread-safe)
│   │   ├── schema.sql              # CREATE TABLE migrations
│   │   ├── writer.py               # ReportWriter: dual-write flat files + SQLite
│   │   ├── pdf_export.py           # PdfExporter: Jinja2 → weasyprint/pdfkit
│   │   ├── csv_export.py           # CsvExporter: investigation findings → CSV
│   │   └── templates/              # Jinja2 HTML templates cho PDF rendering
│   │
│   ├── proxy/                      # Proxy management (Epic 1 + Epic 3)
│   │   └── manager.py              # ProxyManager: pool rotation, health check, identity
│   │
│   ├── scrapers/                   # Scraper registry (Epic 1)
│   │   └── registry.py             # ScraperRegistry: register + dispatch platform scrapers
│   │
│   ├── config/                     # Configuration management (Epic 4)
│   │   ├── settings.py             # Settings singleton: .env + Configuration.ini
│   │   └── logging_config.py       # Centralized logger factory
│   │
│   └── Support/                    # Legacy utility layer
│       ├── Menu.py                 # Interactive menu dispatcher (option 1–16)
│       ├── Font.py                 # ANSI color codes
│       ├── Language.py             # i18n translation loader
│       ├── Headers.py              # HTTP user-agent headers
│       ├── Proxies.py              # Legacy proxy helper
│       ├── ProxyRequests.py        # Proxy-aware requests wrapper
│       ├── Requests_Search.py      # Legacy sync search (backward compat)
│       ├── Database.py             # Legacy database helper
│       ├── Logs.py                 # Log file management
│       ├── Notification.py         # Desktop/email notifications
│       ├── Useragent.py            # Random user-agent selection
│       ├── Dorks.py                # Dork template loader
│       ├── Recap.py                # Session recap summary
│       ├── FileTransfer.py         # File copy utilities
│       │
│       ├── Username/               # Username deep scrapers
│       │   ├── Scraper.py          # 19 platform scrapers (Instagram, GitHub, TikTok, etc.)
│       │   └── Get_Posts.py        # Post/media downloader
│       │
│       ├── Phone/                  # Phone OSINT support
│       │   ├── Numbers.py          # phonenumbers wrapper
│       │   └── Lookup.py           # Phone lookup API
│       │
│       ├── Mail/                   # Email OSINT support
│       │   └── Mail_Validator.py   # Email format validation
│       │
│       ├── Person/                 # Person profiling support
│       ├── Websites/               # Website OSINT support
│       └── Notification/           # Notification templates
│
├── GUI/                            # PHP web dashboard (standalone)
│   ├── index.php                   # Dashboard entry point
│   ├── Actions/                    # PHP request controllers
│   ├── Reports/                    # Output bridge: Python ghi, PHP đọc
│   │   ├── mrholmes.db             # SQLite database (shared với Python)
│   │   ├── Usernames/              # Username scan results
│   │   ├── E-Mail/                 # Email scan results
│   │   ├── Phone/                  # Phone scan results
│   │   ├── Autonomous/             # Autonomous profiler artifacts
│   │   ├── CSV/                    # CSV exports
│   │   ├── Dorks/                  # Dork results
│   │   └── Ports/                  # Port scan results
│   ├── Database/                   # PHP DB abstraction layer
│   ├── Graphs/                     # Chart/graph rendering (PHP)
│   ├── Maps/                       # Map visualization (PHP)
│   ├── PDF/                        # PDF viewer (PHP)
│   ├── Theme/                      # CSS themes
│   ├── Css/                        # Stylesheet files
│   └── searxng/                    # SearxNG Docker config
│
├── Site_lists/                     # JSON site definitions (no-code extension)
│   ├── Username/
│   │   ├── site_list.json          # 150+ sites: URL pattern, error string, tags
│   │   ├── NSFW_site_list.json     # NSFW sites (opt-in)
│   │   ├── Google_dorks.txt        # Google dork templates
│   │   └── Yandex_dorks.txt        # Yandex dork templates
│   ├── E-Mail/                     # Email lookup sites
│   ├── Phone/                      # Phone lookup sites
│   ├── Websites/                   # Website/domain lookup sites
│   └── Dorks/                      # Dork templates
│
├── Configuration/
│   └── Configuration.ini           # Non-secret settings: language, SMTP, proxy path, etc.
│
├── Lang/                           # i18n translation files (JSON per language)
│
├── Proxies/                        # Proxy list files
├── Useragents/                     # User-agent list files
├── Banners/                        # ASCII art banners
├── Quotes/                         # Random quotes cho CLI
├── Logs/                           # Runtime log files
├── Temp/                           # Temporary files
├── Transfer/                       # Transfer output staging
│
├── tests/                          # Test suite
├── test_epic2.py                   # Epic 2 async engine tests
├── test_epic7_suite.py             # Epic 7 plugin system tests
├── pytest.ini                      # pytest configuration
│
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Dev/test dependencies
├── install.sh                      # Linux/macOS install script
├── install_Termux.sh               # Termux (Android) install script
├── Install.cmd                     # Windows install script
│
├── docs/                           # Project documentation (thư mục này)
├── design-artifacts/               # Architecture diagrams, PRDs
└── _bmad/                          # BMAD workflow artifacts
```

---

## Directories quan trọng nhất

### `Core/engine/`
Não của hệ thống. Chứa async scan engine, BFS profiler, AI synthesizer, và mindmap generator. Mọi tính năng mới thuộc epic-level đều được thêm vào đây.

### `Core/plugins/`
Plugin system. Thêm intelligence source mới bằng cách tạo file mới implement `IntelligencePlugin` Protocol — `PluginManager` tự discover.

### `Site_lists/Username/site_list.json`
Bộ não no-code của username scanner. Định nghĩa 150+ site với URL pattern, error string, và tags. Thêm site mới không cần sửa Python code.

### `GUI/Reports/`
Bridge layer duy nhất giữa Python và PHP. Python ghi output vào đây, PHP đọc và hiển thị. `mrholmes.db` là SQLite database được chia sẻ.

### `Core/config/settings.py`
Điểm tập trung mọi configuration. Đọc từ `.env` (secrets) và `Configuration.ini` (settings). Import `from Core.config import settings` ở bất kỳ đâu.

### `Core/Support/`
Layer legacy được giữ lại cho backward compatibility. Code mới nên dùng engine/plugins/cli thay vì thêm vào Support.
