---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2026-03-26'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/epics.md
  - docs/project-context.md
  - docs/architecture.md
  - docs/component-inventory.md
  - docs/tech-stack.md
  - docs/source-tree-analysis.md
  - docs/testing-strategy.md
  - docs/brownfield-analysis-Mr.Holmes-2025-10-08.md
workflowType: 'architecture'
project_name: 'Mr.Holmes'
user_name: 'Luisphan'
date: '2026-03-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (24 FRs):**

| Capability Area | FRs | Tóm tắt |
|----------------|-----|---------|
| Scanning Engine | FR1-5 | Async concurrent scanning, rate limiting, retry |
| Proxy Management | FR6-8 | Auto-rotate, health-check, configurable sources |
| Scraper System | FR9-11 | Registry pattern, concurrent dispatch, retry fallback |
| Data & Reporting | FR12-15 | SQLite dual-write, PDF/CSV export, cross-case search |
| CLI & UX | FR16-18 | Batch mode, Rich UI, input validation |
| Security & Config | FR19-21 | .env secrets, structured logging, unit tests |
| External Intelligence | FR22-24 | HaveIBeenPwned, Shodan, API key config |

**Non-Functional Requirements (7 NFRs):**

- NFR1: Scan 300 sites < 2 phút (semaphore=20)
- NFR2: Memory < 200MB/session
- NFR3: Test coverage > 60% core modules
- NFR4: Backward compatible với PHP GUI (dual-write)
- NFR5: Python 3.9+
- NFR6: Zero plaintext secrets
- NFR7: Structured error messages

### Scale & Complexity

- **Primary domain:** CLI backend / OSINT scraping engine
- **Complexity level:** HIGH (brownfield refactoring, 690 LOC God Method, zero tests, significant tech debt)
- **Estimated architectural components:** ~8 (ScanPipeline, AsyncScanner, ProxyManager, ScraperRegistry, ReportWriter, ExportManager, ConfigManager, CLIInterface)

### Technical Constraints & Dependencies

- Python 3.9+ required (asyncio maturity)
- PHP GUI backward compatibility — file-based reports must continue working during migration
- Existing site list JSON format (`Site_lists/`) must be preserved
- i18n system (`Language.Translation`) integrated across all output layers
- `os.chdir()` pattern in Scraper — relative paths create fragile navigation

### Cross-Cutting Concerns Identified

| Concern | Ảnh hưởng | Components |
|---------|-----------|------------|
| Error Handling | ALL | Custom exceptions, structured logging thay except:pass |
| Proxy Management | Scanning + Scraping | ProxyManager shared across engine |
| Structured Logging | ALL | Replace print() với logging module |
| File I/O Safety | Reporting + Writers | Context managers, aiofiles |
| i18n/Localization | CLI Output | Language.Translation integration |
| Concurrency Safety | Scanning + Reporting | ScanResult[] collect pattern, avoid shared mutable state |

## Technology Stack Decisions

### Primary Domain: CLI Backend / OSINT Scraping Engine (Python)

### Selected Stack (Brownfield Evolution)

| Layer | Công nghệ | Version | Lý do |
|-------|-----------|---------|-------|
| Runtime | Python | 3.9+ | asyncio maturity, existing codebase |
| HTTP Client | aiohttp | latest | Async HTTP, connection pooling |
| Async Runtime | asyncio | stdlib | Native Python, zero dependency |
| File I/O | aiofiles | latest | Non-blocking file operations |
| CLI Framework | argparse + Rich | stdlib + latest | Batch mode + modern TUI |
| Testing | pytest + aioresponses | latest | Mock HTTP, async test support |
| Config/Secrets | python-dotenv | latest | .env files, security best practice |
| Logging | logging | stdlib | Structured levels, no dependency |
| Data Storage | SQLite + flat files | stdlib | Dual-write backward compat |
| Templating | Jinja2 | latest | PDF/HTML report generation |

### Rationale

- Tối thiểu hóa external dependencies — ưu tiên stdlib
- Backward compatible với PHP GUI qua dual-write strategy
- aiohttp là async HTTP client mature nhất cho Python

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Code Architecture Patterns (Pipeline + Registry)
2. Concurrency Model (asyncio.gather + Semaphore)
3. Error Handling Hierarchy

