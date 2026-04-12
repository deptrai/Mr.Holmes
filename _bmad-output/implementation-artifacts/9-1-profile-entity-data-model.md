# Story 9.1: ProfileEntity Data Model

Status: done

## Story

As a developer building the Epic 9 profiling pipeline,
I want a `ProfileEntity` dataclass that holds merged OSINT data from multiple sources with confidence scoring,
so that the system has a unified Golden Record data model for identity synthesis.

## Acceptance Criteria

1. `ProfileEntity` dataclass tồn tại tại `Core/models/profile_entity.py` với các fields:
   - `seed: str` — input ban đầu (email/username/phone)
   - `seed_type: str` — "EMAIL" | "USERNAME" | "PHONE"
   - `real_names: list[SourcedField]`
   - `emails: list[SourcedField]`
   - `phones: list[SourcedField]`
   - `usernames: list[SourcedField]`
   - `locations: list[SourcedField]`
   - `avatars: list[SourcedField]`
   - `bios: list[SourcedField]`
   - `platforms: dict[str, str]` — `{platform_name: profile_url}`
   - `breach_sources: list[str]`
   - `active_hours: dict[str, Any]` — e.g. `{"timezone": "UTC+7", "peak": "22:00-02:00"}`
   - `confidence: float` — overall confidence 0.0-1.0
   - `sources: list[str]` — list of plugin names that contributed data

2. `SourcedField` dataclass với:
   - `value: str`
   - `source: str` — plugin name
   - `confidence: float` — 0.0-1.0

3. `ProfileEntity.merge(other: ProfileEntity) -> ProfileEntity`:
   - Merge 2 entities thành 1, dedup values trong mỗi list field
   - Overall confidence = average của tất cả SourcedField.confidence trong merged entity
   - Sources list = union của 2 sources lists

4. `ProfileEntity.to_dict() -> dict` — JSON-serializable output
5. `ProfileEntity.from_dict(data: dict) -> ProfileEntity` — classmethod reconstruct từ dict
6. `Core/models/__init__.py` export `ProfileEntity` và `SourcedField`
7. Unit tests tại `tests/models/test_profile_entity.py` với coverage ≥ 80%:
   - Test merge với overlapping values → dedup
   - Test merge confidence averaging
   - Test to_dict/from_dict roundtrip
   - Test empty entity merge

## Tasks / Subtasks

- [x] Task 1: Tạo `SourcedField` dataclass (AC: 2)
  - [x] `value`, `source`, `confidence` fields
  - [x] `__eq__` by value (ignore source/confidence khi so sánh)

- [x] Task 2: Tạo `ProfileEntity` dataclass (AC: 1)
  - [x] Tất cả fields với `field(default_factory=...)` cho mutable defaults
  - [x] `confidence: float = 0.0`, `sources: list[str] = field(default_factory=list)`

- [x] Task 3: Implement `merge()` method (AC: 3)
  - [x] Merge mỗi list field bằng cách dedup theo `value`
  - [x] Merge `platforms` dict (union, no overwrite)
  - [x] Merge `breach_sources` (dedup)
  - [x] Recalculate `confidence` = mean của tất cả SourcedField.confidence
  - [x] Union `sources` lists

- [x] Task 4: Implement `to_dict()` và `from_dict()` (AC: 4, 5)
  - [x] `to_dict()`: convert SourcedField objects → dicts
  - [x] `from_dict()`: reconstruct SourcedField objects từ dicts

- [x] Task 5: Update `Core/models/__init__.py` exports (AC: 6)

- [x] Task 6: Viết unit tests (AC: 7)
  - [x] `tests/models/test_profile_entity.py`
  - [x] 21 test cases (≥ 4 covering AC 7) — 100% pass

## Dev Notes

### Existing Patterns to Follow

- Existing models ở `Core/models/`: `ScanContext` (`Core/models/scan_context.py`), `ScanResult` (`Core/models/scan_result.py`) đều dùng `@dataclass` với `field(default_factory=...)` — follow cùng pattern
- `Core/models/__init__.py` hiện export `ScanContext`, `ScanResult`, `ValidationError` — thêm `ProfileEntity` và `SourcedField` vào đây
- Tests existing tại `tests/models/` — tạo `tests/models/test_profile_entity.py` cùng thư mục

### Key Design Decisions

**`SourcedField.__eq__` chỉ so sánh `value`:**
```python
def __eq__(self, other):
    if isinstance(other, SourcedField):
        return self.value == other.value
    return NotImplemented

def __hash__(self):
    return hash(self.value)
```
Điều này cho phép `set()` dedup theo value khi merge.

**Merge confidence calculation:**
```python
all_fields = [f for lst in [self.real_names, self.emails, ...] for f in lst]
if all_fields:
    merged.confidence = sum(f.confidence for f in all_fields) / len(all_fields)
```

**`ProfileEntity` không kế thừa `ProfileGraph` — đây là data model riêng biệt.** `ProfileGraph` (trong `autonomous_agent.py`) vẫn giữ nguyên cho Epic 8 backward compat. Epic 9 sẽ build Golden Record từ `ProfileGraph.plugin_results`.

### File Locations

| File | Action |
|------|--------|
| `Core/models/profile_entity.py` | CREATE |
| `Core/models/__init__.py` | MODIFY — thêm exports |
| `tests/models/test_profile_entity.py` | CREATE |

### Project Structure Notes

- `Core/models/` là đúng location cho data model này (consistent với `ScanContext`, `ScanResult`)
- Không đặt vào `Core/engine/` — engine sẽ import model, không ngược lại
- File naming: `profile_entity.py` (snake_case, consistent với `scan_context.py`)

### References

- Existing dataclass pattern: [Source: Core/models/scan_context.py]
- Plugin Protocol: [Source: Core/plugins/base.py] — `PluginResult.data: dict[str, Any]`
- ProfileNode (để hiểu context Epic 8): [Source: Core/engine/autonomous_agent.py#ProfileNode]
- PRD FR19-FR23 (Golden Record requirements): [Source: _bmad-output/planning-artifacts/prd-epic9.md#Golden-Record--Entity-Resolution]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_none_

### Completion Notes List

- `SourcedField.__eq__` chỉ so sánh value → dedup via set() trong merge() hoạt động đúng
- `_LIST_FIELDS` định nghĩa là dataclass field với `init=False` để tránh duplicate code trong merge/serialization
- `_dedup_sourced_fields()` là module-level helper, không dùng set() để preserve insertion order
- `merge()` merge platforms với `.setdefault()` → first source wins (no overwrite)
- 21 unit tests pass, 0 regression

### File List

- `Core/models/profile_entity.py` (created)
- `Core/models/__init__.py` (modified)
- `tests/models/test_profile_entity.py` (created)

### Review Findings

- [x] [Review][Patch] P5: `_LIST_FIELDS` should be `ClassVar` instead of dataclass `field()` [`Core/models/profile_entity.py:93`] — FIXED
