# PRD: Mr.Holmes 2.0 — MCP Detective

**Version:** 2.0.0  
**Date:** 2026-06-27  
**Status:** approved  
**Author:** John (PM)  
**Architect:** Winston  

---

## 1. Executive Summary

Mr.Holmes 2.0 chuyển từ công cụ OSINT CLI standalone thành **MCP-powered tool collection**. Claude Code làm AI orchestrator — tự quyết định tìm gì tiếp, kết nối thông tin, đặt giả thuyết. Mr.Holmes expose 30+ tools qua MCP server, bao gồm: username/email/phone/domain OSINT, browser automation (Playwright), breach databases, Vietnamese public records, evidence store.

## 2. Goals & Non-Goals

### Goals
- Expose 30+ OSINT tools qua MCP server
- Claude Code có thể điều tra iterative từ bất kỳ seed nào
- Browser automation bypass Cloudflare/captcha
- Evidence store SQLite — lưu mọi finding, queryable, resume
- 5+ new plugins (Vietnamese sources, breach, social media)
- BMad skills cho investigation workflows
- 1400+ tests, CI green

### Non-Goals
- Web dashboard / React frontend
- Mobile app
- Real-time monitoring
- Custom AI model
- Graph database (Neo4j)

## 3. Epics & User Stories

### Epic 10: MCP Server
Expose tất cả OSINT functions qua MCP protocol.

**US-10-1: MCP Server Core**
As a Claude Code user, I want to connect to Mr.Holmes MCP server so that I can call OSINT tools.
- AC: MCP server chạy trên stdio transport
- AC: Server expose 30+ tools
- AC: Mỗi tool có input schema (JSON Schema)
- AC: Error handling — tool exception trả structured error
- AC: `mcp` Python package installed

**US-10-2: Username OSINT Tools**
As a Claude Code user, I want to search usernames across 3000+ sites.
- AC: `search_username(username, sites?)` tool
- AC: `run_maigret(username, top_n?)` tool
- AC: `scrape_profile(url, fields?)` tool
- AC: Returns JSON với found/not_found/blocked

**US-10-3: Email/Phone/Domain Tools**
As a Claude Code user, I want to search by email, phone, or domain.
- AC: `search_email`, `check_breach`, `check_leak`, `validate_email` tools
- AC: `search_phone`, `validate_phone` tools
- AC: `search_domain`, `scan_ports`, `shodan_lookup`, `whois_lookup` tools

**US-10-4: Entity Resolution Tools**
As a Claude Code user, I want to merge duplicate entities.
- AC: `resolve_entities(entities)` → golden record
- AC: `merge_profiles(profiles)` → unified profile
- AC: Confidence scoring preserved

**US-10-5: Utility Tools**
As a Claude Code user, I want decode/generate/report tools.
- AC: `decode_text`, `generate_dorks`, `generate_report` tools
- AC: `create_investigation`, `get_investigation` tools

### Epic 11: Browser Automation
Playwright-based plugin để bypass bot detection.

**US-11-1: Stealth Browser Context**
As a plugin developer, I want a Playwright stealth context to bypass Cloudflare.
- AC: `Core/browser/stealth_context.py` module
- AC: Stealth config (user-agent, viewport, stealth scripts)
- AC: Context pool (reuse browsers)
- AC: Timeout handling

**US-11-2: Browser Scraper Plugin**
As a Claude Code user, I want to scrape profiles that block HTTP requests.
- AC: `scrape_profile(url)` MCP tool
- AC: Extract: bio, name, avatar, posts count, follower count
- AC: Support: Instagram, Twitter, TikTok, Facebook, LinkedIn
- AC: Fallback to HTTP if Playwright unavailable

**US-11-3: Screenshot Tool**
As a Claude Code user, I want to screenshot a webpage for evidence.
- AC: `screenshot_page(url)` MCP tool
- AC: Returns base64 image
- AC: Full page or viewport mode

### Epic 12: Enhanced Source Coverage
New plugins cho Vietnamese sources, breach DBs, social media.

**US-12-1: Vietnamese Business Registry**
As a Claude Code user, I want to search Vietnamese business records.
- AC: `search_vn_business(tax_id_or_name)` MCP tool
- AC: Source: dangkykinhdoanh.gov.vn (public)
- AC: Returns: company name, tax code, address, legal rep, status

**US-12-2: Vietnamese Phone Lookup**
As a Claude Code user, I want to identify Vietnamese phone carriers.
- AC: `lookup_vn_phone(phone)` MCP tool
- AC: Carrier detection (Viettel, MobiFone, VinaPhone, etc.)
- AC: Region detection (prefix-based)

**US-12-3: IntelX Breach Search**
As a Claude Code user, I want to search breach data via IntelX.
- AC: `search_intelx(query, type)` MCP tool
- AC: Requires `MH_INTELX_API_KEY`
- AC: Returns: breach name, date, data types, match count