**Important Decisions (Shape Architecture):**
4. Data Architecture (Normalized SQLite + dual-write)
5. Module Structure (Core/ reorganization)
6. Interface Contracts (Python Protocols)

**Deferred Decisions (Post-MVP):**
7. Docker packaging
8. Plugin SDK
9. REST API layer

### Code Architecture — Pipeline + Registry

**Decision:** Decompose God Method into Pipeline Pattern + Scraper Registry.

- `MrHolmes.search()` 500 LOC → `ScanPipeline` class với 8 stages
- 15 scrapers copy-paste → `SCRAPER_REGISTRY` dict + generic dispatcher
- 3x proxy code duplication → `ProxyManager` singleton

**Rationale:** Mỗi stage có 1 trách nhiệm, testable independently, dễ thêm/sửa.

### Concurrency Model

**Decision:** `asyncio.gather()` + `Semaphore(20)` + `ScanResult` collection.

- Semaphore giới hạn concurrent connections (configurable)
- `ScanResult` dataclass thu kết quả — không shared mutable lists
- Main event loop tại entry point (`asyncio.run()`)

**Rationale:** Tránh race conditions, memory-efficient, 10-30x faster.

### Error Handling Hierarchy

**Decision:** Custom exception hierarchy thay thế `except Exception: pass`.

```
OSINTError (base)
├── TargetSiteTimeout
├── ProxyDeadError
├── RateLimitExceeded
├── ScraperError
└── ConfigurationError
```

Retry policy: Exponential backoff + jitter, max 3 retries.

### Data Architecture

**Decision:** Normalized SQLite + dual-write cho backward compatibility.

**Schema:**
- `subjects` (id, type, value, created_at)
- `findings` (id, subject_id, source_id, url, status, tags, scraped_data)
- `sources` (id, name, category, error_type)
- `scans` (id, subject_id, started_at, proxy_used, total_found)

**Dual-write:** `ReportWriter` ghi cả flat file (`GUI/Reports/`) + SQLite song song.

### Module Structure

**Decision:** Reorganize `Core/` thành domain-based modules.

```
Core/
├── models/          # ScanContext, ScanResult, ScanConfig dataclasses
├── engine/          # ScanPipeline, AsyncScanner
├── proxy/           # ProxyManager
├── scrapers/        # ScraperRegistry + individual scrapers
├── reporting/       # ReportWriter, ExportManager
├── config/          # ConfigManager (.env loader)
├── cli/             # CLIInterface (argparse + Rich)
└── support/         # Logging, i18n, utilities (existing)
```

### Interface Contracts — Python Protocols

**Decision:** Dùng `typing.Protocol` cho loose coupling.

```python
class ScraperPlugin(Protocol):
    name: str
    async def scrape(self, url: str, ctx: ScanContext) -> ScanResult: ...

class ReportOutput(Protocol):
    async def write(self, results: list[ScanResult]) -> None: ...
```

### Decision Impact Analysis

**Implementation Sequence:**
1. `models/` (ScanContext, ScanResult) — prerequisite cho mọi thứ
2. `proxy/` (ProxyManager) — extracted từ existing code
3. `scrapers/` (Registry) — eliminates duplication
4. `engine/` (ScanPipeline) — decomposes God Method
5. `reporting/` (ReportWriter) — dual-write
6. `config/` (ConfigManager) — .env migration
7. `cli/` (CLIInterface) — batch mode + Rich

**Cross-Component Dependencies:**
- `engine/` depends on `models/`, `proxy/`, `scrapers/`
- `reporting/` depends on `models/`
- `cli/` depends on `engine/`, `config/`
- `scrapers/` depends on `models/`, `proxy/`

## Implementation Patterns & Consistency Rules

### Naming Patterns

| Ngữ cảnh | Convention | Ví dụ |
|----------|-----------|-------|
| File/Module | `snake_case.py` | `scan_pipeline.py`, `proxy_manager.py` |
| Class | `PascalCase` | `ScanPipeline`, `ProxyManager` |
| Function/Method | `snake_case` | `dispatch_scrapers()`, `health_check()` |
| Variable | `snake_case` | `scan_result`, `proxy_dict` |
| Constant | `UPPER_SNAKE` | `SCRAPER_REGISTRY`, `MAX_RETRIES` |
| DB Table | `snake_case` (plural) | `subjects`, `findings`, `sources` |
| DB Column | `snake_case` | `subject_id`, `created_at` |

