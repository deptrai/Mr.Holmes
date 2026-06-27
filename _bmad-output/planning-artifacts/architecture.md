# Mr.Holmes 2.0 — Tài liệu Kiến trúc (MCP-Powered OSINT Tool Collection)

Ngày: 2026-06-26
Phiên bản: 2.0-draft
Tác giả: Winston (System Architect)

---

## 1. Tổng quan Kiến trúc (Architecture Overview)

Mr.Holmes 2.0 biến công cụ OSINT đơn thể hiện tại thành một **bộ sưu tập công cụ MCP (Model Context Protocol)**, trong đó **Claude Code** đóng vai trò AI orchestrator. Mr.Holmes chỉ expose các tool thu thập dữ liệu qua MCP server; Claude Code gọi tool, nhận kết quả, suy luận, và quyết định bước tiếp theo.

### 1.1 Sơ đồ kiến trúc (ASCII)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Claude Code (AI Orchestrator)                │
│  - Nhận yêu cầu điều tra từ user                                     │
│  - Lập kế hoạch: gọi tool nào, theo thứ tự nào                       │
│  - Suy luận trên kết quả, đề xuất giả thuyết, quyết định tool tiếp   │
│  - Tổng hợp thành báo cáo cuối                                       │
└───────────────▲───────────────────────────────────▲──────────────────┘
                │ MCP Protocol (stdio / SSE)         │
                │ JSON-RPC 2.0                       │
┌───────────────┴───────────────────────────────────┴──────────────────┐
│                   Mr.Holmes MCP Server (mcp Python SDK)              │
│  Core/mcp/server.py                                                  │
│  - Đăng ký ~25 tools (username, email, phone, domain, person, ...)   │
│  - Mỗi tool → wrapper gọi PluginManager / StagedProfiler / Evidence  │
│  - Auth: API key (MH_MCP_TOKEN), rate limiting per-tool              │
└───────┬────────────┬───────────────┬───────────────┬─────────────────┘
        │            │               │               │
┌───────▼──────┐ ┌───▼──────────┐ ┌──▼───────────┐ ┌─▼──────────────┐
│ Plugin Layer │ │ Engine Layer │ │ Evidence     │ │ Browser Layer  │
│ Core/plugins │ │ Core/engine  │ │ Store        │ │ Playwright     │
│  - hibp      │ │  - Staged    │ │ Core/        │ │ Core/browser/  │
│  - shodan    │ │    Profiler  │ │ reporting    │ │  - stealth ctx │
│  - holehe    │ │  - Entity    │ │  +evidence   │ │  - scrape      │
│  - maigret   │ │    Resolver  │ │  +hypothesis │ │  - bypass CF   │
│  - github    │ │              │ │              │ │                │
│  - searxng   │ │              │ │              │ │                │
│  - dns       │ │              │ │              │ │                │
│  - numverify │ │              │ │              │ │                │
└──────┬───────┘ └──────────────┘ └──────────────┘ └────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────────┐
│  Shared Infrastructure                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ PluginCache  │  │ ProxyManager │  │ Settings     │  │ Database │ │
│  │ Core/cache   │  │ Core/proxy   │  │ Core/config  │  │ SQLite   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Mô tả thành phần

| Thành phần | Vai trò | File hiện tại |
|---|---|---|
| **Claude Code** | AI orchestrator — reasoning, planning, gọi tool | (external) |
| **MCP Server** | Expose OSINT tools qua MCP protocol | `Core/mcp/server.py` (mới) |
| **Plugin Layer** | Các plugin OSINT (HIBP, Shodan, Maigret...) | `Core/plugins/` |
| **Engine Layer** | StagedProfiler (BFS), EntityResolver (golden record) | `Core/engine/` |
| **Evidence Store** | SQLite lưu kết quả điều tra có thể query/resume | `Core/reporting/` |
| **Browser Layer** | Playwright cho bot-detection bypass | `Core/browser/` (mới) |
| **PluginCache** | Cache kết quả plugin, giảm API call | `Core/cache/plugin_cache.py` |
| **ProxyManager** | Pool proxy, rotation, health check | `Core/proxy/manager.py` |
| **Settings** | Secrets (.env) + config (.ini) | `Core/config/settings.py` |
| **REST API** | FastAPI — secondary interface (giữ lại) | `Core/api/server.py` |
| **CLI** | Legacy interactive — secondary interface | `MrHolmes.py` |

---

## 2. Quyết định Thiết kế Chính (Key Design Decisions)

### 2.1 Tại sao MCP?

