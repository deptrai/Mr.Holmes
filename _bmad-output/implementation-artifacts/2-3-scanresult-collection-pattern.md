# Story 2.3: ScanResult Collection Pattern

Status: done

## Story

As a developer,
I want to implement centralized `ScanResult[]` collection pattern cho concurrent scan results,
so that results từ `asyncio.gather()` được thu thập, sorted, và processed ở 1 nơi duy nhất.

## Acceptance Criteria

1. **AC1:** `ScanResultCollector` class thu thập tất cả `ScanResult` objects
2. **AC2:** Methods: `add()`, `get_found()`, `get_tags()`, `get_scraper_sites()`, `to_json()`, `to_report()`
3. **AC3:** Replace 5 shared mutable lists (successfull, successfullName, ScraperSites, Tags, MostTags)
4. **AC4:** Thread-safe cho concurrent access
5. **AC5:** Export compatible với existing report format

## Tasks / Subtasks

- [x] Task 1 — Create `ScanResultCollector` class
  - [x] `Core/engine/result_collector.py`
  - [x] Accumulate `ScanResult` objects from gather

- [x] Task 2 — Implement derived properties
  - [x] `found_urls` → replaces `successfull` list
  - [x] `found_names` → replaces `successfullName` list
  - [x] `scraper_sites` → replaces `ScraperSites` list
  - [x] `all_tags`, `most_tags` → replaces `Tags`, `MostTags` logic

- [x] Task 3 — Report export methods
  - [x] `to_report_text()` → .txt format (same as current)
  - [x] `to_json()` → JSON format
  - [x] `to_mh()` → .mh format

- [x] Task 4 — Integrate into ScanPipeline (exported from `Core/engine/__init__.py`)
- [x] Task 5 — Unit tests (20 tests, AC1-5)

## Dev Notes

### Dependencies

- **REQUIRES Story 1.1** — ScanResult dataclass
- **REQUIRES Story 2.2** — gather produces ScanResult list
- **BUILDING ON Story 1.2** — tag processing logic reused here

### File Structure

```
Core/engine/
└── result_collector.py  # NEW — ScanResultCollector
```

## Dev Agent Record

### Agent Model Used
### Completion Notes List
### File List
