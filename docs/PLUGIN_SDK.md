# Plugin SDK — Developer Guide

This document describes how to write, register, test, and ship new OSINT
plugins for Mr.Holmes. It is the single reference for the plugin system
introduced in **Epic 7** and extended through **Epic 9**.

---

## 1. Overview

A **plugin** is a self-contained module that queries a single external
intelligence source (an API, a website, a DNS resolver, a CLI tool, etc.)
and returns a normalized result. Plugins are the building blocks of the
modern Mr.Holmes scan pipeline.

### Where plugins fit in the pipeline

```
                        ┌──────────────────────────────┐
   user input ───────▶  │  PluginManager.run_all()      │
   (target, type)       │  ┌────────┐ ┌────────┐ ...    │
                        │  │Plugin A│ │Plugin B│        │
                        │  └───┬────┘ └───┬────┘        │
                        └──────┼──────────┼─────────────┘
                               │          │
                          PluginResult  PluginResult
                               │          │
                               ▼          ▼
                        ┌──────────────────────────────┐
                        │  ScanResultCollector /        │
                        │  RecursiveProfiler /          │
                        │  EntityResolver               │
                        └──────────────────────────────┘
                               │
                               ▼
                        Reports (JSON / SQLite / PDF)
```

- The **PluginManager** discovers plugins, instantiates them, and runs
  `check()` on all of them **concurrently** with a shared `aiohttp`
  session for connection pooling.
- The **RecursiveProfiler / StagedProfiler** (Epic 8/9) runs plugins in
  stages, extracts *clues* from each result, and feeds those clues back
  into the next stage (breadth-first identity expansion).
- Each plugin is **independent**: it decides which `target_type`s it
  supports, whether it needs an API key, and how to degrade gracefully
  when a dependency is missing.

### Key files

| File | Purpose |
|------|---------|
| `Core/plugins/base.py` | `IntelligencePlugin` Protocol + `PluginResult` dataclass |
| `Core/plugins/manager.py` | `PluginManager` — discovery, registration, concurrent execution, caching |
| `Core/plugins/*.py` | Concrete plugin implementations (GitHub, HIBP, Shodan, DNS, …) |
| `Core/cache/plugin_cache.py` | Optional SQLite-backed result cache (transparent to plugins) |

---

## 2. The Plugin Protocol

Every plugin must implement the `IntelligencePlugin` Protocol defined in
`Core/plugins/base.py`. Because it is a `typing.Protocol`, plugins do
**not** need to inherit from a base class — they only need to provide the
required attributes and methods (structural / duck typing). In practice,
most plugins inherit from `IntelligencePlugin` for documentation and IDE
support, but it is not required.

### Required interface

```python
class IntelligencePlugin(Protocol):
    @property
    def name(self) -> str:
        """Identifier for the plugin (e.g. 'HaveIBeenPwned')."""
        ...

    @property
    def requires_api_key(self) -> bool:
        """Whether the plugin needs an API key to function."""
        ...

    async def check(self, target: str, target_type: str) -> PluginResult:
        """Run the plugin against the given target."""
        ...
```

### Optional Epic 9 additions (backward compatible)

These attributes are **not** required by the Protocol, but the staged
profiler and CLI use them when present. Existing plugins that omit them
default to safe values.

| Attribute | Type | Default | Meaning |
|-----------|------|---------|---------|
| `stage` | `int` | `1` (via `getattr(plugin, 'stage', 1)`) | Enrichment stage: `1` = primary/legacy, `2` = identity expansion, `3` = deep enrichment |
| `tos_risk` | `str` | `"safe"` | Terms-of-service risk level: `"safe"`, `"tos_risk"`, or `"ban_risk"` — used by the CLI ToS summary |
| `extract_clues(result)` | `method` | none | Returns `list[tuple[str, str]]` of `(value, target_type)` clues for recursive profiling |

### `name`

A short, human-readable identifier. It is used for:

- De-duplication in `PluginManager.register()` (plugins with a duplicate
  name are silently skipped).
