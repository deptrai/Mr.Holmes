# Story 9.15: Cross-Platform Bridge

Status: ready-for-dev

## Story

As the identity resolution engine,
I want to bridge identities across platforms by comparing avatar hashes and recovery info overlap,
so that the system can confirm that two different usernames belong to the same person.

## Acceptance Criteria

1. `CrossPlatformBridge` class tại `Core/engine/cross_platform_bridge.py`:
   - `find_bridges(profiles: list[dict]) -> list[BridgeMatch]` — nhận list of profile dicts (từ `PluginResult.data["profiles"]`), return confirmed identity bridges

2. `BridgeMatch` dataclass:
   - `source_platform: str`
   - `target_platform: str`
   - `confidence: float` (0.0-1.0)
   - `evidence: list[str]` — e.g. `["avatar_hash_match: similarity=0.95", "recovery_email_overlap"]`

3. Bridge signals:
   - **Avatar hash match** (pHash, distance ≤ 10): confidence += 0.4
   - **Recovery email overlap** (same email appears in 2+ profiles): confidence += 0.35
   - **Name similarity** (Jaro-Winkler ≥ 0.85 giữa 2 profile names): confidence += 0.25
   - Minimum confidence để return bridge: ≥ 0.5 (tức là ít nhất 2 signals)

4. Bridge không tự merge entities — chỉ return matches để `EntityResolver` quyết định merge:
   - `BridgeMatch` được inject vào `EntityResolver.resolve()` như additional evidence
   - Separation of concerns: bridge finds links, resolver merges

5. Optional deps graceful skip:
   - Nếu `imagehash`/`Pillow` không installed → skip avatar hash signal
   - Nếu `jellyfish` không installed → skip name similarity, dùng exact match

6. Unit tests tại `tests/engine/test_cross_platform_bridge.py` ≥ 80% coverage:
   - Test 2 profiles cùng avatar hash → BridgeMatch với evidence
   - Test 2 profiles cùng recovery email → BridgeMatch
   - Test 2 profiles không có signal chung → không có BridgeMatch
   - Test single profile → empty result
   - Test confidence threshold (chỉ 1 weak signal → below 0.5 → not returned)

## Tasks / Subtasks

- [ ] Task 1: Tạo `BridgeMatch` dataclass (AC: 2)
- [ ] Task 2: Tạo `CrossPlatformBridge` class (AC: 1)
- [ ] Task 3: Implement avatar hash comparison (AC: 3)
  - [ ] Reuse `_avatar_hash()` helper từ Story 9.10 (EntityResolver) nếu có, hoặc implement mới
- [ ] Task 4: Implement recovery email overlap detection (AC: 3)
- [ ] Task 5: Implement name similarity check (AC: 3)
- [ ] Task 6: Integrate với `EntityResolver` — update `resolve()` để accept optional bridges (AC: 4)
- [ ] Task 7: Viết unit tests (AC: 6)

## Dev Notes

### Algorithm Sketch

```python
@dataclass
class BridgeMatch:
    source_platform: str
    target_platform: str
    confidence: float
    evidence: list[str]

class CrossPlatformBridge:
    async def find_bridges(self, profiles: list[dict]) -> list[BridgeMatch]:
        matches = []
        for i, p1 in enumerate(profiles):
            for p2 in profiles[i+1:]:
                confidence = 0.0
                evidence = []

                # Avatar hash
                h1 = await _avatar_hash(p1.get("avatar_url", ""))
                h2 = await _avatar_hash(p2.get("avatar_url", ""))
                if h1 and h2 and abs(h1 - h2) <= 10:
                    confidence += 0.4
                    evidence.append(f"avatar_hash_match (dist={abs(h1-h2)})")

                # Name similarity
                name1, name2 = p1.get("name", ""), p2.get("name", "")
                if name1 and name2 and _names_similar(name1, name2):
                    confidence += 0.25
                    evidence.append(f"name_similarity: '{name1}' ~ '{name2}'")

                if confidence >= 0.5:
                    matches.append(BridgeMatch(
                        source_platform=p1.get("site", ""),
                        target_platform=p2.get("site", ""),
                        confidence=min(confidence, 1.0),
                        evidence=evidence,
                    ))
        return matches
```

### Reuse

`_avatar_hash()` và `_names_similar()` nên được extract thành module-level helpers trong `Core/engine/` (e.g., `Core/engine/similarity_utils.py`) để tái sử dụng giữa `EntityResolver` và `CrossPlatformBridge` — tránh duplicate code.

### File Locations

| File | Action |
|------|--------|
| `Core/engine/cross_platform_bridge.py` | CREATE |
| `Core/engine/similarity_utils.py` | CREATE — shared helpers (`_avatar_hash`, `_names_similar`) |
| `Core/engine/entity_resolver.py` | MODIFY — import và sử dụng `similarity_utils` |
| `tests/engine/test_cross_platform_bridge.py` | CREATE |

### References

- `Core/engine/entity_resolver.py` (Story 9.10)
- PRD: Cross-Platform Bridge concept (Identity Synthesis section)

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
- `Core/engine/cross_platform_bridge.py` (created)
- `Core/engine/similarity_utils.py` (created)
- `Core/engine/entity_resolver.py` (modified)
- `tests/engine/test_cross_platform_bridge.py` (created)
