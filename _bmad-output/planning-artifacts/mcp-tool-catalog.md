# Mr.Holmes 2.0 — MCP Tool Catalog

Danh sách đầy đủ các MCP tool mà Mr.Holmes expose cho Claude Code.

Mỗi tool có: tên, input params, output schema, plugin/file backend.

---

## Username OSINT

### `search_username`
- **Input**: `username: str`, `sites: list[str] | None = None`
- **Output**: `{ "found": [{site, url, tags}], "not_found": [site], "total_checked": int }`
- **Backend**: `PluginManager` → Maigret + site list JSON (`Site_lists/Username/`)
- **Notes**: `sites=None` quét tất cả 509+ sites. Pass list để giới hạn.

### `run_maigret`
- **Input**: `username: str`, `top_n: int | None = None`
- **Output**: `{ "profiles": [{site, url, rank}], "count": int }`
- **Backend**: `Core/plugins/maigret.py`
- **Notes**: `top_n` giới hạn số site (Maigret hỗ trợ `--top`). Mặc định all.

### `scrape_profile`
- **Input**: `url: str`, `fields: list[str] | None = None`
- **Output**: `{ "bio": str, "posts": int, "avatar": str, "name": str, "raw_html": str }`
- **Backend**: `Core/browser/stealth_context.py` (Playwright)
- **Notes**: Dùng browser automation để bypass Cloudflare. `fields=None` scrape tất cả.

---

## Email OSINT

### `search_email`
- **Input**: `email: str`
- **Output**: `{ "registered_sites": [{site, url}], "count": int }`
- **Backend**: `Core/plugins/holehe.py`
- **Notes**: Kiểm tra email đã đăng ký trên哪些 services (Instagram, Twitter, ...).

### `check_breach`
- **Input**: `email: str`
- **Output**: `{ "breaches": [{name, date, data_classes, count}], "count": int }`
- **Backend**: `Core/plugins/hibp.py`
- **Notes**: Yêu cầu `MH_HAVEIBEENPWNED_API_KEY`.

### `check_leak`
- **Input**: `email: str`
- **Output**: `{ "leaks": [{source, emails_found, date}], "count": int }`
- **Backend**: `Core/plugins/leak_lookup.py`
- **Notes**: Yêu cầu `MH_LEAKLOOKUP_API_KEY`.

### `validate_email`
- **Input**: `email: str`
- **Output**: `{ "valid": bool, "format_ok": bool, "mx_records": list[str], "disposable": bool }`
- **Backend**: `Core/plugins/dns_resolver.py` (MX lookup) + format check
- **Notes**: Free, không cần API key.

---

## Phone OSINT

### `search_phone`
- **Input**: `phone: str`
- **Output**: `{ "carrier": str, "location": str, "line_type": str, "valid": bool }`
- **Backend**: `Core/plugins/numverify.py`
- **Notes**: Yêu cầu `MH_NUMVERIFY_API_KEY`. Phone format E.164.

### `validate_phone`
- **Input**: `phone: str`
- **Output**: `{ "valid": bool, "format": str, "country_code": str }`
- **Backend**: `Core/models/validators.py` (phonenumbers lib)
- **Notes**: Free, offline validation.

---

## Domain/IP OSINT

### `search_domain`
- **Input**: `domain: str`
- **Output**: `{ "whois": {...}, "dns": {"a": [], "mx": [], "txt": [], "ns": []}, "ip": str, "registrar": str }`
- **Backend**: `Core/plugins/dns_resolver.py` + WHOIS
- **Notes**: Free.

### `resolve_dns`
- **Input**: `domain: str`, `record_type: str = "A"`
- **Output**: `{ "records": [str], "record_type": str }`
- **Backend**: `Core/plugins/dns_resolver.py`
- **Notes**: `record_type`: A, AAAA, MX, TXT, NS, CNAME, SOA.

### `scan_ports`
- **Input**: `ip: str`, `ports: list[int] | None = None`
- **Output**: `{ "open_ports": [{port, service, banner}], "closed": int, "total_scanned": int }`
- **Backend**: `Core/Port_Scanner.py` (legacy) wrapped as MCP tool
- **Notes**: `ports=None` scan top 100 common ports. Rate-limited.

### `shodan_lookup`
- **Input**: `ip: str`
- **Output**: `{ "services": [{port, protocol, banner}], "vulnerabilities": [...], "hostnames": [...], "org": str, "location": str }`
- **Backend**: `Core/plugins/shodan.py`
- **Notes**: Yêu cầu `MH_SHODAN_API_KEY`.

---

## Person OSINT

### `search_person`
- **Input**: `name: str`, `location: str | None = None`
- **Output**: `{ "profiles": [{platform, url, confidence}], "count": int }`
- **Backend**: Composite — Maigret + GitHub + SearXNG
- **Notes**: Composite plugin: chạy nhiều source, aggregate kết quả.

### `search_github`
- **Input**: `username: str`
- **Output**: `{ "profile": {url, bio, repos, followers}, "repos": [{name, stars, language}], "email": str | None }`
- **Backend**: `Core/plugins/github.py`
- **Notes**: Free (GitHub API, rate-limited 60 req/hr without token).

### `generate_dorks`
- **Input**: `target: str`, `type: str` (username|email|domain|phone)
- **Output**: `{ "google_dorks": [str], "yandex_dorks": [str], "count": int }`
- **Backend**: `Site_lists/Username/Google_dorks.txt` + `Yandex_dorks.txt`
- **Notes**: Utility tool, không gọi API. Trả list dork queries cho Claude Code.