- Cache key construction: `"{name}:{TARGET_TYPE}:{target}"`.
- Report output and CLI display.

### `requires_api_key`

When `True`, the CLI / wizard will prompt the user to configure the
corresponding environment variable. The plugin itself is still
responsible for reading the key (typically via `os.getenv(...)`) and for
returning a clear `error_message` when the key is missing.

### `stage`

Controls **when** the plugin runs in the staged pipeline:

| Stage | Role | Examples |
|-------|------|----------|
| `1` | Primary / legacy — runs on the seed target and during BFS | HIBP, Shodan, LeakLookup, SearxNG, DNS |
| `2` | Identity expansion — runs on the seed, extracts new clues | Holehe, Maigret, GitHub |
| `3` | Deep enrichment — runs on clues discovered by stage 2 | Numverify, Hunter |

> **Note:** `DNSResolverPlugin` sets `stage = 1` even though it resolves
> domains, because it must run *inside* the RecursiveProfiler BFS on
> discovered `DOMAIN` clues.

### `target_types`

There is **no** formal `target_types` property in the Protocol. Instead,
each plugin validates `target_type` inside `check()` and returns a
failure `PluginResult` for types it does not support. The canonical
target type strings (always compared with `.upper()`) are:

| `target_type` | Example target |
|---------------|----------------|
| `USERNAME` | `torvalds` |
| `EMAIL` | `foo@bar.com` |
| `PHONE` | `+84928881690` |
| `DOMAIN` | `example.com` |
| `IP` | `192.168.1.1` |

### `check(target, target_type) -> PluginResult`

The core method. It is `async` so that the manager can run all plugins
concurrently. Contract:

- **Never raise.** Catch all exceptions and return a `PluginResult` with
  `is_success=False` and a descriptive `error_message`. The manager
  wraps calls in `_safe_execute()` as a safety net, but plugins should
  handle their own errors for better messages.