- **Chuẩn mở**: MCP là protocol chuẩn cho LLM-tool integration, không lock-in vào một vendor cụ thể.
- **Claude Code native**: Claude Code đã built-in MCP client, zero integration cost.
- **Structured I/O**: Mỗi tool có schema rõ ràng (input/output), Claude Code tự hiểu cách gọi.
- **Iterative reasoning**: Claude Code gọi tool → nhận kết quả → suy luận → gọi tool tiếp, thay vì batch-run tất cả plugin như hiện tại.

### 2.2 Tại sao KHÔNG build AI orchestrator nội bộ?

- **Chi phí bảo trì cao**: Phải duy trì prompt engineering, context window management, tool routing logic — tất cả Claude Code đã làm tốt hơn.
- **Lặp lại công sức**: Claude Code đã là một orchestrator xuất sắc; build thêm layer AI nội bộ = trùng lặp.
- **Phụ thuộc nhẹ hơn**: Phụ thuộc Claude Code (external, well-maintained) tốt hơn phụ thuộc vào codebase AI nội bộ tự viết.
- **Chi tiết thêm**: xem ADR-0010.

### 2.3 CLI/REST vẫn giữ, nhưng secondary

- CLI (`MrHolmes.py`) và REST API (`Core/api/server.py`) vẫn hoạt động cho backward compatibility và automation.
- MCP server là **primary interface** cho interactive investigation.
- REST API hữu ích cho integration với hệ thống khác (SIEM, dashboard).

---

## 3. Thiết kế MCP Server (MCP Server Design)

### 3.1 Công nghệ

- **Package**: `mcp` (Python SDK, `pip install mcp`)
- **Transport**: stdio (local, Claude Code mặc định) hoặc SSE (remote)
- **File**: `Core/mcp/server.py`

### 3.2 Định nghĩa tool

Mỗi tool đăng ký qua `@server.tool()` decorator:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mrholmes")

@mcp.tool()
async def search_username(username: str, sites: list[str] | None = None) -> dict:
    """Tìm username trên các site mạng xã hội.

    Args:
        username: Tên người dùng cần tìm.
        sites: Danh sách site cụ thể (optional). Mặc định quét tất cả.
    Returns:
        Dict với key "found" (list) và "not_found" (list).
    """
    ...