### `search_web`
- **Input**: `query: str`, `engines: list[str] | None = None`
- **Output**: `{ "results": [{title, url, snippet}], "count": int }`
- **Backend**: `Core/plugins/searxng.py`
- **Notes**: SearXNG meta-search. Self-hosted instance configurable qua `MH_SEARXNG_URL`.

---

## Entity Resolution

### `resolve_entities`
- **Input**: `entities: list[dict]` (each = ProfileEntity dict)
- **Output**: `{ "golden_record": ProfileEntity, "confidence": float, "sources_merged": int }`
- **Backend**: `Core/engine/entity_resolver.py` (`EntityResolver.resolve()`)
- **Notes**: Merge multiple ProfileEntity → 1 golden record. Jaro-Winkler + pHash.

### `merge_profiles`
- **Input**: `profiles: list[dict]`
- **Output**: `{ "unified": ProfileEntity, "conflicts": [{field, values, resolved}], "confidence": float }`
- **Backend**: `Core/engine/entity_resolver.py` + conflict detection
- **Notes**: Giống `resolve_entities` nhưng trả thêm conflict report.

### `run_profiler`
- **Input**: `seed: str`, `seed_type: str`, `max_depth: int = 2`
- **Output**: `{ "nodes": [...], "edges": [...], "plugin_results": [...], "stats": {...} }`
- **Backend**: `Core/engine/autonomous_agent.py` (`StagedProfiler.run_staged()`)
- **Notes**: BFS recursive profiling. `seed_type`: EMAIL|USERNAME|PHONE|DOMAIN|IP.

---

## Evidence Store

### `create_investigation`
- **Input**: `seed: str`, `seed_type: str`
- **Output**: `{ "investigation_id": int, "created_at": str }`
- **Backend**: `Core/reporting/database.py` → `investigations` table
- **Notes**: Tạo investigation mới. Trả ID dùng cho các tool save/query.

### `save_evidence`
- **Input**: `investigation_id: int`, `evidence: dict` (tool_name, target, result_data, source_url?, confidence?)
- **Output**: `{ "evidence_id": int, "saved_at": str }`
- **Backend**: `Core/reporting/database.py` → `evidence` table
- **Notes**: Lưu kết quả 1 tool call làm evidence.

### `query_evidence`
- **Input**: `investigation_id: int`, `filters: dict | None = None` (tool_name?, target?, min_confidence?)
- **Output**: `{ "evidence": [evidence_row], "count": int }`
- **Backend**: `Core/reporting/database.py` → `evidence` table (SELECT with filters)
- **Notes**: Query evidence đã thu thập. Hỗ trợ resume investigation.

### `get_investigation`
- **Input**: `id: int`
- **Output**: `{ "investigation": {...}, "evidence": [...], "hypotheses": [...], "stats": {...} }`
- **Backend**: `Core/reporting/database.py` → JOIN investigations + evidence + hypotheses
- **Notes**: Load full investigation state. Claude Code dùng để resume.

### `create_hypothesis`
- **Input**: `investigation_id: int`, `statement: str`, `evidence_ids: list[int] | None = None`
- **Output**: `{ "hypothesis_id": int, "status": "unverified" }`
- **Backend**: `Core/reporting/database.py` → `hypotheses` table
- **Notes**: Claude Code đề xuất giả thuyết, link evidence.

### `update_hypothesis`
- **Input**: `hypothesis_id: int`, `status: str` (confirmed|refuted|inconclusive), `confidence: float`
- **Output**: `{ "hypothesis_id": int, "updated_at": str }`
- **Backend**: `Core/reporting/database.py` → `hypotheses` table (UPDATE)
- **Notes**: Cập nhật trạng thái giả thuyết sau khi verify.

---

## Utility

### `decode_text`
- **Input**: `text: str`, `format: str` (base64|hex|url|rot13|binary|morse)
- **Output**: `{ "decoded": str, "format": str, "original": str }`
- **Backend**: `Core/Decoder.py` (legacy) wrapped as MCP tool
- **Notes**: Offline, không gọi API.

### `generate_report`
- **Input**: `investigation_id: int`, `format: str` (json|html|pdf|txt)
- **Output**: `{ "report_path": str, "format": str, "size_bytes": int }`
- **Backend**: `Core/reporting/` + `Core/PDF_Converter.py`
- **Notes**: Tạo báo cáo từ investigation data. PDF cần `reportlab`.

### `list_plugins`
- **Input**: (none)
- **Output**: `{ "plugins": [{name, stage, requires_api_key, target_types, tos_risk}] }`
- **Backend**: `PluginManager.discover_plugins()`
- **Notes**: Liệt kê tất cả plugin available. Claude Code dùng để biết tool nào dùng được.

### `check_proxy_health`
- **Input**: (none)
- **Output**: `{ "total": int, "healthy": int, "dead": int, "dead_urls": [str] }`
- **Backend**: `Core/proxy/manager.py` (`ProxyManager.health_check()`)
- **Notes**: Kiểm tra proxy pool health.

---

## Tổng kết

| Category | Số tool | Tools |
|---|---|---|
| Username OSINT | 3 | search_username, run_maigret, scrape_profile |
| Email OSINT | 4 | search_email, check_breach, check_leak, validate_email |
| Phone OSINT | 2 | search_phone, validate_phone |
| Domain/IP OSINT | 4 | search_domain, resolve_dns, scan_ports, shodan_lookup |
| Person OSINT | 4 | search_person, search_github, generate_dorks, search_web |
| Entity Resolution | 3 | resolve_entities, merge_profiles, run_profiler |
| Evidence Store | 6 | create_investigation, save_evidence, query_evidence, get_investigation, create_hypothesis, update_hypothesis |
| Utility | 4 | decode_text, generate_report, list_plugins, check_proxy_health |
| **Tổng** | **30** | |
