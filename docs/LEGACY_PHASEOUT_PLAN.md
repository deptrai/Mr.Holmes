# Legacy Code Phase-Out Plan

## Status: Proposed
## Date: 2026-06-26

---

## 1. Context

Mr.Holmes has two coexisting code generations:

- **Legacy modules** (`Core/Searcher.py`, `Core/Searcher_phone.py`, etc.) —
  the original God Method architecture from Lucksi's Mr.Holmes.
- **Modern modules** (`Core/engine/`, `Core/plugins/`, `Core/cli/`, etc.) —
  Epic 7-9 architecture with async pipeline, plugin system, and dual-write
  reporting.

The legacy modules are still wired into the CLI menu (`Core/Support/Menu.py`)
and are the primary entry points for options 1-14. The modern modules are
accessible via option 16 (Autonomous Profiler) and the batch CLI runner.

**Goal:** Gradually phase out legacy modules by migrating their functionality
to the modern architecture, without breaking backward compatibility.

---

## 2. Legacy Module Inventory

| Module | LOC | Tests | Modern Replacement | Migration Priority |
|--------|-----|-------|--------------------|--------------------|
| `Core/Searcher.py` | 197 | ✅ tests/unit/test_searcher.py | `Core/engine/scan_pipeline.py` | HIGH |
| `Core/Searcher_phone.py` | ~350 | ✅ tests/unit/test_searcher_phone.py | None yet | MEDIUM |
| `Core/Searcher_website.py` | ~400 | ✅ tests/unit/test_searcher_website.py | None yet | MEDIUM |
| `Core/Searcher_person.py` | 213 | ✅ tests/unit/test_searcher_person.py | None yet | MEDIUM |
| `Core/E_Mail.py` | ~300 | ✅ tests/unit/test_email_searcher.py | None yet | MEDIUM |
| `Core/Port_Scanner.py` | ~250 | ✅ tests/unit/test_port_scanner.py | None yet | LOW |
| `Core/Dork.py` | ~150 | Partial | None yet | LOW |
| `Core/Decoder.py` | 74 | ✅ tests/unit/test_decoder.py | None (utility) | LOW |
| `Core/PDF_Converter.py` | 156 | ✅ tests/unit/test_pdf_converter.py | `Core/reporting/pdf_export.py` | LOW |
| `Core/Transfer.py` | 104 | ✅ tests/unit/test_transfer.py | None (utility) | LOW |
| `Core/Session.py` | 41 | ✅ tests/unit/test_session.py | None (utility) | LOW |

**Total legacy LOC:** ~2,200

---

## 3. Migration Strategy

### Phase 1: Username OSINT (HIGH priority)

**Target:** Migrate `Core/Searcher.py` → `Core/engine/scan_pipeline.py`

`ScanPipeline` already exists and `Searcher.search()` already delegates to it.
The remaining work:

1. Move `Google_dork()` and `Yandex_dork()` into `ScanPipeline` or a new
   `DorkGenerator` class under `Core/engine/`.
2. Move `Scraping()` (Instagram/Twitter/TikTok scrapers) into a new
   `ProfileScraper` class under `Core/engine/`.
3. Move `Controll()` (site list iteration) into `ScanPipeline.run()`.
4. Update `Menu.py` option 1 to call `ScanPipeline` directly.
5. Mark `Core/Searcher.py` as deprecated with a deprecation warning.
6. Remove `Core/Searcher.py` after one release cycle.

**Estimated effort:** 2-3 sprints

### Phase 2: Phone/Website/Email/Person OSINT (MEDIUM priority)

**Target:** Create modern equivalents for phone, website, email, person search.

For each:

1. Create a new `ScanPipeline` variant or extend the existing one to handle
   the target type.
2. Migrate site list JSON files to the plugin system where possible.
3. Migrate dork generation to `DorkGenerator`.
4. Migrate report writing to `ReportWriter` (dual-write).
5. Update `Menu.py` to call the new pipeline.
6. Mark legacy module as deprecated.

**Estimated effort:** 4-6 sprints (1-1.5 sprints per module)

### Phase 3: Utility Modules (LOW priority)

**Target:** Migrate or deprecate utility modules.

- `Core/Decoder.py` → Keep as utility, no migration needed.
- `Core/PDF_Converter.py` → Already has `Core/reporting/pdf_export.py`.
  Migrate graph-to-PDF feature, then deprecate.
- `Core/Transfer.py` → Keep as utility, no migration needed.
- `Core/Session.py` → Keep as utility, no migration needed.
- `Core/Port_Scanner.py` → Create `Core/plugins/port_scanner_plugin.py`
  following the IntelligencePlugin Protocol.
- `Core/Dork.py` → Merge into `DorkGenerator` under `Core/engine/`.

**Estimated effort:** 2-3 sprints

---

## 4. Deprecation Process

For each legacy module being phased out:

1. **Add deprecation warning** at module level:
   ```python
   import warnings
   warnings.warn(
       "Core.Searcher is deprecated. Use Core.engine.ScanPipeline instead.",
       DeprecationWarning,
       stacklevel=2,
   )
   ```

2. **Update Menu.py** to call the modern equivalent.

3. **Keep legacy module for one release cycle** as a fallback.

4. **Remove legacy module** after the release cycle, once all tests pass
   with the modern equivalent.

5. **Update AGENTS.md** Module Status Summary to reflect the change.

---

## 5. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking backward compatibility | Keep legacy modules as fallback for one release |
| Missing functionality in modern equivalent | Write feature parity tests before migration |
| User confusion during transition | Document migration in CHANGELOG and AGENTS.md |
| Test coverage gaps | Write tests for modern equivalent before deprecating legacy |

---

## 6. Success Criteria

- [ ] All legacy modules have deprecation warnings
- [ ] All legacy modules have modern equivalents with feature parity
- [ ] All tests pass with modern equivalents
- [ ] Menu.py calls modern equivalents for all options
- [ ] Legacy modules removed after one release cycle
- [ ] AGENTS.md updated to reflect final state

---

## 7. Timeline (Indicative)

| Phase | Duration | Modules |
|-------|----------|---------|
| Phase 1 | 2-3 sprints | Searcher.py |
| Phase 2 | 4-6 sprints | Searcher_phone, Searcher_website, E_Mail, Searcher_person |
| Phase 3 | 2-3 sprints | Decoder, PDF_Converter, Transfer, Session, Port_Scanner, Dork |
| **Total** | **8-12 sprints** | **All legacy modules** |

This is a gradual migration — no big-bang rewrite. Each phase is independently
deployable and reversible.
