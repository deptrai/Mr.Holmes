# Mr.Holmes v2.1 — Architecture Spine

> Vietnam OSINT Enhancement Initiative
> Altitude: initiative → features
> Date: 2026-06-27

## Paradigm

**Plugin-first MCP detective.** Mọi OSINT source là một plugin implement `IntelligencePlugin` Protocol. MCP server expose plugins as tools. AI orchestrator (Claude Code) gọi tools, lưu evidence, cross-reference. v2.1 mở rộng coverage sang Vietnam-specific sources + social media scrapers + government records, giữ nguyên paradigm v2.0.

## Inherited Invariants (from v2.0)

- **Plugin Protocol**: `name`, `requires_api_key`, `check(target, target_type) → PluginResult`
- **PluginManager**: auto-discover `Core/plugins/*.py`, duck-type check, dedup by name
- **MCP tool pattern**: `@mcp.tool() async def func(...) -> str`, trả JSON string
- **Evidence Store**: SQLite, `investigation_id` FK, `result_json`, `confidence`, audit log
- **StealthBrowser**: `Core/browser/stealth_context.py`, Playwright `start()/stop()`
- **Settings**: `.env` + python-dotenv, `MH_*` env var prefix
- **Stage routing**: 1=legacy, 2=identity expansion, 3=deep enrichment

## Architecture Decisions

### AD-1: Plugin-first — mọi source mới là plugin [ADOPTED]
- **Binds**: tất cả OSINT sources mới tuân thủ `IntelligencePlugin` Protocol
- **Prevents**: divergence giữa plugins, dead standalone scripts
- **Rule**: `Core/plugins/<name>.py`, auto-discover qua `PluginManager.discover_plugins()`

### AD-2: Vietnam OSINT layer — stage=3 deep enrichment [ADOPTED]
- **Binds**: Vietnam-specific plugins (VnCourt, VnTax, VnNews, Zalo, FacebookVn) gán `stage=3`
- **Prevents**: chạy Vietnam scrapers khi chưa có clue (waste, IP ban risk)
- **Rule**: Stage router chạy stage 1→2→3, stage 3 chỉ khi có clues từ stage 1-2

### AD-3: Social media scraper pattern — StealthBrowser [ADOPTED]
- **Binds**: Facebook/Instagram/TikTok/Zalo scrapers dùng `StealthBrowser` context manager
- **Prevents**: 403/bot detection failures từ HTTP requests
- **Rule**: `async with StealthBrowser() as browser: page = await browser.new_page(); ...`

### AD-4: Government records — scrape public portals [ADOPTED]
- **Binds**: `tracuunnt.gdt.gov.vn`, `thuvienphapluat.vn`, `dangkykinhdoanh.gov.vn` qua Playwright
- **Prevents**: IP ban
- **Rule**: Rate limit 1 req/3s, CAPTCHA → log warning + return partial result

### AD-5: Wire 3 engine modules vào MCP [ADOPTED]
- **Binds**: `llm_synthesizer` → `synthesize_report`, `pdf_builder` → `export_pdf`, `mindmap_generator` → `generate_mindmap`
- **Prevents**: dead code, modules chỉ dùng trong legacy CLI
- **Rule**: MCP wrapper, giữ nguyên implementation

### AD-6: Cross-reference engine [ADOPTED]
- **Binds**: `cross_reference` tool nhận evidence IDs, tìm overlap, suggest new targets
- **Prevents**: manual cross-check by AI orchestrator
- **Rule**: Query Evidence Store, match emails/usernames/phones across evidence rows

### AD-7: Truecaller/GetContact — phone → owner name [ADOPTED]
- **Binds**: Phone enrichment trả tên chủ sở hữu, không chỉ carrier
- **Prevents**: phone chỉ trả carrier mà không có tên
- **Rule**: Truecaller API (paid) hoặc GetContact (free), user cung cấp key

### AD-8: News archive — Google News + site dorks [ADOPTED]
- **Binds**: Vietnam news search qua Google News API + `site:tuoitre.vn` dorks
- **Prevents**: IP ban từ newspaper sites (anti-bot)
- **Rule**: Không scrape trực tiếp newspaper sites

### AD-9: Avatar reverse search [ADOPTED]
- **Binds**: Google Images + Yandex Images + FaceCheck.id API
- **Prevents**: manual image search
- **Rule**: Input avatar URL → output other profiles dùng cùng avatar

### AD-10: Snusbase — breach DB alternative [ADOPTED]
- **Binds**: Snusbase plugin riêng, không thay thế IntelX/LeakLookup
- **Prevents**: single point of failure cho breach data
- **Rule**: User cung cấp `MH_SNUSBASE_API_KEY`, paid $5/mo

