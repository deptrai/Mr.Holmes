# Story 1.4: Tạo ScraperRegistry — Replace Copy-Paste Dispatch

Status: done

## Story

As a developer,
I want to thay thế 250 LOC copy-paste scraper dispatch (48 `Scraper.info.*` calls) bằng `ScraperRegistry` dict + generic dispatcher,
so that adding/removing scrapers chỉ cần edit 1 registry entry thay vì copy 15-line blocks.

## Acceptance Criteria

1. **AC1:** `ScraperRegistry` class tại `Core/scrapers/registry.py` với `register()` và `dispatch()` methods
2. **AC2:** Registry dict maps scraper name → callable (e.g., `{"Instagram": Scraper.info.Instagram}`)
3. **AC3:** Generic dispatcher loop thay thế 15+ `if "Name" in ScraperSites:` blocks
4. **AC4:** Mỗi scraper có `try/except` với proxy fallback (giữ behavior cũ)
5. **AC5:** Scraper list dễ mở rộng — thêm scraper = 1 dòng register
6. **AC6:** Unit test verify dispatch routing, error handling

## Tasks / Subtasks

- [ ] Task 1 — Create `Core/scrapers/` package
  - [ ] `Core/scrapers/__init__.py`
  - [ ] `Core/scrapers/registry.py`

- [ ] Task 2 — Build ScraperRegistry class
  - [ ] `register(name: str, callable: Callable, params_factory: Callable)` method
  - [ ] `dispatch(scraper_sites: list, report, username, http_proxy, ...)` method

- [ ] Task 3 — Register all 15 existing scrapers
  - [ ] Instagram, Twitter, TikTok, Github, GitLab, Ngl, Tellonym, Gravatar, Joinroll, Chess, Minecraft, Disqus, Imgur, Pr0gramm, Binarysearch, MixCloud, Dockerhub, Kik, Wattpad

- [ ] Task 4 — Implement generic dispatch loop với proxy fallback
  - [ ] For each scraper_name in scraper_sites: try call → except → retry without proxy

- [ ] Task 5 — Replace dispatch code trong `Searcher.py` (lines ~340-590)
- [ ] Task 6 — Unit tests

## Dev Notes

### Current Dispatch Pattern (repeated 15+ times):

```python
if "Instagram" in ScraperSites:
    try:
        Scraper.info.Instagram(report, username, http_proxy, ...)
    except ConnectionError:
        http_proxy = None
        Scraper.info.Instagram(report, username, http_proxy, ...)
    except Exception as e:
        print("Something went wrong")
```

**48 total `Scraper.info.*` calls** across `Searcher.py` — most are duplicated (primary + fallback).

### Scrapers Found (from grep):
Instagram, Twitter, TikTok, Github, GitLab, Ngl, Tellonym, Gravatar, Joinroll, Chess, Minecraft, Disqus, Imgur, Pr0gramm, Binarysearch, MixCloud, Dockerhub, Kik, Wattpad

### Dependencies

- **REQUIRES Story 1.3** — ScraperRegistry integrates into ScanPipeline
- CAN be developed in parallel, integrated during 1.3

### Architecture Compliance

- [Source: `architecture.md`#Scraper Registry Pattern]
- [Source: `architecture.md`#Module Structure] `Core/scrapers/`

### File Structure

```
Core/
└── scrapers/
    ├── __init__.py     # NEW
    └── registry.py     # NEW — ScraperRegistry
Core/
└── Searcher.py         # MODIFY — replace dispatch blocks
```

## Dev Agent Record

### Agent Model Used
### Completion Notes List
### File List