### Structure Patterns

- Tests: `tests/` mirror `Core/` structure (`tests/engine/test_scan_pipeline.py`)
- Config: `.env` tại project root, `Configuration/` cho non-secret settings
- Shared utils: `Core/support/` (existing pattern preserved)

### Format Patterns

- JSON output fields: `snake_case`
- Dates: ISO 8601 (`2026-03-26T22:45:00+07:00`)
- Booleans: `true/false` (Python native)

### Process Patterns

**Error Handling (Bắt buộc):**
```python
# ✅ ĐÚNG
try:
    result = await scanner.check(site, ctx)
except RateLimitExceeded as e:
    logger.warning("Rate limited: %s", site.name, exc_info=True)
    await asyncio.sleep(e.retry_after)
except OSINTError as e:
    logger.error("Scan failed: %s: %s", site.name, e)
    results.append(ScanResult(site=site, found=False, error=str(e)))
```

**Logging (Bắt buộc):**
```python
logger = logging.getLogger(__name__)  # Mỗi module 1 logger
```

**Async (Bắt buộc):**
```python
# ✅ Collect results tập trung
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Enforcement — All Agents MUST:

1. Dùng `dataclass` cho mọi data structure (không raw dict)
2. Dùng `typing.Protocol` cho interfaces
3. Dùng `with` cho file I/O (KHÔNG raw `open()`)
4. Dùng `logging` module (KHÔNG `print()`)
5. Mỗi function < 50 LOC, mỗi file < 200 LOC

## Project Structure & Boundaries

### Complete Project Directory Structure

```
Mr.Holmes/
├── MrHolmes.py                    # Entry point (asyncio.run())
├── .env                           # Secrets (SMTP, API keys)
├── .env.example                   # Template
├── requirements.txt               # Dependencies
├── .github/workflows/ci.yml       # GitHub Actions CI
│
├── Core/
│   ├── models/                    # 🆕 Data structures
│   │   ├── __init__.py
│   │   ├── scan_context.py        # ScanContext, ScanConfig
│   │   ├── scan_result.py         # ScanResult
│   │   └── exceptions.py          # OSINTError hierarchy
│   │
│   ├── engine/                    # 🆕 Scan orchestration
│   │   ├── __init__.py
│   │   ├── scan_pipeline.py       # ScanPipeline
│   │   └── async_scanner.py       # AsyncScanner (aiohttp)
│   │
│   ├── proxy/                     # 🆕 Proxy management
│   │   ├── __init__.py
│   │   └── proxy_manager.py       # ProxyManager
│   │
│   ├── scrapers/                  # 🆕 Plugin scrapers
│   │   ├── __init__.py
│   │   ├── registry.py            # SCRAPER_REGISTRY
│   │   ├── instagram.py
│   │   ├── twitter.py
│   │   ├── tiktok.py
│   │   └── ...
│   │
│   ├── reporting/                 # 🆕 Report output
│   │   ├── __init__.py
│   │   ├── report_writer.py       # Dual-write
│   │   └── export_manager.py      # PDF/CSV/JSON
│   │
│   ├── config/                    # 🆕 Config
│   │   ├── __init__.py
│   │   └── config_manager.py      # .env loader
│   │
│   ├── cli/                       # 🆕 CLI
│   │   ├── __init__.py
│   │   ├── cli_interface.py       # argparse + Rich
│   │   └── output_layer.py        # Abstract output
│   │
│   ├── Support/                   # ✅ Preserved
│   ├── Searcher.py               # ⚠️ Legacy → wraps ScanPipeline
│   └── Searcher_phone.py         # ⚠️ Legacy
│
├── data/mrholmes.db              # 🆕 SQLite
├── tests/                         # 🆕 Test suite (mirrors Core/)
│   ├── conftest.py
│   ├── engine/test_scan_pipeline.py
│   ├── proxy/test_proxy_manager.py
│   ├── scrapers/test_registry.py
│   └── reporting/test_report_writer.py
│
├── Site_lists/                    # ✅ Preserved
├── GUI/Reports/                   # ✅ Preserved (PHP GUI)
├── Configuration/                 # ✅ Preserved
└── docs/                          # ✅ Preserved
```

### Epic → Structure Mapping

| Epic | Primary Directory | Key Files |
|------|------------------|-----------|
| E1: Foundation | `models/`, `scrapers/`, `proxy/` | `scan_context.py`, `registry.py`, `proxy_manager.py` |
| E2: Async | `engine/` | `scan_pipeline.py`, `async_scanner.py` |
| E3: Proxy | `proxy/` | `proxy_manager.py` |
| E4: Quality | `tests/`, root | `conftest.py`, `.env`, `ci.yml` |
| E5: CLI | `cli/` | `cli_interface.py`, `output_layer.py` |
| E6: Data | `reporting/`, `data/` | `report_writer.py`, `mrholmes.db` |
| E7: APIs | `scrapers/` | New plugin files |

### Data Flow

```
CLI → ConfigManager → ScanPipeline
                        ├── ProxyManager.resolve()
                        ├── AsyncScanner.scan_all() → aiohttp → Sites
                        ├── ScraperRegistry.dispatch()
                        └── ReportWriter.write()
                            ├── flat files (GUI/Reports/)
                            └── SQLite (data/mrholmes.db)
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices (Python 3.9+, aiohttp, asyncio, SQLite) are stdlib or mature Python libs — zero conflicts.