## Feature Map (v2.1)

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Orchestrator (Claude Code)             │
│                  Cross-reference + Reasoning                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ MCP tools
┌──────────────────────────▼──────────────────────────────────┐
│                    MCP Server (Core/mcp/)                     │
│  v2.0 tools (27) + v2.1 new tools (12) = 39 total             │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Plugins     │  │  Engine      │  │  Browser     │
│  (Core/plugins)│  (Core/engine)│  │  (Stealth)   │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ v2.0 (13)    │  │ v2.0 (9 wired│  │ Playwright   │
│ v2.1 new:    │  │  +3 newly    │  │ stealth ctx  │
│ - Zalo       │  │  wired)      │  │              │
│ - FacebookVn │  │ - LLM synth  │  │ Scrapers:    │
│ - TikTokVn   │  │ - PDF build  │  │ - FB         │
│ - Instagram  │  │ - Mindmap    │  │ - IG         │
│ - LinkedIn   │  │              │  │ - Zalo       │
│ - VnCourt    │  │              │  │ - TikTok     │
│ - VnTax      │  │              │  │ - Gov portals│
│ - VnNews     │  │              │  │              │
│ - Truecaller │  │              │  │              │
│ - Snusbase   │  │              │  │              │
│ - AvatarRev  │  │              │  │              │
│ - XInvoice   │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              Evidence Store (SQLite)                          │
│  investigations + evidence + audit_log + cross_refs           │
└─────────────────────────────────────────────────────────────┘
```

## New Plugins (v2.1)

| # | Plugin | Target Types | Source | Stage | API Key |
|---|--------|-------------|--------|-------|---------|
| 1 | **Zalo** | USERNAME, PHONE | zalo.me/scrape | 3 | No |
| 2 | **FacebookVn** | USERNAME, NAME, PHONE | mbasic.facebook.com | 3 | No |
| 3 | **TikTokVn** | USERNAME | tiktok.com + Toutatis | 3 | No |
| 4 | **Instagram** | USERNAME, EMAIL | instagram.com + stealth | 2 | No |
| 5 | **LinkedIn** | NAME, USERNAME | linkedin.com + stealth | 3 | No |
| 6 | **VnCourt** | NAME, CASE_ID | thuvienphapluat.vn | 3 | No |
| 7 | **VnTax** | TAX_ID, NAME | tracuunnt.gdt.gov.vn | 3 | No |
| 8 | **VnNews** | NAME, COMPANY | Google News + dorks | 2 | No |
| 9 | **Truecaller** | PHONE | truecaller.com API | 3 | Yes |
| 10 | **Snusbase** | EMAIL, USERNAME, PHONE, IP | snusbase.com | 1 | Yes |
| 11 | **AvatarReverse** | IMAGE_URL | Google + Yandex + FaceCheck | 3 | FaceCheck: Yes |
| 12 | **XInvoice** | TAX_ID | api.xinvoice.vn | 3 | Yes |

## New MCP Tools (v2.1)

| # | Tool | Function |
|---|------|----------|
| 1 | `search_zalo` | Zalo profile lookup |
| 2 | `search_facebook` | Facebook profile scrape |
| 3 | `search_tiktok` | TikTok profile + Toutatis enrichment |
| 4 | `search_instagram` | Instagram profile scrape |
| 5 | `search_linkedin` | LinkedIn profile scrape |
| 6 | `search_court_records` | Vietnam court records |
| 7 | `search_tax` | Vietnam tax code lookup |
| 8 | `search_news` | Vietnam news archive search |
| 9 | `reverse_phone` | Phone → owner name (Truecaller) |
| 10 | `snusbase_search` | Snusbase breach search |
| 11 | `reverse_avatar` | Avatar → other profiles |
| 12 | `cross_reference` | Cross-reference evidence IDs |
| 13 | `synthesize_report` | LLM report generation |
| 14 | `export_pdf` | PDF report export |
| 15 | `generate_mindmap` | Mindmap generation |

**Total: v2.0 (27) + v2.1 (15) = 42 MCP tools**

## Sprints

### Sprint 1 (P0 — Vietnam Core)
- Wire 3 engine modules → MCP (synthesize_report, export_pdf, generate_mindmap)
- VnTax plugin (tracuunnt.gdt.gov.vn scraper)
- VnCourt plugin (thuvienphapluat.vn scraper)
- VnNews plugin (Google News + dorks)
- XInvoice plugin (API integration)
- Cross-reference engine

### Sprint 2 (P0 — Social Media)
- FacebookVn plugin (StealthBrowser + mbasic.facebook.com)
- Instagram plugin (StealthBrowser)
- TikTokVn plugin (StealthBrowser + Toutatis)
- Zalo plugin (StealthBrowser)
- LinkedIn plugin (StealthBrowser)

### Sprint 3 (P1 — Enrichment)
- Truecaller plugin (phone → name)
- Snusbase plugin (breach DB)
- AvatarReverse plugin (Google + Yandex + FaceCheck)
- Enhanced VnPhone with Trang Vàng

## Deferred

- **Financial intelligence** (bank accounts, credit) — require legal authorization, not public OSINT
- **OSINTDog/CloudSINT** — paid unified APIs, evaluate later
- **Telegram/Discord OSINT** — niche, lower priority for Vietnam
- **Face recognition models** — heavy ML, defer to v2.2
- **Vietnam land registry (sổ đỏ)** — not publicly accessible online

## Open Questions

- **Q1**: Zalo có public API không, hay phải reverse engineer? → Research needed
- **Q2**: Truecaller API pricing cho Vietnam? → Check truecaller.com/api
- **Q3**: thuvienphapluat.vn có CAPTCHA không? → Test during Sprint 1
- **Q4**: FaceCheck.id API free tier limits? → Check during Sprint 3
