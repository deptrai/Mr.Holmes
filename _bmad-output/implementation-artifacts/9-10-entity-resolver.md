# Story 9.10: EntityResolver

Status: review

## Story

As the Golden Record builder,
I want an EntityResolver that merges ProfileEntity objects from multiple sources using confidence-weighted similarity,
so that identity claims from different plugins are unified accurately and false positives are avoided.

## Acceptance Criteria

1. `EntityResolver` class tại `Core/engine/entity_resolver.py`:
   - `resolve(entities: list[ProfileEntity]) -> ProfileEntity` — merge list → 1 Golden Record
   - Input: list của `ProfileEntity` objects (1 per source/plugin)
   - Output: single merged `ProfileEntity` với confidence scores và deduplication

2. Name matching — Jaro-Winkler similarity:
   - Khi merge `real_names`, so sánh pairwise bằng Jaro-Winkler (`jellyfish` library)
   - Nếu similarity ≥ 0.85 → treat as same person, merge (keep value với higher confidence, boost confidence bằng 0.1)
   - Nếu similarity < 0.85 → giữ cả 2 entry riêng biệt
   - Thư viện: `jellyfish` (pure Python, pip install jellyfish)

3. Avatar deduplication — pHash:
   - Nếu `avatar_url` present trong profiles → download và tính perceptual hash
   - pHash difference ≤ 10 → same person (boost confidence 0.15)
   - Thư viện: `imagehash` (pip install imagehash Pillow)
   - Skip pHash nếu `imagehash` không installed hoặc download fails — không block resolve

4. Merge gate — FR23: chỉ merge nếu ≥ 2 independent signals:
   - Independent signal = different `source` trong `SourcedField`
   - Nếu chỉ có 1 nguồn → trả về ProfileEntity đó không merge, confidence giữ nguyên
   - Nếu ≥ 2 nguồn → merge, recalculate confidence theo `ProfileEntity.merge()`

5. Confidence thresholds:
   - Merged entity confidence < 0.5 → tag `entity.flags = ["LOW_CONFIDENCE"]` trong `sources` list với prefix `"⚠ "`
   - Confidence ≥ 0.75 → Golden Record chất lượng cao

6. `EntityResolver` không gọi external APIs — pure computation:
   - pHash download trong helper method, catch tất cả exceptions silently
   - Jaro-Winkler sync, không cần async

7. Unit tests tại `tests/engine/test_entity_resolver.py` ≥ 80% coverage:
   - Test merge 2 entities với same name (similarity ≥ 0.85) → deduped, confidence boosted
   - Test merge 2 entities với different names → both retained
   - Test single-source entity → không merge, confidence unchanged
   - Test merge gate enforcement (1 source → no merge)
   - Test low confidence flagging (< 0.5)
   - Test pHash skip khi imagehash không installed

## Tasks / Subtasks

- [x] Task 1: Tạo `Core/engine/entity_resolver.py` (AC: 1)
  - [x] Class skeleton với `resolve()` signature

- [x] Task 2: Implement Jaro-Winkler name merging (AC: 2)
  - [x] `try: import jellyfish` — graceful skip nếu không có
  - [x] Pairwise comparison trong `real_names`
  - [x] Confidence boost logic

- [x] Task 3: Implement pHash avatar comparison (AC: 3)
  - [x] `try: import imagehash, PIL` — graceful skip nếu không có
  - [x] Download avatar URL → compute hash → compare
  - [x] Confidence boost khi match

- [x] Task 4: Implement merge gate (AC: 4, 5)
  - [x] Count independent sources
  - [x] Single-source guard
  - [x] Low confidence flag

- [x] Task 5: Viết unit tests (AC: 7)

## Dev Notes

### Jaro-Winkler Integration

```python
def _names_similar(name1: str, name2: str, threshold: float = 0.85) -> bool:
    try:
        import jellyfish
        return jellyfish.jaro_winkler_similarity(name1.lower(), name2.lower()) >= threshold
    except ImportError:
        # Fallback: exact match only
        return name1.lower().strip() == name2.lower().strip()
```

### pHash Integration

```python
async def _avatar_hash(url: str) -> int | None:
    """Download image and compute perceptual hash. Returns None on any error."""
    try:
        import imagehash
        from PIL import Image
        import io
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                img_bytes = await resp.read()
        img = Image.open(io.BytesIO(img_bytes))
        return imagehash.phash(img)
    except Exception:
        return None
```

### Merge Gate Logic

```python
def resolve(self, entities: list[ProfileEntity]) -> ProfileEntity:
    if not entities:
        return ProfileEntity(seed="", seed_type="UNKNOWN")
    if len(entities) == 1:
        return entities[0]  # Single source, no merge

    # Check independent sources
    all_sources = set()
    for e in entities:
        all_sources.update(e.sources)
    if len(all_sources) < 2:
        return entities[0]  # Only 1 source across all — no merge

    # Proceed with merge
    merged = entities[0]
    for other in entities[1:]:
        merged = merged.merge(other)  # uses ProfileEntity.merge() from Story 9.1
    return merged
```

### Dependencies

- `jellyfish` — thêm vào `requirements.txt` (optional dep, graceful skip)
- `imagehash` + `Pillow` — thêm vào `requirements.txt` (optional dep, graceful skip)
- `ProfileEntity.merge()` từ Story 9.1 — required

### File Locations

| File | Action |
|------|--------|
| `Core/engine/entity_resolver.py` | CREATE |
| `tests/engine/test_entity_resolver.py` | CREATE |
| `requirements.txt` | MODIFY — thêm `jellyfish`, `imagehash`, `Pillow` (optional) |

### References

- `ProfileEntity.merge()`: `Core/models/profile_entity.py` (Story 9.1)
- PRD FR19-FR23 (Golden Record merge, confidence, merge gate)
- jellyfish: https://github.com/jamesturk/jellyfish
- imagehash: https://github.com/JohannesBuchner/imagehash

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
- Bug: `_dedup_names_by_similarity()` chạy SAU `ProfileEntity.merge()` → merge() đã dedup bằng exact value, chỉ còn 1 entry → Jaro-Winkler không có gì để so sánh → confidence boost không được apply.
  Fix: Collect `all_names` từ tất cả entities TRƯỚC khi gọi `merge()`, chạy `_dedup_names_by_similarity()` trên combined list, sau đó override `merged.real_names`.

### Completion Notes List
- `EntityResolver.resolve()` — async, merge gate (FR23): ≥ 2 independent sources required
- `_names_similar()` — Jaro-Winkler via jellyfish, fallback to exact match (case-insensitive) nếu import fail
- `_dedup_names_by_similarity()` — chạy trên combined names TRƯỚC merge để có đủ entries cho comparison + boost
- `_avatar_hash()` — async helper, catch all exceptions silently; returns None on any failure
- `_apply_avatar_phash()` — pHash comparison, boost confidence bằng 0.15 nếu diff ≤ 10
- Confidence recalculation sau post-processing (sau khi names đã boosted)
- LOW_CONFIDENCE flag: `"⚠ LOW_CONFIDENCE"` appended vào sources nếu confidence < 0.5, deduplicated
- 19 tests, 100% pass

### File List
- `Core/engine/entity_resolver.py` (created)
- `tests/engine/test_entity_resolver.py` (created)
- `requirements.txt` (modified — added jellyfish, imagehash, Pillow)