**Pattern Consistency:** Pipeline, Registry, Protocol patterns all follow Python idioms. Naming conventions (snake_case) consistent across DB, code, and JSON output.

**Structure Alignment:** Module structure directly maps to architectural decisions — each decision has a clear home directory.

### Requirements Coverage Validation ✅

**Epic Coverage:**
- ✅ Epic 1 (Foundation): `models/`, `scrapers/registry.py`, `proxy/`
- ✅ Epic 2 (Async): `engine/scan_pipeline.py`, `engine/async_scanner.py`
- ✅ Epic 3 (Proxy): `proxy/proxy_manager.py`
- ✅ Epic 4 (Quality): `tests/`, `.env`, `.github/`
- ✅ Epic 5 (CLI): `cli/cli_interface.py`, `cli/output_layer.py`
- ✅ Epic 6 (Data): `reporting/report_writer.py`, `data/mrholmes.db`
- ✅ Epic 7 (APIs): `scrapers/` plugin files

**NFR Coverage:**
- ✅ NFR1 (Performance): asyncio.gather + Semaphore
- ✅ NFR2 (Memory): Semaphore limits concurrency
- ✅ NFR3 (Test coverage): pytest framework + test structure
- ✅ NFR4 (Backward compat): Dual-write strategy
- ✅ NFR5 (Python 3.9+): All decisions compatible
- ✅ NFR6 (Zero secrets): python-dotenv + .env
- ✅ NFR7 (Structured errors): Custom exception hierarchy + logging

### Implementation Readiness ✅

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
- Clean separation: mỗi architectural concern có module riêng
- Backward compatible: PHP GUI không bị ảnh hưởng
- Incremental: có thể implement từng epic tuần tự
- Testable: mỗi module có test directory tương ứng

**Areas for Future Enhancement:**
- Docker packaging (deferred)
- Plugin SDK documentation (deferred)
- REST API layer (deferred)

### Architecture Completeness Checklist

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped
- [x] Critical decisions documented
- [x] Technology stack fully specified
- [x] Implementation patterns defined
- [x] Naming conventions established
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Requirements to structure mapping complete
- [x] Validation passed all checks

### Implementation Handoff

**AI Agent Guidelines:**
1. Follow all architectural decisions exactly as documented
2. Use implementation patterns consistently
3. Respect module boundaries
4. Start with `Core/models/` (prerequisite for all)

**Implementation Priority:**
1. `Core/models/` → dataclasses + exceptions
2. `Core/proxy/` → extract ProxyManager
3. `Core/scrapers/` → Registry Pattern
4. `Core/engine/` → ScanPipeline (decomposes God Method)
5. `tests/` → pytest framework
6. `Core/reporting/` → dual-write
7. `Core/config/` → .env migration
8. `Core/cli/` → argparse + Rich
