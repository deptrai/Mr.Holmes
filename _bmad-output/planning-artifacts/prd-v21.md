# PRD: Mr.Holmes v2.1 — Vietnam OSINT Enhancement

> Version: 2.1
> Date: 2026-06-27
> Status: Draft
> Owner: Luisphan

## 1. Problem Statement

Mr.Holmes v2.0 đã hoạt động end-to-end với MCP server, 13 plugins, 27 tools. Tuy nhiên, điều tra thực tế (case `deptraidapxichlo`) cho thấy **gap lớn trong coverage Vietnam**:

- **Không tìm được số điện thoại từ tên** — chỉ trả carrier, không có tên chủ sở hữu
- **Không có thông tin chính phủ** — mã số thuế cá nhân, hồ sơ tòa án, đăng ký doanh nghiệp chi tiết
- **Không scrape được social media Vietnam** — Zalo, Facebook Vietnam, TikTok Vietnam
- **Không có báo chí/archive search** — bài báo cũ, phỏng vấn
- **12/21 engine modules chưa wire vào MCP** — LLM synthesizer, PDF builder, mindmap generator là dead code
- **Không có cross-reference** — AI orchestrator phải manual check overlap giữa evidence

## 2. Target Users

- **OSINT investigators** điều tra cá nhân/doanh nghiệp Vietnam
- **Journalists** cần verify thông tin công dân, doanh nghiệp
- **Due diligence teams** kiểm tra đối tác kinh doanh Vietnam

## 3. Goals

| # | Goal | Success Metric |
|---|------|----------------|
| G1 | Mở rộng coverage Vietnam-specific sources | +12 plugins mới (Zalo, FB Vn, TikTok Vn, VnCourt, VnTax, VnNews, XInvoice, Truecaller, Snusbase, Instagram, LinkedIn, AvatarReverse) |
| G2 | Wire 3 engine modules vào MCP | synthesize_report, export_pdf, generate_mindmap tools hoạt động |
| G3 | Cross-reference engine | cross_reference tool tìm overlap + suggest new targets |
| G4 | Social media scraping | Facebook, Instagram, TikTok, Zalo profiles scrape được qua StealthBrowser |
| G5 | Government records | VnTax, VnCourt trả thông tin từ tracuunnt.gdt.gov.vn, thuvienphapluat.vn |
| G6 | Phone → owner name | Truecaller plugin trả tên chủ sở hữu số điện thoại |
| G7 | News archive search | VnNews plugin trả bài báo từ Tuổi Trẻ, VnExpress, Thanh Niên |
| G8 | Avatar reverse search | AvatarReverse plugin tìm profiles dùng cùng avatar |
| G9 | Total MCP tools | 42 tools (27 v2.0 + 15 v2.1) |

## 4. Non-Goals

- **Financial intelligence** (bank accounts, credit scores) — require legal authorization
- **Real-time tracking** (GPS location, live monitoring) — privacy/legal concerns
- **Face recognition ML models** — heavy, defer to v2.2
- **Telegram/Discord OSINT** — niche, lower priority
- **Legacy CLI enhancement** — focus on MCP path

## 5. User Stories

### Epic 16: Vietnam Government Records

**US-16.1: VnTax Plugin**
> As an investigator, I want to look up a tax code on tracuunnt.gdt.gov.vn so that I get taxpayer name, address, tax department, and status.

- Input: tax_id (10-13 digits) OR business_name
- Output: orgType, taxID, name, address, taxDepartment, status
- Source: tracuunnt.gdt.gov.vn (Playwright scrape) + XInvoice API (fallback)
- AC1: Plugin returns valid JSON for 10-digit tax code
- AC2: Plugin handles CAPTCHA (log warning, return partial)
- AC3: Rate limit 1 req/3s

**US-16.2: VnCourt Plugin**
> As an investigator, I want to search court records by name so that I find public court cases involving a person.

- Input: name (Vietnamese)
- Output: list of cases (case_id, court, date, parties, summary)
- Source: thuvienphapluat.vn (Playwright scrape)
- AC1: Returns cases matching name
- AC2: Handles no-results gracefully
- AC3: Rate limit 1 req/5s

**US-16.3: XInvoice Plugin**
> As an investigator, I want to look up tax info via API so that I get structured data without scraping.