- Validate `target_type` first and bail out early for unsupported types.
- Use the shared HTTP session via `get_http_session(self)` (see
  [Best practices](#8-best-practices)) so the manager can pool
  connections.
- Return a `PluginResult` — see the next section.

---

## 3. The PluginResult Model

`PluginResult` is a frozen-ish dataclass defined in
`Core/plugins/base.py`:

```python
@dataclass
class PluginResult:
    plugin_name: str
    is_success: bool
    data: dict[str, Any]
    error_message: str | None = None
```

| Field | Type | Meaning |
|-------|------|---------|
| `plugin_name` | `str` | The `name` of the plugin that produced this result. Set it to `self.name`. |
| `is_success` | `bool` | `True` when the plugin got a definitive answer (even a "not found" 404 can be a success). `False` on errors, unsupported types, missing keys, network failures. |
| `data` | `dict[str, Any]` | Normalized payload. Structure is plugin-specific, but should be JSON-serializable. Empty dict `{}` on failure. |
| `error_message` | `str \| None` | Human-readable explanation when `is_success=False`. `None` on success. |

### Success vs. failure semantics

A common source of confusion: **a 404 "not found" is a success**, not a
failure. The plugin successfully queried the API and the API said "no
data". Reserve `is_success=False` for situations where the plugin could
not complete its job:

- Unsupported `target_type`
- Missing API key
- Network error / timeout
- HTTP 401 / 403 / 429 / 5xx
- Malformed response

Example from `hibp.py` — a 404 means "no breaches found", which is a
success with `breach_count: 0`:

```python
if response.status == 404:
    return PluginResult(
        plugin_name=self.name,
        is_success=True,
        data={"breach_count": 0, "breach_names": [], ...},
    )
```

### The `data` dict

There is no enforced schema for `data`, but good plugins follow these
conventions:

- Use **snake_case** keys.
- Include a boolean `data_found` flag when the distinction between
  "queried successfully, nothing found" and "found results" matters.
- Return **lists** for multi-valued fields (e.g. `emails`, `ips`,
  `breach_names`) rather than comma-separated strings.
- Avoid embedding raw API responses — normalize into the fields the
  downstream collectors and report writers expect.

---

## 4. Step-by-step: Creating a New Plugin

### Step 1 — Create the module

Add a new file under `Core/plugins/`, e.g. `Core/plugins/my_source.py`.
The filename is arbitrary (the manager discovers by module, not by
filename), but by convention it matches the plugin's `name` in
lowercase.

### Step 2 — Implement the interface

```python
"""Core/plugins/my_source.py — MySource intelligence plugin."""
from __future__ import annotations

import os
import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session


class MySourcePlugin(IntelligencePlugin):
    name: str = "MySource"
    requires_api_key: bool = True
    stage: int = 2
    tos_risk: str = "safe"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    async def check(self, target: str, target_type: str) -> PluginResult:
        ...
```

Key implementation rules:

- The class **must** have `name`, `requires_api_key`, and `check` as
  attributes — the manager duck-types on these.
- The constructor **must** be callable with no arguments
  (`MySourcePlugin()`) because `discover_plugins()` instantiates with
  `obj()`. Accept an optional `api_key=""` parameter for testing and
  explicit injection, but default it to empty.
- Read the API key from `os.getenv("MH_MYSOURCE_API_KEY", "")` inside
  `check()` (or a helper), not at import time.

### Step 3 — Registration (auto-discovery)

You do **not** need to edit any registry. `PluginManager.discover_plugins()`
scans every submodule of `Core.plugins` and registers any class that has
`name`, `requires_api_key`, and `check` attributes (see
[Plugin discovery](#7-plugin-discovery)). Simply placing the file in
`Core/plugins/` is enough.

The manager skips `Core.plugins.base` and `Core.plugins.manager`, so
never put a concrete plugin in those modules.

### Step 4 — Add the API key to `.env.example`

If your plugin `requires_api_key`, document the environment variable in
`.env.example` so users know to configure it:

```env
# MySource — example intelligence lookup (https://mysource.example)
MH_MYSOURCE_API_KEY=
```

Follow the naming convention `MH_{SOURCE}_API_KEY` (or `MH_{SOURCE}_TOKEN`
for tokens like GitHub's).

### Step 5 — Write tests

Add `tests/plugins/test_my_source.py` (see
[Testing plugins](#6-testing-plugins)).

### Step 6 — Verify

```bash
python3.10 -m pytest tests/plugins/test_my_source.py -v
python3.10 -m pytest tests/ --tb=no -q
```

---

## 5. Example: Full Plugin Implementation

Below is a complete, self-contained plugin that looks up a username on a
hypothetical API. It demonstrates all the conventions: target-type
validation, API-key handling, shared session usage, rate-limit handling,
graceful degradation, and clue extraction.

```python
"""Core/plugins/example_lookup.py — Example intelligence plugin.

Demonstrates the full plugin contract:
  - supports USERNAME and EMAIL targets
  - optional API key (works without one at lower rate limits)
  - stage 2 identity expansion with clue extraction
  - graceful degradation on missing key / network error / rate limit
"""
from __future__ import annotations

import os
import asyncio
import time
from typing import Any

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session

_BASE_URL = "https://api.example-lookup.com/v1"
_TIMEOUT = aiohttp.ClientTimeout(total=15)


class ExampleLookupPlugin(IntelligencePlugin):
    """Example intelligence plugin. stage=2, tos_risk='safe'."""

    name: str = "ExampleLookup"
    requires_api_key: bool = False          # works without a key (lower limits)
    stage: int = 2                          # identity expansion
    tos_risk: str = "safe"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    # ── helpers ───────────────────────────────────────────────────────

    def _get_key(self) -> str:
        return self.api_key or os.getenv("MH_EXAMPLE_LOOKUP_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        h = {"User-Agent": "MrHolmes-OSINT"}
        key = self._get_key()
        if key:
            h["Authorization"] = f"Bearer {key}"
        return h

    # ── IntelligencePlugin protocol ────────────────────────────────────

    async def check(self, target: str, target_type: str) -> PluginResult:
        t = target_type.upper()
        if t == "USERNAME":
            return await self._lookup(target, by="username")
        if t == "EMAIL":
            return await self._lookup(target, by="email")
        return PluginResult(
            plugin_name=self.name,
            is_success=False,
            data={},
            error_message=f"ExampleLookup does not support target type: {target_type}",
        )

    async def _lookup(self, target: str, by: str) -> PluginResult:
        url = f"{_BASE_URL}/lookup?{by}={target}"
        try:
            async with get_http_session(self) as session:
                async with session.get(url, headers=self._headers(),
                                       timeout=_TIMEOUT) as resp:
                    if resp.status == 404:
                        # definitive "not found" → success with empty data
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={"found": False, "profiles": []},
                        )
                    if resp.status == 401:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="401 Unauthorized — invalid MH_EXAMPLE_LOOKUP_API_KEY.",
                        )
                    if resp.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="429 Rate limit exceeded for ExampleLookup.",
                        )
                    if resp.status != 200:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"ExampleLookup API error: HTTP {resp.status}",
                        )
                    payload: dict[str, Any] = await resp.json(content_type=None)
        except Exception as exc:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"ExampleLookup network error: {exc}",
            )

        profiles = payload.get("profiles", [])
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "found": len(profiles) > 0,
                "profiles": profiles,
                "emails": [p.get("email") for p in profiles if p.get("email")],
                "real_names": [p.get("name") for p in profiles if p.get("name")],
            },
        )

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """Emit emails and names as clues for the next pipeline stage."""
        if not result.is_success or not result.data:
            return []
        clues: list[tuple[str, str]] = []
        clues += [(e, "EMAIL") for e in result.data.get("emails", [])]
        clues += [(n, "USERNAME") for n in result.data.get("real_names", [])]
        return clues
```

### How the manager runs it

```python
from Core.plugins.manager import PluginManager

mgr = PluginManager()
mgr.discover_plugins()          # finds ExampleLookupPlugin automatically
results = await mgr.run_all("torvalds", "USERNAME")
for r in results:
    print(r.plugin_name, r.is_success, r.data)
```

---

## 6. Testing Plugins

Plugin tests live in `tests/plugins/` and follow the mock-based HTTP
pattern established in `tests/conftest.py`. The project migrated away
from `aioresponses` (incompatible with aiohttp 3.11+) and uses
`unittest.mock` instead.

### Minimal test skeleton

```python
"""tests/plugins/test_my_source.py"""
import pytest
from unittest.mock import AsyncMock, patch

from Core.plugins.my_source import MySourcePlugin
from Core.plugins.base import PluginResult


@pytest.mark.asyncio
async def test_mysource_unsupported_type():
    plugin = MySourcePlugin()
    result = await plugin.check("foo", "PHONE")
    assert result.is_success is False
    assert "PHONE" in result.error_message


@pytest.mark.asyncio
async def test_mysource_missing_api_key():
    plugin = MySourcePlugin(api_key="")
    with patch.dict("os.environ", {}, clear=True):
        result = await plugin.check("foo@bar.com", "EMAIL")
    assert result.is_success is False
    assert "API Key" in result.error_message or "key" in result.error_message.lower()
```

### Mocking HTTP with the conftest helpers

`tests/conftest.py` provides `make_mock_response()` and
`make_mock_session()` for building fake `aiohttp` responses. For plugins
that use `get_http_session(self)`, patch the session on the plugin
instance directly:

```python
@pytest.mark.asyncio
async def test_mysource_success(mock_session):
    from tests.conftest import make_mock_response
    mock_session.get.return_value = make_mock_response(
        status=200,
        payload={"profiles": [{"name": "Jane", "email": "jane@x.com"}]},
    )
    plugin = MySourcePlugin(api_key="fake-key")
    plugin._shared_session = mock_session          # injected shared session
    result = await plugin.check("jane", "USERNAME")
    assert result.is_success is True
    assert result.data["found"] is True
```

### Patterns to test

For every plugin, cover at least:

1. **Unsupported target type** → `is_success=False`, descriptive message.
2. **Missing API key** (if `requires_api_key`) → graceful failure.
3. **Happy path** (200 with data) → `is_success=True`, normalized `data`.
4. **Not-found path** (404) → `is_success=True` with empty/`found=False`
   data (this is the success-vs-failure semantic — see §3).
5. **Error paths** — 401, 403, 429, 5xx, and a network exception.
6. **`extract_clues`** — returns correct `(value, type)` tuples on
   success and `[]` on failure.
7. **Rate-limit handling** (if the plugin implements it) — verify it
   waits/retries or bails out correctly.

Run a single plugin's tests:

```bash
python3.10 -m pytest tests/plugins/test_my_source.py -v
```

---

## 7. Plugin Discovery

`PluginManager.discover_plugins()` (in `Core/plugins/manager.py`) uses
`pkgutil.iter_modules` to enumerate every submodule of the
`Core.plugins` package and `importlib.import_module` to load each one.

For each loaded module it inspects all classes via
`inspect.getmembers(module, inspect.isclass)` and applies a **duck-type
check**:

```python
hasattr(obj, "name") and hasattr(obj, "requires_api_key") and hasattr(obj, "check")
and obj is not IntelligencePlugin
```

Classes that pass are instantiated with `obj()` (no arguments) and
registered via `register()`, which de-duplicates by `name`.

### What this means for plugin authors

- **No registration code needed.** Drop the file in `Core/plugins/` and
  it is picked up on the next `discover_plugins()` call.
- **The constructor must be zero-argument callable.** Use default
  parameters (`def __init__(self, api_key: str = "")`).
- **Avoid import-time side effects.** Module import happens during
  discovery; do not open files, make network calls, or read env vars at
  module top level. Do all of that inside `check()` or lazily.
- **Skip modules `base` and `manager`** are hard-coded to be skipped;
  never put a concrete plugin class in them.
- **Import errors are tolerated.** If a plugin module fails to import
  (e.g. missing optional dependency), the manager logs a warning and
  continues with the rest. This is how plugins like `holehe` and
  `maigret` degrade gracefully when their pip package is absent.

### Manual registration (advanced)

You can bypass auto-discovery and register plugins explicitly — useful
in tests or when you want to inject a configured instance:

```python
mgr = PluginManager()
mgr.register(GitHubPlugin(api_key="ghp_..."))
mgr.register(HIBPPlugin(api_key="..."))
```

---

## 8. Best Practices

### Error handling

- **Never let `check()` raise.** Wrap all I/O in `try/except` and return
  a `PluginResult` with `is_success=False`. The manager's
  `_safe_execute()` is a last-resort safety net, but a plugin that
  raises produces a generic `"Plugin Exception: ..."` message instead of
  a useful one.
- **Differentiate HTTP errors.** Return specific messages for 401
  (bad key), 403 (forbidden / rate limit), 404 (not found → success!),
  429 (rate limited), and 5xx. See `hibp.py` and `github.py` for
  examples.
- **Guard against unexpected response shapes.** Check
  `isinstance(payload, dict)` before calling `.get()` on it — APIs
  occasionally return `null` or HTML error pages.

### Rate limiting

- If the upstream API enforces a rate limit, implement a client-side
  throttle. `HIBPPlugin` uses a class-level `asyncio.Lock` plus a
  `_last_request_time` timestamp to enforce "1 request per 1.5 seconds"
  globally.
- For APIs that return `X-RateLimit-Reset` headers (like GitHub), sleep
  until the reset time and retry once — but cap the maximum wait so a
  stuck scan does not hang forever (`github.py` uses `_MAX_RATE_WAIT =
  60`).
- On `429`, return a clear `error_message` rather than silently
  retrying in a loop.

### Graceful degradation

- **Missing optional dependencies:** wrap the import in a `try/except
  ImportError` at module top and have `check()` return
  `is_success=False` with a message like `"holehe not installed. pip
  install holehe"`. The manager will still discover and register the
  plugin; it just fails cleanly at runtime. (See `holehe.py` /
  `maigret.py`.)
- **Missing API key:** return a helpful message naming the exact env
  var to set (e.g. `"Please configure MH_HIBP_API_KEY."`).
- **Partial data:** if one of several sub-requests fails but others
  succeed, return the partial data and set a flag like
  `data["_events_partial"] = True` (as `github.py` does when the events
  endpoint is rate-limited).

### HTTP sessions

- Use the `get_http_session(self)` async context manager from
  `base.py` instead of creating your own `aiohttp.ClientSession()`. The
  manager injects a shared session (`plugin._shared_session`) before
  calling `check()` so that all plugins reuse one connection pool. When
  a plugin is used standalone (no manager), `get_http_session` creates
  and closes a fresh session automatically — fully backward compatible.
- Always pass a `timeout` to requests (`aiohttp.ClientTimeout(total=N)`)
  so a slow API cannot stall the whole concurrent batch.

### Caching

- Caching is **transparent** to plugins. `PluginManager._safe_execute()`
  checks the optional `PluginCache` before calling `check()` and stores
  successful results afterwards. You do not need to do anything.
- Only results with `is_success=True` **and** non-empty `data` are
  cached; failures are never cached.
- If your plugin can normalize a target (e.g. strip `+` from a phone
  number), implement a `normalize_target(target)` method. The manager
  calls it when building the cache key so that different surface formats
  share one entry.

### Clue extraction (stage 2/3 plugins)

- Implement `extract_clues(result) -> list[tuple[str, str]]` if your
  plugin discovers new identifiers (emails, usernames, IPs, domains).
  The `RecursiveProfiler` uses these to expand the investigation
  breadth-first.
- Return `[]` on failure or when no clues were found.
- Each tuple is `(value, TARGET_TYPE)` where `TARGET_TYPE` is one of the
  canonical strings (`EMAIL`, `USERNAME`, `IP`, `DOMAIN`, `PHONE`).

### General style

- Use `from __future__ import annotations` so `str | None` type hints
  work on Python 3.10.
- Keep the module docstring up to date — it is the first thing users see
  when reading `Core/plugins/`.
- Define module-level constants (`_BASE_URL`, `_TIMEOUT`) in
  UPPER_SNAKE_CASE with a leading underscore to mark them private.
- Prefer class-level attributes for `name`, `requires_api_key`, `stage`,
  and `tos_risk` (as `GitHubPlugin` does) over `@property` — it is
  simpler and the duck-type check works either way. Use `@property` only
  when the value must be computed (as `HIBPPlugin` does).

---

## Appendix: Existing Plugins Reference

| Plugin | File | `stage` | `requires_api_key` | Target types | Notes |
|--------|------|---------|--------------------|--------------|-------|
| GitHub | `github.py` | 2 | `False` (optional token) | USERNAME, EMAIL | Rate-limit aware, extracts emails + real names from commit history |
| HaveIBeenPwned | `hibp.py` | 1 | `True` | EMAIL | 1.5s global throttle via `asyncio.Lock` |
| DNSResolver | `dns_resolver.py` | 1 | `False` | DOMAIN | Resolves DOMAIN → IP, filters CDN noise, emits IP clues |
| Shodan | `shodan.py` | 1 | `True` | IP | Port/scan/vulnerability lookup |
| LeakLookup | `leak_lookup.py` | 1 | `True` | EMAIL, USERNAME | Breach data lookup |
| Numverify | `numverify.py` | 3 | `True` | PHONE | Phone number validation/enrichment |
| SearxNG | `searxng.py` | 1 | `False` | (search) | OSINT meta-search |
| Holehe | `holehe.py` | 2 | `False` | EMAIL | Degrades gracefully if `holehe` pip package missing |
| Maigret | `maigret.py` | 2 | `False` | USERNAME | Degrades gracefully if `maigret` pip package missing |

Use these as templates when building your own plugin — `github.py` and
`dns_resolver.py` are the most complete reference implementations.
