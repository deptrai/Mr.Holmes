# OSINT Person Investigation

Investigate a person from any seed (username, email, phone, name, tax ID) using Mr.Holmes MCP tools. Builds a comprehensive profile through iterative discovery.

## When to Use
- User says "investigate this person"
- User says "find information about [username/email/phone/name]"
- User says "build a profile on [target]"
- User provides a seed and wants deep OSINT investigation

## Prerequisites
- Mr.Holmes MCP server must be connected
- Required tools: search_username, run_maigret, search_email, check_breach, search_phone, search_domain, run_plugin, create_investigation, save_evidence, query_evidence, get_investigation

## Investigation Playbook

### Phase 1: Seed Intake
1. Identify seed type (username, email, phone, name, tax_id, domain)
2. Create investigation: `create_investigation(seed, seed_type)`
3. Save investigation_id for later use

### Phase 2: Broad Scan
Based on seed type, run primary tools:

**If username:**
- `run_maigret(username)` — 500+ sites
- `run_plugin("GitHub", username, "username")` — GitHub profile
- `run_plugin("Reddit", username, "username")` — Reddit profile
- `generate_dorks(username, "google")` — Google dorks

**If email:**
- `search_email(email)` — registered sites (Holehe)
- `check_breach(email)` — breach data (HIBP)
- `check_leak(email)` — leak lookup
- `validate_email(email)` — format validation
- Derive username from email prefix → run username tools

**If phone:**
- `search_phone(phone)` — carrier, location (Numverify)
- `run_plugin("VnPhone", phone, "phone")` — Vietnamese carrier
- `validate_phone(phone)` — format validation
- `generate_dorks(phone, "google")` — Google dorks

**If name:**
- `search_person(name)` — SearxNG person search
- `generate_dorks(name, "google")` — Google dorks
- Try common username derivations

**If domain:**
- `search_domain(domain)` — DNS, IP
- `whois_lookup(domain)` — registration info
- `scan_ports(ip)` — port scan
- `shodan_lookup(ip)` — Shodan data

### Phase 3: Entity Expansion
1. From Phase 2 results, extract new entities:
   - Email found in GitHub profile → search_email
   - Phone found in profile → search_phone
   - Domain found → search_domain
   - Other usernames → run_maigret
2. Save ALL evidence: `save_evidence(investigation_id, tool_name, target, target_type, result)`
3. Use `run_profiler(target, target_type, max_depth=2)` for automated BFS expansion

### Phase 4: Deep Dive
1. For each found profile, try `scrape_profile(url)` for bio/avatar/posts
2. Cross-reference: same avatar across platforms = same person
3. Check breach data for all found emails
4. Generate dorks for all found entities

### Phase 5: Resolution & Report
1. `resolve_entities(entities)` — merge into golden record
2. `query_evidence(investigation_id)` — get all evidence
3. `get_investigation(investigation_id)` — full case file
4. Synthesize findings into Vietnamese markdown report:
   - Tổng quan (Executive Summary)
   - Thực thể phát hiện (Discovered Entities)
   - Mối quan hệ (Relationships)
   - Đánh giá rủi ro (Risk Assessment)
   - Khuyến nghị下一步 (Next Steps)

## Output Format
Always produce a Vietnamese markdown report with:
- Investigation ID
- Seed and seed type
- Timeline of discovery
- All entities found (with confidence)
- Cross-platform linkages
- Risk assessment
- Evidence citations (tool_name, timestamp)

## Important Notes
- ALWAYS save evidence after each tool call
- Ask user before running paid tools (IntelX, Spokeo)
- Respect rate limits — don't hammer APIs
- Use safe mode by default (no NSFW)
- Log consent before investigation
