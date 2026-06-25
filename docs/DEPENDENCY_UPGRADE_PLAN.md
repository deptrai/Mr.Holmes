# Dependency Upgrade Plan

## Status: Proposed
## Date: 2026-06-26

---

## 1. Context

Mr.Holmes has several dependency version caps that block security updates
and feature improvements. These caps were introduced to maintain test
stability with `aioresponses` and `pytest-asyncio`, but they prevent
upgrading to newer versions of `aiohttp` and other libraries.

**Current caps:**

```txt
# requirements.txt
aiohttp>=3.9.0,<3.11

# requirements-dev.txt
pytest-asyncio>=0.23,<0.24
aioresponses>=0.7.6,<0.7.7
```

**Problem:** Installing `maigret` (which requires `aiohttp>=3.12.14`) upgrades
aiohttp past the cap, breaking `aioresponses`-based tests. This was observed
during the review session — 34 tests failed after maigret installation.

---

## 2. Affected Dependencies

| Dependency | Current Cap | Latest Stable | Impact of Cap |
|------------|-------------|---------------|---------------|
| `aiohttp` | `<3.11` | 3.14.1 | Blocks security fixes, blocks maigret 0.6+ |
| `pytest-asyncio` | `<0.24` | 0.24+ | Blocks pytest-asyncio improvements |
| `aioresponses` | `<0.7.7` | 0.7.7+ | Blocks aiohttp 3.11+ compatibility |

---

## 3. Upgrade Strategy

### Phase 1: aiohttp + aioresponses (HIGH priority)

**Goal:** Upgrade aiohttp to 3.11+ and aioresponses to latest compatible.

**Steps:**

1. **Check aioresponses compatibility:**
   - aioresponses 0.7.7+ may support aiohttp 3.11+
   - If not, consider alternatives:
     - `pytest-httpserver` — HTTP server mocking
     - `respx` — aiohttp/requests mocking (if supports 3.11+)
     - Direct `unittest.mock` patching of aiohttp.ClientSession

2. **Migrate test mocks:**
   - Update all `aioresponses` usage in tests to new API (if needed)
   - Test with aiohttp 3.11+ and aioresponses latest

3. **Update requirements:**
   ```txt
   # requirements.txt
   aiohttp>=3.11.0,<4.0.0

   # requirements-dev.txt
   aioresponses>=0.7.7
   ```

4. **Run full test suite** to verify all tests pass.

5. **Update AGENTS.md** with new dependency versions.

**Estimated effort:** 1-2 sprints

### Phase 2: pytest-asyncio (MEDIUM priority)

**Goal:** Upgrade pytest-asyncio to 0.24+.

**Steps:**

1. **Review breaking changes:**
   - pytest-asyncio 0.24 changed the event-loop fixture API
   - Tests using `event_loop` fixture may need updates

2. **Migrate test fixtures:**
   - Replace deprecated `event_loop` fixture usage
   - Update `asyncio_mode` in `pytest.ini` if needed

3. **Update requirements:**
   ```txt
   # requirements-dev.txt
   pytest-asyncio>=0.24
   ```

4. **Run full test suite** to verify.

**Estimated effort:** 1 sprint

### Phase 3: Other dependencies (LOW priority)

**Goal:** Remove unnecessary caps on other dependencies.

- Review all `<` caps in requirements.txt and requirements-dev.txt
- Test with latest stable versions
- Remove caps where possible, or document why they're needed

**Estimated effort:** 0.5 sprint

---

## 4. Test Migration Guide

### aioresponses → mock-based approach (if needed)

If aioresponses cannot support aiohttp 3.11+, migrate tests to use
`unittest.mock` directly:

```python
# Before (aioresponses)
from aioresponses import aioresponses

async def test_hibp():
    with aioresponses() as m:
        m.get("https://haveibeenpwned.com/api/v3/breachedaccount/test",
              status=200, payload=[{"Name": "Adobe"}])
        result = await plugin.check("test", "email")
        assert result.is_success

# After (mock-based)
from unittest import mock

async def test_hibp():
    mock_resp = mock.AsyncMock()
    mock_resp.status = 200
    mock_resp.json = mock.AsyncMock(return_value=[{"Name": "Adobe"}])
    mock_resp.text = mock.AsyncMock(return_value='[{"Name": "Adobe"}]')

    with mock.patch("aiohttp.ClientSession.get", return_value=mock_resp):
        result = await plugin.check("test", "email")
        assert result.is_success
```

### pytest-asyncio 0.24 migration

```python
# Before (0.23)
@pytest.mark.asyncio
async def test_example(event_loop):
    await asyncio.sleep(0.1)

# After (0.24)
@pytest.mark.asyncio
async def test_example():
    await asyncio.sleep(0.1)
```

---

## 5. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Test breakage after upgrade | Migrate tests incrementally, one file at a time |
| Production code breakage | Test with real API calls before merging |
| Dependency conflicts | Use `pip-audit` to check for conflicts |
| Rollback needed | Keep old requirements.txt in git history for easy rollback |

---

## 6. Success Criteria

- [ ] aiohttp upgraded to 3.11+ with all tests passing
- [ ] aioresponses upgraded or replaced with mock-based approach
- [ ] pytest-asyncio upgraded to 0.24+ with all tests passing
- [ ] No unnecessary version caps in requirements files
- [ ] Full test suite passes (1107+ tests)
- [ ] maigret and holehe work with upgraded dependencies

---

## 7. Immediate Workaround

Until the upgrade is complete, use this approach to avoid conflicts:

```bash
# Install requirements first (pins aiohttp <3.11)
python3.10 -m pip install -r requirements.txt -r requirements-dev.txt

# Then install maigret with --no-deps to avoid aiohttp upgrade
python3.10 -m pip install --no-deps maigret

# Or accept the aiohttp upgrade and skip aioresponses-based tests
python3.10 -m pip install maigret
python3.10 -m pytest tests/ --ignore=tests/plugins --ignore=tests/engine/test_async_search.py
```

**Note:** The current state (aiohttp 3.10.11) is the stable configuration.
Do not upgrade aiohttp until the test migration is complete.