- Input: tax_id
- Output: orgType, taxID, name, address, taxDepartment, status
- Source: api.xinvoice.vn
- AC1: Returns valid JSON for valid tax code
- AC2: Handles 404 (invalid tax code)
- AC3: Requires MH_XINVOICE_API_KEY

### Epic 17: Vietnam Social Media

**US-17.1: FacebookVn Plugin**
> As an investigator, I want to scrape a Facebook profile so that I get name, bio, location, work, education, friends count.

- Input: username OR profile URL
- Output: name, bio, location, work, education, friends_count, profile_pic
- Source: mbasic.facebook.com (StealthBrowser)
- AC1: Returns profile data for public profile
- AC2: Handles login wall (return partial + warning)
- AC3: Uses StealthBrowser with anti-detection

**US-17.2: Instagram Plugin**
> As an investigator, I want to scrape an Instagram profile so that I get bio, followers, posts count, external URL.

- Input: username
- Output: bio, followers_count, following_count, posts_count, external_url, profile_pic
- Source: instagram.com (StealthBrowser)
- AC1: Returns profile data for public account
- AC2: Handles private account (return status=private)
- AC3: Uses StealthBrowser

**US-17.3: TikTokVn Plugin**
> As an investigator, I want to scrape a TikTok profile so that I get bio, followers, video count, and extract email/phone if exposed.

- Input: username
- Output: bio, followers_count, following_count, video_count, profile_pic, email (if any), phone (if any)
- Source: tiktok.com (StealthBrowser) + Toutatis (email/phone extraction)
- AC1: Returns profile data for public account
- AC2: Toutatis integration for email/phone extraction
- AC3: Uses StealthBrowser

**US-17.4: Zalo Plugin**
> As an investigator, I want to look up a Zalo profile so that I get name, avatar, status.

- Input: phone number OR zalo ID
- Output: name, avatar, status, cover_photo
- Source: zalo.me (StealthBrowser)
- AC1: Returns profile data for public Zalo ID
- AC2: Handles private/locked profile
- AC3: Uses StealthBrowser

**US-17.5: LinkedIn Plugin**
> As an investigator, I want to scrape a LinkedIn profile so that I get name, title, company, education, location.

- Input: profile URL OR name + company
- Output: name, headline, company, education, location, connections_count
- Source: linkedin.com (StealthBrowser)
- AC1: Returns profile data for public profile
- AC2: Handles auth wall (return partial + warning)
- AC3: Uses StealthBrowser

### Epic 18: Phone Enrichment

**US-18.1: Truecaller Plugin**
> As an investigator, I want to reverse lookup a phone number so that I get the owner's name.

- Input: phone number (international format)
- Output: name, email (if any), address (if any), spam_score
- Source: truecaller.com API
- AC1: Returns owner name for valid number
- AC2: Handles not-found gracefully
- AC3: Requires MH_TRUECALLER_API_KEY

### Epic 19: Breach Database Enhancement

**US-19.1: Snusbase Plugin**
> As an investigator, I want to search Snusbase so that I get breach data from additional sources.

- Input: email, username, phone, IP
- Output: breach records (source, date, data_fields)
- Source: snusbase.com API
- AC1: Returns breach records for exposed targets
- AC2: Handles no-results
- AC3: Requires MH_SNUSBASE_API_KEY

### Epic 20: News & Media

**US-20.1: VnNews Plugin**
> As an investigator, I want to search Vietnam news archives so that I find articles mentioning a person or company.

- Input: name OR company name
- Output: list of articles (title, url, date, source, snippet)
- Source: Google News API + site-specific dorks (tuoitre.vn, vnexpress.net, thanhnien.vn)
- AC1: Returns articles matching name
- AC2: Supports date range filter
- AC3: Rate limit 1 req/2s

### Epic 21: Avatar Reverse Search

**US-21.1: AvatarReverse Plugin**
> As an investigator, I want to reverse search an avatar image so that I find other profiles using the same image.

- Input: image URL
- Output: list of URLs where same image appears
- Source: Google Images + Yandex Images + FaceCheck.id API
- AC1: Returns matching URLs
- AC2: FaceCheck.id for face matching (requires API key)
- AC3: Google/Yandex for exact image match (free)