```

### 3.3 Request / Response format

- **Input**: JSON object, schema tự sinh từ type hints của Python.
- **Output**: JSON object, luôn có cấu trúc:
  ```json
  {
    "success": true,
    "data": { ... },
    "error": null,
    "metadata": { "plugin": "Maigret", "duration_ms": 3200, "cached": false }
  }
  ```
- **Error**: Khi tool fail, trả `success: false` + `error` message (không raise exception ra MCP layer).

### 3.4 Error handling

- Plugin exception → catch trong wrapper, trả `PluginResult(is_success=False, error_message=...)`.
- Timeout → trả error với `error_type: "timeout"`.
- Rate limited → trả error với `error_type: "rate_limited"`, gợi ý retry-after.
- Missing API key → trả error với `error_type: "missing_key"`, chỉ rõ env var cần set.

### 3.5 Auth & rate limiting

- Auth: token qua env `MH_MCP_TOKEN` (optional, cho remote SSE mode).
- Rate limiting: per-tool semaphore + PluginCache (TTL 24h, configurable qua `MH_CACHE_TTL`).
- Proxy: tự động dùng ProxyManager nếu enabled.

---

## 4. Kiến trúc Plugin (Plugin Architecture)

### 4.1 Plugin hiện tại → MCP tool mapping

Mỗi plugin hiện tại (`Core/plugins/`) được wrap thành 1+ MCP tool. Plugin interface (`IntelligencePlugin` Protocol) không thay đổi — chỉ thêm layer MCP wrapper.

| Plugin hiện tại | MCP tool(s) | File |
|---|---|---|
| `hibp.py` | `check_breach(email)` | `Core/plugins/hibp.py` |
| `shodan.py` | `shodan_lookup(ip)` | `Core/plugins/shodan.py` |
| `holehe.py` | `search_email(email)` | `Core/plugins/holehe.py` |
| `maigret.py` | `run_maigret(username, top_n?)` | `Core/plugins/maigret.py` |
| `github.py` | `search_github(username)` | `Core/plugins/github.py` |
| `searxng.py` | `search_web(query)` | `Core/plugins/searxng.py` |
| `dns_resolver.py` | `resolve_dns(domain)` | `Core/plugins/dns_resolver.py` |
| `numverify.py` | `search_phone(phone)` | `Core/plugins/numverify.py` |
| `leak_lookup.py` | `check_leak(email)` | `Core/plugins/leak_lookup.py` |

### 4.2 Plugin types mới

| Type | Mô tả | Ví dụ |
|---|---|---|
| **HTTP Plugin** (hiện tại) | Gọi REST API, parse JSON | HIBP, Shodan, Numverify |
| **Scrape Plugin** (hiện tại) | HTTP + HTML scraping | Maigret, Holehe |
| **Browser Plugin** (mới) | Playwright, bypass bot detection | Cloudflare-protected sites |
| **Composite Plugin** (mới) | Gọi nhiều plugin con, aggregate | `search_person` → Maigret + GitHub + SearXNG |
| **Utility Plugin** (mới) | Không gọi API, xử lý data | `decode_text`, `generate_dorks` |

### 4.3 Auto-discovery

`PluginManager.discover_plugins()` (hiện tại) quét `Core/plugins/` và đăng ký tất cả. MCP server dùng cùng cơ chế — chỉ cần thêm plugin file, tool tự xuất hiện.

MCP wrapper layer (`Core/mcp/tool_registry.py`) map plugin → MCP tool tự động dựa trên `target_types` attribute của plugin:

```python
# Tự động: plugin có target_types=["EMAIL"] → expose làm email tool
# Plugin có target_types=["USERNAME"] → expose làm username tool
```

---

## 5. Evidence Store (Kho Bằng chứng)

### 5.1 Mục tiêu

Lưu trữ kết quả điều tra có thể **query, resume, audit**. Claude Code có thể:
- Tạo investigation mới
- Save evidence sau mỗi tool call
- Query evidence đã thu thập
- Resume investigation bị gián đoạn

### 5.2 Schema mở rộng (SQLite)

Mở rộng `Core/reporting/schema.sql` hiện tại (investigations, findings, tags) thêm 3 bảng:

```sql
-- Bằng chứng thu thập được (mỗi tool call = 1 evidence)
CREATE TABLE IF NOT EXISTS evidence (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    tool_name        TEXT    NOT NULL,      -- MCP tool name
    target           TEXT    NOT NULL,      -- input target
    target_type      TEXT,                  -- EMAIL/USERNAME/IP/DOMAIN/PHONE
    result_data      TEXT    NOT NULL,      -- JSON blob
    confidence       REAL    DEFAULT 0.0,
    source_url       TEXT,
    collected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    collected_by     TEXT    DEFAULT 'claude-code'  -- orchestrator id
);

-- Giả thuyết điều tra (Claude Code đề xuất, verify qua tool)
CREATE TABLE IF NOT EXISTS hypotheses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    statement        TEXT    NOT NULL,      -- "Target likely owns GitHub account X"
    status           TEXT    DEFAULT 'unverified'
                     CHECK(status IN ('unverified','confirmed','refuted','inconclusive')),
    confidence       REAL    DEFAULT 0.0,
    evidence_ids     TEXT,                  -- JSON array of evidence.id
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail (mọi tool call)
CREATE TABLE IF NOT EXISTS audit_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER REFERENCES investigations(id) ON DELETE SET NULL,
    tool_name        TEXT    NOT NULL,
    input_hash       TEXT,                  -- SHA-256 hash of input (privacy)
    success          BOOLEAN,
    duration_ms      INTEGER,
    proxy_used       BOOLEAN DEFAULT FALSE,
    called_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence(investigation_id);
CREATE INDEX IF NOT EXISTS idx_evidence_tool ON evidence(tool_name);
CREATE INDEX IF NOT EXISTS idx_hypotheses_investigation ON hypotheses(investigation_id);
CREATE INDEX IF NOT EXISTS idx_audit_investigation ON audit_log(investigation_id);
```

### 5.3 Evidence Store API

Qua MCP tools:
- `create_investigation(seed, seed_type) → investigation_id`
- `save_evidence(investigation_id, evidence) → evidence_id`
- `query_evidence(investigation_id, filters?) → evidence[]`
- `get_investigation(id) → full profile + evidence + hypotheses`

### 5.4 Resume capability

Claude Code có thể load investigation cũ, đọc evidence đã có, và tiếp tục từ đó — không cần chạy lại tool đã chạy.

---

## 6. Browser Automation Layer (Playwright)

### 6.1 Vấn đề

Nhiều site OSINT (Instagram, Twitter, TikTok) chặn HTTP request thông thường bằng Cloudflare, captcha, hoặc JS challenge. Plugin hiện tại (Holehe, Maigret) dùng HTTP thuần → bị block trên một số site.

### 6.2 Giải pháp: Playwright

- **Package**: `playwright` (Python)
- **File**: `Core/browser/stealth_context.py`
- **Mode**: Headless Chromium với stealth plugin (fake user-agent, disable webdriver flag, human-like delays)
- **Plugin type mới**: `BrowserPlugin` — extends `IntelligencePlugin` nhưng dùng browser thay vì aiohttp

### 6.3 Cách dùng

```python
# Core/browser/stealth_context.py
from playwright.async_api import async_playwright

