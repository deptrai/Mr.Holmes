# Story 7.1: Plugin Interface Design

Status: ready-for-dev

## Story

As a developer,
I want to tạo Plugin Interface chuẩn cho external API integrations,
so that adding new intelligence sources (HIBP, Shodan, etc.) chỉ cần implement 1 interface.

## Acceptance Criteria

1. **AC1:** `IntelligencePlugin` Protocol tại `Core/plugins/base.py`
2. **AC2:** Methods: `name()`, `requires_api_key()`, `check(target, target_type) → PluginResult`
3. **AC3:** `PluginManager` — discover, load, execute plugins
4. **AC4:** Plugin results integrated vào ScanResultCollector
5. **AC5:** API key management via `.env`

## Tasks / Subtasks

- [ ] Task 1 — Define `IntelligencePlugin` Protocol
- [ ] Task 2 — Define `PluginResult` dataclass
- [ ] Task 3 — Implement `PluginManager`
- [ ] Task 4 — API key injection from Settings
- [ ] Task 5 — Unit tests with mock plugin

## Dev Notes

### Plugin Interface
```python
class IntelligencePlugin(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def requires_api_key(self) -> bool: ...
    async def check(self, target: str, target_type: str) -> PluginResult: ...
```

### Dependencies
- **REQUIRES Story 4.2** — .env for API keys
- **REQUIRED BY Stories 7.2, 7.3, 7.4**

### File Structure
```
Core/plugins/
├── __init__.py   # NEW
├── base.py       # NEW — Protocol + PluginResult
└── manager.py    # NEW — PluginManager
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