### Epic 22: Engine Modules Wire

**US-22.1: synthesize_report MCP tool**
> As an investigator, I want to generate an LLM-synthesized report so that I get a narrative summary of all evidence.

- Input: investigation_id
- Output: markdown report (narrative summary)
- Source: Core/engine/llm_synthesizer.py
- AC1: Returns markdown report for investigation
- AC2: Uses configured LLM (Gemini/OpenAI)
- AC3: Includes all evidence in report

**US-22.2: export_pdf MCP tool**
> As an investigator, I want to export an investigation to PDF so that I can share it.

- Input: investigation_id
- Output: PDF file path
- Source: Core/engine/pdf_builder.py
- AC1: Generates PDF with all evidence
- AC2: Includes charts/mindmap if available
- AC3: Returns file path

**US-22.3: generate_mindmap MCP tool**
> As an investigator, I want to generate a mindmap so that I visualize entity relationships.

- Input: investigation_id
- Output: mindmap file path (JSON + PNG)
- Source: Core/engine/mindmap_generator.py
- AC1: Generates mindmap with all entities
- AC2: Shows relationships between entities
- AC3: Returns file path

### Epic 23: Cross-Reference Engine

**US-23.1: cross_reference MCP tool**
> As an investigator, I want to cross-reference evidence so that I find overlaps and suggested new targets.

- Input: investigation_id
- Output: overlaps (emails/usernames/phones appearing in multiple evidence), suggested_targets (new targets to investigate)
- Source: Evidence Store query
- AC1: Finds emails appearing in multiple evidence rows
- AC2: Suggests new targets based on extracted clues
- AC3: Returns JSON with overlaps + suggestions

## 6. Technical Architecture

See `ARCHITECTURE-SPINE.md` for detailed architecture decisions.

### Key Principles
- **Plugin-first**: mọi source mới là plugin implement IntelligencePlugin Protocol
- **StealthBrowser**: social media scrapers dùng Playwright stealth
- **Stage routing**: Vietnam plugins stage=3, chạy khi có clues
- **Rate limiting**: 1 req/3s cho gov portals, 1 req/2s cho news

### New Env Vars
```
MH_TRUECALLER_API_KEY=
MH_SNUSBASE_API_KEY=
MH_XINVOICE_API_KEY=
MH_FACECHECK_API_KEY=
```

## 7. Sprints

### Sprint 1 (P0 — Vietnam Core + Engine Wire)
- US-22.1: synthesize_report
- US-22.2: export_pdf
- US-22.3: generate_mindmap
- US-23.1: cross_reference
- US-16.1: VnTax plugin
- US-16.2: VnCourt plugin
- US-16.3: XInvoice plugin
- US-20.1: VnNews plugin

### Sprint 2 (P0 — Social Media)
- US-17.1: FacebookVn plugin
- US-17.2: Instagram plugin
- US-17.3: TikTokVn plugin
- US-17.4: Zalo plugin
- US-17.5: LinkedIn plugin

### Sprint 3 (P1 — Enrichment)
- US-18.1: Truecaller plugin
- US-19.1: Snusbase plugin
- US-21.1: AvatarReverse plugin

## 8. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Zalo/FB block bots | Cao | StealthBrowser, proxy rotation |
| Gov portals CAPTCHA | Trung bình | Log warning, return partial, manual fallback |
| Truecaller API expensive | Trung bình | Free tier first, user provides key |
| Snusbase paid only | Thấp | Optional plugin, user provides key |
| LinkedIn auth wall | Cao | Return partial + warning |
| News sites anti-bot | Trung bình | Use Google News API, not direct scrape |

## 9. Success Metrics

| Metric | v2.0 | v2.1 Target |
|--------|------|-------------|
| Plugins | 13 | 25 |
| MCP tools | 27 | 42 |
| Vietnam sources | 2 (VnBusiness, VnPhone) | 8 (+VnTax, VnCourt, VnNews, XInvoice, Zalo, FacebookVn) |
| Social media scrapers | 0 | 5 (FB, IG, TikTok, Zalo, LinkedIn) |
| Engine modules wired | 9/21 | 12/21 |
| Cross-reference | Manual | Automated |
| Report generation | Manual | LLM + PDF + Mindmap |