async def get_stealth_page():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    context = await browser.new_context(user_agent="...")
    page = await context.new_page()
    return page, browser
```

Browser plugin implement `check()` nhưng thay vì `aiohttp.get()`, dùng `page.goto()` + `page.content()`.

### 6.4 Tradeoff

- **Chậm hơn**: browser load ~2-5s/page vs HTTP ~0.5s/page.
- **Nặng hơn**: Chromium ~200MB dependency.
- **Hiệu quả hơn**: bypass được Cloudflare/captcha đơn giản.
- **Chi tiết**: xem ADR-0011.

---

## 7. Source Coverage (Phủ nguồn dữ liệu)

### 7.1 Free vs Paid sources

| Source | Loại | Plugin | Ghi chú |
|---|---|---|---|
| Maigret (509+ sites) | Free | `maigret.py` | Username enumeration |
| Holehe | Free | `holehe.py` | Email → registered sites |
| GitHub | Free | `github.py` | Public profiles, repos |
| SearXNG | Free (self-host) | `searxng.py` | Meta search engine |
| DNS | Free | `dns_resolver.py` | WHOIS, A, MX, TXT |
| HaveIBeenPwned | Paid (API key) | `hibp.py` | Breach data |
| Shodan | Freemium | `shodan.py` | IP services, vulns |
| Numverify | Freemium | `numverify.py` | Phone carrier lookup |
| LeakLookup | Paid | `leak_lookup.py` | Leak database |
| Hunter.io | Paid (API key) | (mới) | Email verification + finder |

### 7.2 API key management

- Tất cả API key qua env variables (`.env`), không bao giờ hardcode.
- Convention: `MH_{PLUGIN_NAME}_API_KEY` (đã có trong `settings.get_plugin_key()`).
- MCP tool trả error rõ ràng nếu thiếu key: `"error_type": "missing_key", "message": "Set MH_SHODAN_API_KEY in .env"`.

### 7.3 Rate limiting

- **Per-plugin**: semaphore trong `PluginManager._safe_execute()` (hiện tại: 5 concurrent).
- **Global**: PluginCache TTL 24h — tránh gọi lại API cho cùng target.
- **Source-specific**: mỗi plugin tự implement retry/backoff cho API-specific limits (e.g. Shodan 1 req/sec).
- **Proxy rotation**: `ProxyManager.rotate()` khi bị IP-banned.

---

## 8. Bảo mật & Đạo đức (Security & Ethics)

### 8.1 Consent tracking

- Mỗi investigation ghi `consent_accepted: true` + timestamp khi tạo.
- CLI/MCP hiển thị disclaimer trước khi chạy tool.
- Audit log ghi lại mọi tool call (xem §5.2 `audit_log` table).

### 8.2 Audit trail

- `audit_log` table: tool name, input hash (không lưu raw input — privacy), success, duration, proxy used, timestamp.
- Giống ADR-0008 (proxy audit trail) nhưng mở rộng cho mọi tool call, không chỉ proxy.
- Retention: 90 ngày (configurable qua `MH_AUDIT_RETENTION_DAYS`).

### 8.3 Data retention

- Evidence: giữ vô hạn (user-controlled delete).
- Audit log: 90 ngày default, auto-purge.
- Plugin cache: 24h TTL (configurable).
- Proxy audit: 30 ngày (hiện tại, ADR-0008).

### 8.4 Safe mode

- MCP server có flag `safe_mode` (env `MH_SAFE_MODE=true`):
  - Exclude NSFW sources.
  - Exclude sources có `tos_risk: "ban_risk"`.
  - Disable browser automation (chỉ HTTP).
- Mặc định: safe_mode ON. User phải explicitly disable.

### 8.5 Legal disclaimer

- Mỗi investigation report có footer: "Data collected from public sources. Verify before acting. Comply with local laws."
- Không lưu raw credentials/passwords — chỉ metadata (breach name, date).

---

## 9. Technology Stack

| Layer | Công nghệ | Lý do |
|---|---|---|
| **Language** | Python 3.10+ | Đã có, ecosystem OSINT phong phú |
| **MCP SDK** | `mcp` (pip install mcp) | Official Python SDK, FastMCP decorator |
| **Browser** | Playwright (Python) | Cross-browser, stealth, async-native |
| **Database** | SQLite (WAL mode) | Đã có, zero-infra, đủ cho single-user |
| **HTTP** | aiohttp | Đã có, async, connection pooling |
| **REST API** | FastAPI | Đã có (`Core/api/server.py`), giữ lại |
| **Cache** | SQLite (PluginCache) | Đã có, TTL-based |
| **Proxy** | aiohttp + ProxyManager | Đã có, pool rotation + health check |
| **Config** | python-dotenv + configparser | Đã có, secrets in .env |
| **Testing** | pytest + pytest-asyncio | Đã có |
| **Entity resolution** | jellyfish + imagehash + Pillow | Đã có (optional deps) |

### Dependencies mới

```
mcp>=1.0          # MCP Python SDK
playwright>=1.40  # Browser automation
```

---

## 10. Đường di chuyển (Migration Path)

### Phase 1: MCP Server MVP (2-3 tuần)

1. Tạo `Core/mcp/server.py` — FastMCP server với 5 tool cốt lõi:
   - `search_username`, `search_email`, `search_domain`, `check_breach`, `resolve_entities`
2. Mỗi tool wrap `PluginManager` / `StagedProfiler` hiện tại — không thay đổi plugin code.
3. Test với Claude Code: thêm config `~/.claude/mcp_servers.json`:
   ```json
   { "mrholmes": { "command": "python", "args": ["-m", "Core.mcp.server"] } }
   ```
4. Giữ CLI + REST API hoạt động (backward compatible).

### Phase 2: Evidence Store (1-2 tuần)

1. Mở rộng `schema.sql` thêm `evidence`, `hypotheses`, `audit_log` tables.
2. Thêm MCP tools: `create_investigation`, `save_evidence`, `query_evidence`, `get_investigation`.
3. Mỗi tool call tự động save evidence nếu `investigation_id` được truyền.

### Phase 3: Browser Automation (1-2 tuần)

1. Add `playwright` dependency.
2. Tạo `Core/browser/stealth_context.py`.
3. Convert 2-3 plugin quan trọng (Instagram, Twitter) sang BrowserPlugin.
4. Thêm MCP tool `scrape_profile(url)`.

### Phase 4: Tool Catalog đầy đủ (1-2 tuần)

1. Wrap tất cả plugin còn lại thành MCP tool (xem `mcp-tool-catalog.md`).
2. Thêm utility tools: `decode_text`, `generate_dorks`, `generate_report`.
3. Auto-discovery: plugin mới tự xuất hiện làm MCP tool.

### Phase 5: Hardening (tuần rải rác)

1. Rate limiting per-tool.
2. Safe mode enforcement.
3. Audit log auto-purge.
4. Documentation + examples cho Claude Code prompts.

### Tổng thời gian ước tính: 6-9 tuần (part-time, 1 developer)

---

## Phụ lục: Tham chiếu file hiện tại

| File | Vai trò trong 2.0 |
|---|---|
| `Core/plugins/base.py` | Không đổi — `IntelligencePlugin` Protocol |
| `Core/plugins/manager.py` | Không đổi — `PluginManager` dùng trong MCP wrapper |
| `Core/engine/autonomous_agent.py` | Không đổi — `StagedProfiler` gọi qua MCP tool |
| `Core/engine/entity_resolver.py` | Không đổi — `EntityResolver` gọi qua `resolve_entities` tool |
| `Core/api/server.py` | Giữ lại — secondary interface |
| `Core/reporting/database.py` | Mở rộng — thêm evidence/hypotheses/audit tables |
| `Core/reporting/schema.sql` | Mở rộng — thêm 3 bảng mới |
| `Core/cache/plugin_cache.py` | Không đổi — dùng trong MCP wrapper |
| `Core/proxy/manager.py` | Không đổi — dùng trong MCP wrapper |
| `Core/config/settings.py` | Mở rộng — thêm `mcp_token`, `safe_mode` settings |
| `Core/models/profile_entity.py` | Không đổi — golden record model |
| `Core/mcp/server.py` | **Mới** — MCP server entry point |
| `Core/mcp/tool_registry.py` | **Mới** — auto map plugin → MCP tool |
| `Core/browser/stealth_context.py` | **Mới** — Playwright stealth context |