**US-12-4: Social Media Plugins**
As a Claude Code user, I want dedicated social media plugins.
- AC: `search_reddit(username)` — Reddit profile + posts
- AC: `search_instagram(username)` — Instagram profile (via Playwright)
- AC: `search_twitter(username)` — Twitter/X profile (via Playwright)

### Epic 13: Evidence Store
Enhanced SQLite schema cho iterative investigation.

**US-13-1: Evidence Schema**
As a system, I want to store every finding with provenance.
- AC: `evidence` table: id, investigation_id, tool_name, target, target_type, result_json, confidence, source_url, timestamp
- AC: `investigations` table: id, seed, seed_type, status, created_at, updated_at, summary_json
- AC: `audit_log` table: id, investigation_id, action, actor, timestamp, details_json
- AC: Migration script (backward compatible)

**US-13-2: Evidence MCP Tools**
As a Claude Code user, I want to save and query evidence.
- AC: `create_investigation(seed, seed_type)` → investigation_id
- AC: `save_evidence(investigation_id, evidence)` → evidence_id
- AC: `query_evidence(investigation_id, filters?)` → evidence[]
- AC: `get_investigation(id)` → full profile with all evidence

**US-13-3: Investigation Resume**
As a Claude Code user, I want to resume a previous investigation.
- AC: `list_investigations()` → all investigations
- AC: `get_investigation(id)` → full state
- AC: Claude Code can continue from saved state

### Epic 14: OSINT Skills
BMad skills cho investigation workflows.

**US-14-1: Person Investigation Skill**
As a Claude Code user, I want a skill that guides person investigation.
- AC: `.devin/skills/osint-investigate-person/SKILL.md`
- AC: Playbook: seed → expand → scrape → resolve → report
- AC: Calls MCP tools in sequence
- AC: Produces Vietnamese markdown report

**US-14-2: Fraud Check Skill**
As a Claude Code user, I want to check if someone is a scammer.
- AC: `.devin/skills/osint-fraud-check/SKILL.md`
- AC: Check: phone carrier, breach history, social media age, cross-platform consistency
- AC: Risk scoring (low/medium/high)

**US-14-3: Due Diligence Skill**
As a Claude Code user, I want to vet a business partner.
- AC: `.devin/skills/osint-due-diligence/SKILL.md`
- AC: Check: business registry, tax code, legal rep profile, domain WHOIS, online reputation

### Epic 15: Documentation
Update docs cho MCP integration.

**US-15-1: MCP Integration Guide**
As a user, I want to know how to connect Claude Code to Mr.Holmes.
- AC: `docs/MCP_INTEGRATION.md`
- AC: Setup instructions (pip install, config, Claude Code config)
- AC: Tool catalog reference
- AC: Example investigation walkthrough

**US-15-2: Plugin SDK Update**
As a developer, I want to create new MCP-compatible plugins.
- AC: Update `docs/PLUGIN_SDK.md` with MCP section
- AC: How plugins auto-map to MCP tools
- AC: Testing guide for MCP tools

## 4. Non-Functional Requirements

### Performance
- MCP tool response <30s (except Maigret full scan <5min)
- Browser automation <60s per page
- SQLite query <100ms

### Security
- API keys from .env, never logged
- Consent tracking for all investigations
- Audit log for every tool call
- Safe mode (exclude NSFW by default)

### Reliability
- Tool exceptions return structured error, don't crash server
- Browser context pool with auto-recovery
- SQLite WAL mode for concurrent access

### Compatibility
- Python 3.10+
- macOS, Linux, Windows
- Claude Code MCP client

## 5. Technical Constraints
- MCP protocol via `mcp` Python package (FastMCP)
- Playwright for browser automation
- SQLite (no new database infrastructure)
- Existing codebase (Core/plugins/, Core/engine/, Core/models/)
- 1305 existing tests must continue to pass

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Playwright heavy dependency | Medium | Optional install, HTTP fallback |
| MCP SDK API changes | Low | Pin version, abstract transport |
| Vietnamese sources block bots | Medium | Playwright stealth, rate limiting |
| API key costs | Low | Free tier first, user provides own keys |
| Claude Code context limit | Medium | Evidence store offloads to SQLite |

## 7. Dependencies
- `mcp` Python package (MCP SDK)
- `playwright` (browser automation)
- Existing: aiohttp, fastapi, pytest, rich
- New: `mcp>=1.0`, `playwright>=1.40`

## 8. Acceptance Criteria (Per Epic)

| Epic | Done When |
|------|-----------|
| Epic 10 | MCP server runs, 30+ tools callable from Claude Code |
| Epic 11 | scrape_profile works on Instagram/Twitter via Playwright |
| Epic 12 | 4 new plugins operational with real data |
| Epic 13 | Evidence stored, queryable, resume works |
| Epic 14 | 3 BMad skills created, tested with real investigation |
| Epic 15 | Docs complete, user can setup in <10 min |
