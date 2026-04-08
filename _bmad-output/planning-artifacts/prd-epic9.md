---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-Mr.Holmes-Epic9.md"
  - "_bmad-output/planning-artifacts/research/technical-osint-profiling-system-research-2026-04-05.md"
  - "docs/project-context.md"
  - "docs/architecture.md"
  - "docs/component-inventory.md"
  - "docs/project-overview.md"
workflowType: 'prd'
classification:
  projectType: cli_tool
  domain: cybersecurity_osint
  complexity: medium_high
  projectContext: brownfield
project_name: Mr.Holmes
epic: 9
status: complete
---

# Product Requirements Document — Mr.Holmes Epic 9

**Author:** Luisphan
**Date:** 2026-04-05

## Executive Summary

Mr.Holmes là OSINT CLI tool Python mã nguồn mở. Epics 1-8 xây dựng nền tảng: async engine, plugin system, BFS recursive profiler, LLM synthesis. Khi analyst có 1 email cần điều tra, hệ thống hiện trả về danh sách URLs và breach names — không có tên thật, SĐT, location, hay personality.

**Epic 9 giải quyết bài toán identity fragmentation:** cùng 1 người có hàng chục accounts phân tán, mỗi platform lộ 1 mảnh thông tin. Epic 9 tự động thu thập và merge các mảnh đó thành 1 Golden Record — profile thống nhất với tên thật, SĐT, location, nghề nghiệp, hành vi, và personality. Tất cả từ 1 manh mối ban đầu, trong 15-20 phút, không thao tác thủ công.

**Target users:** OSINT researchers và cybersecurity analysts cần xây dựng hồ sơ nhanh từ dữ liệu tối thiểu. Secondary: ethical hackers (recon phase), private investigators, nhà báo điều tra.

**Vấn đề đo được:** Holehe test với `deptraidapxichlo@gmail.com` trả về 79 registered services trong khi username scan 150 sites chỉ tìm được 19. 60+ platforms bị bỏ sót. Quy trình thủ công mất 2-4 giờ/target.

**Differentiator:** Identity Synthesis Engine — Entity Resolver merge dữ liệu từ 10+ nguồn bằng Jaro-Winkler name matching, pHash avatar comparison, bio cosine similarity → Golden Record với confidence score. Coverage: Maigret 3000+ sites (vs Sherlock 400) + Holehe 120+ services + AI personality analysis. Miễn phí. Không có tool open-source nào cung cấp trải nghiệm tương đương; Maltego làm được nhưng $6,600/năm.

**Project context:** Brownfield — extend existing plugin system, BFS engine, LLM synthesizer. 3 architectural additions cần thiết: `ProfileEntity` data model, multi-stage orchestration, cache layer. CLI tool (interactive + scriptable), Python 3.9+, medium-high complexity.

## Success Criteria

### User Success

- Analyst nhập 1 email → hệ thống tự tìm ra tên thật từ GitHub commits mà analyst chưa biết — không cần mở browser
- 2-4 giờ thủ công → 15-20 phút automated first pass (≥6x faster)
- Golden Record có confidence score ≥ 0.75 → đủ tin tưởng để báo cáo

### Business Success

| Metric | Baseline | Target |
|--------|----------|--------|
| Sites scanned | 150 | 3000+ |
| Data fields per profile | 2 (URL, breach) | 10+ (name, phone, location, bio, avatar, interests, active_hours, confidence) |
| Enrichment time | 2-4h manual | 15-20 min auto |
| Entity resolution confidence | N/A | ≥ 0.75 avg |
| Cache hit rate | 0% | ≥ 60% |

### Technical Success

- Plugin isolation: thêm plugin mới không cần sửa engine core
- Graceful degradation: 1 plugin fail không crash toàn pipeline
- Test coverage ≥ 80% cho EntityResolver, ProfileEntity, và 3 plugin đầu tiên
- LLM failover: Google AI Studio → v98store trong < 2 giây

## Product Scope

### MVP — Phase 1 (Tuần 1-2)

**Mục tiêu:** 1 email → Golden Record với tên thật + platform list trong 20 phút. Đủ để chứng minh concept.

| Story | Component | Rationale |
|-------|-----------|-----------|
| 9.1 | `ProfileEntity` data model | Foundation — không có, không merge được gì |
| 9.2 | Multi-stage BFS orchestration | Foundation — không có, plugins chạy sai thứ tự |
| 9.3 | `HolehPlugin` | 120+ services từ 1 email, extract recovery phone/email |
| 9.4 | `MaigretPlugin` | 3000+ sites, extract tên/bio/avatar |
| 9.5 | Cache layer (SQLite, TTL 24h) | Không có → re-query mọi thứ mỗi lần, bị ban |
| 9.6 | CLI integration (Option 16 update) | User-facing entry point |

**Phase 1 done khi:** E2E `deptraidapxichlo@gmail.com` → Golden Record confidence ≥ 0.75, zero crashes từ plugin failures.

### Growth — Phase 2 (Tuần 3-4)

- `GitHubPlugin` — tên thật từ commits (highest value, lowest ToS risk)
- `NumverifyPlugin` — xác minh SĐT từ Holehe recovery
- `InstagramPlugin` via Instaloader — opt-in, bio + GPS posts
- `EntityResolver` — Golden Record merge với confidence scoring đầy đủ
- Enhanced LLM synthesis với ProfileEntity structured context

### Vision — Phase 3 (Tuần 5-6)

- `RedditPlugin`, `YouTubePlugin`, `HunterPlugin`
- Cross-Platform Bridge (username bridging qua avatar/recovery)
- Personality Analysis (Big-5 traits từ LLM)
- Behavioral Timeline (activity patterns theo thời gian)
- `--profile` batch CLI flag + exit codes

### Risk Mitigation

- _Maigret Python ≥3.10 conflict_ → subprocess wrapper + fallback Sherlock
- _Instagram ban_ → opt-in only, stop-on-429, không block Phase 1
- _Entity resolution false positives_ → merge chỉ khi ≥ 2 independent signals
- _Solo developer burnout_ → mỗi phase deliverable rõ ràng, có thể pause sau Phase 1

## User Journeys

### Journey 1 — Minh, OSINT Analyst (Primary — Success Path)

Minh nhận task điều tra tài khoản đáng ngờ, chỉ có email `deptraidapxichlo@gmail.com`.

**Trước:** 19 platform URLs, 5 breach names. Mở từng tab thủ công. 3 tiếng, vẫn không biết tên thật.

**Với Epic 9:** Option 16 → nhập email. Holehe phát hiện 79 services, Maigret extract bio từ Pinterest ("Nguyen Van A — DJ/Producer"), GitHub API tìm `author.name = "Nguyen Van A"`, Instagram (opt-in) lấy GPS từ 3 posts. 18 phút → Golden Record: tên thật, thành phố, nghề nghiệp, 12 platforms xác nhận, confidence 0.81.

**Capabilities:** multi-stage pipeline, ProfileEntity, Holehe + Maigret + GitHub + Instagram plugins, Golden Record merge.

### Journey 2 — Lan, Ethical Hacker (Primary — Edge Case)

Lan trong recon phase pentest (written authorization). Target chỉ có username, không có email.

Maigret quét 3000+ sites → tìm GitHub profile với email công khai. BFS thêm email vào queue depth 1. Holehe phát hiện thêm 40 services. Instagram bị rate-limited → fail gracefully. Kết quả: partial Golden Record confidence 0.61 + cảnh báo "low confidence, 2 sources failed".

**Capabilities:** username-first seed, BFS email discovery, graceful degradation, confidence-aware reporting.

### Journey 3 — Hoa, Journalist (Secondary — Research)

Hoa muốn verify danh tính online nhân vật công chúng. Chỉ biết CLI cơ bản.

Option 16 → nhập email → hệ thống hỏi "Instagram có ToS risk — bật không?" → Hoa chọn No. 20 phút sau nhận `ai_report.md` với "Confirmed facts" tách biệt "AI-generated hypotheses". Cô dùng phần facts để verify.

**Capabilities:** opt-in confirmation, fact vs hypothesis separation, ephemeral session.

### Journey 4 — Dev Contributor (Integration)

Contributor muốn thêm plugin Telegram username lookup.

Đọc `docs/development-guide.md`, implement `IntelligencePlugin` (3 methods), drop vào `Core/plugins/`. Restart → plugin tự appear, tự inject API key từ `.env`.

**Capabilities:** plugin auto-discovery, zero-config registration, development guide.

### Journey Requirements Summary

| Journey | Capabilities Required |
|---------|----------------------|
| Analyst success | Multi-stage pipeline, Phase 1-2 plugins, Golden Record |
| Ethical hacker | Username seed, BFS discovery, graceful degradation, confidence scoring |
| Journalist | Opt-in prompts, fact/hypothesis separation, ephemeral sessions |
| Dev contributor | Plugin auto-discovery, development guide |

## Domain-Specific Requirements

### Compliance & Ethical Constraints

- Mỗi plugin phải có `tos_risk` flag (`safe` / `tos_risk` / `ban_risk`) — hiển thị cho user trước khi chạy
- High-risk plugins (Instagram, LinkedIn) cần explicit opt-in confirmation
- Tool hiển thị authorized-use disclaimer khi khởi động profiling mode
- Golden Records ephemeral by default — không sync lên bất kỳ server nào
- Data retention: auto-delete sau 30 ngày trừ khi user giữ lại

### Technical Constraints

- Mỗi plugin implement exponential backoff; global semaphore ≤ 5 concurrent requests/domain
- API keys trong `.env`, không hardcode, không log, không include trong reports
- Tất cả AI-generated content gắn tag `[AI-generated hypothesis]`
- Confidence < 0.5 → hiển thị cảnh báo rõ ràng
- Maigret chạy qua subprocess — stdout/stderr sanitize trước khi parse

### Integration Contract

- Plugin Protocol: duck-typed `IntelligencePlugin` với `check()`, `run()`, `extract_clues()` — backward compatible
- Plugins trả về `clues` list với type annotation → BFS route đúng stage
- Mỗi plugin declare `cache_ttl` và `cache_key_fn` — cache layer tự handle
- `llm_synthesizer.py` nhận `ProfileEntity` object, không phải raw dict

### Risk Table

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Instagram ban | Cao | Opt-in only, rate limit 1 req/5s, stop-on-429 |
| Maigret Python version conflict | Trung bình | Subprocess wrapper với virtualenv isolation |
| API key leak trong reports | Cao | Sanitize tất cả env vars khỏi output |
| LLM hallucination | Cao | Label rõ, confidence threshold, source attribution |
| Holehe rate limit | Trung bình | Async semaphore, retry với backoff |

## Innovation & Novel Patterns

### Detected Innovation Areas

**Identity Synthesis (chưa có trong open-source):** Sherlock, theHarvester, Holehe hoạt động độc lập. Epic 9 là tool open-source đầu tiên tự động cross-correlate kết quả từ 10+ nguồn thành 1 Golden Record với confidence scoring — entity resolution, không phải aggregation.

**AI-Augmented OSINT CLI:** LLM infer personality traits, predict behavior patterns từ data patterns. Analyst nhận insight ("active 10pm-2am, Vietnamese timezone, DJ by hobby but Python developer professionally") thay vì đọc thủ công hàng giờ.

**BFS-Driven Clue Chaining:** Holehe trả về partial phone `+84 *** *** 169` → BFS detect → Numverify confirm carrier → add clue "Vietnam mobile, Viettel". Automatic clue chaining theo graph traversal.

### Competitive Landscape

| Tool | Sites | Entity Resolution | AI Analysis | Cost |
|------|-------|------------------|-------------|------|
| Maltego | 500+ | Manual (paid) | Không có | $6,600/năm |
| SpiderFoot | 200+ | Không có | Không có | Paid tier |
| Sherlock | 400 | Không có | Không có | Free |
| **Mr.Holmes Epic 9** | **3000+** | **Auto Golden Record** | **LLM Personality** | **Free** |

### Validation Approach

- E2E với `deptraidapxichlo@gmail.com` (ground truth: 19 platforms known) → validate coverage gap
- Confidence score calibration: test 10+ profiles, đo false positive rate của entity merges
- Personality analysis: blind review — analyst đọc profile thật rồi so với AI output

## CLI Tool Specific Requirements

### Command Interface

```bash
# Interactive mode (Option 16 — Complete Profile Mode)
python3 MrHolmes.py

# Batch mode
python3 MrHolmes.py --profile deptraidapxichlo@gmail.com
python3 MrHolmes.py --profile deptraidapxichlo --type USERNAME
python3 MrHolmes.py --profile +84928881690 --type PHONE --depth 2
python3 MrHolmes.py --profile EMAIL --output all
```

### Output Formats

| Format | Path | Audience |
|--------|------|----------|
| `raw_data.json` | `GUI/Reports/Autonomous/{target}/` | Developer, API consumers |
| `ai_report.md` | `GUI/Reports/Autonomous/{target}/` | Analyst, journalist |
| `mindmap.html` | `GUI/Reports/Autonomous/{target}/` | Visual review |
| `golden_record.json` | `GUI/Reports/Autonomous/{target}/` | Machine-readable ProfileEntity |

### Config & Scripting

- API keys và plugin toggles qua `.env` (`MH_HOLEHE_ENABLED`, `MH_GITHUB_TOKEN`, `MH_CACHE_TTL`, etc.)
- Exit codes: `0` success, `1` no results, `2` all plugins failed, `3` invalid input
- stdout: progress logs → stderr; final report path → stdout
- Non-TTY: skip opt-in prompts, dùng `.env` defaults
- Backward compatible: `--username`, `--email`, `--phone` flags vẫn hoạt động

## Functional Requirements

### Identity Input & Seed Management

- **FR1:** Analyst có thể khởi động profiling từ 1 email, 1 username, hoặc 1 số điện thoại
- **FR2:** System tự detect loại input (EMAIL/USERNAME/PHONE) nếu không chỉ định
- **FR3:** Analyst có thể chỉ định max depth cho BFS traversal
- **FR4:** System cho phép chạy profiling từ batch CLI không cần interactive input

### Multi-Source Data Collection

- **FR5:** System kiểm tra email trên 120+ services qua Holehe, extract recovery phone/email
- **FR6:** System quét username trên 3000+ sites qua Maigret, extract tên thật/bio/avatar URL
- **FR7:** System tra cứu breach data cho email qua LeakLookup và HIBP
- **FR8:** System lấy tên thật từ GitHub commit history qua public API
- **FR9:** System xác minh và enrich số điện thoại qua Numverify (carrier, region, validity)
- **FR10:** System lấy bio, avatar, geo-tagged posts từ Instagram (opt-in)
- **FR11:** System phân tích interests và writing patterns từ Reddit public API
- **FR12:** System discover email addresses từ domain qua Hunter.io
- **FR13:** System phân tích YouTube channel khi có username

### BFS Clue Chaining & Orchestration

- **FR14:** System tự động extract clues (email, username, phone, domain) từ plugin results
- **FR15:** System route clues đúng stage theo type
- **FR16:** System không scan cùng 1 entity 2 lần trong 1 session (deduplication)
- **FR17:** System chạy các plugin trong cùng stage song song (async)
- **FR18:** 1 plugin fail không crash toàn bộ pipeline

### Golden Record & Entity Resolution

- **FR19:** System merge kết quả từ nhiều nguồn thành 1 ProfileEntity (Golden Record)
- **FR20:** System tính confidence score (0.0-1.0) cho mỗi field trong Golden Record
- **FR21:** System hiển thị cảnh báo khi confidence < 0.5 cho một claim
- **FR22:** System track source attribution cho mỗi data point trong Golden Record
- **FR23:** System không merge 2 entities trừ khi có ≥ 2 independent signals xác nhận

### Caching & Performance

- **FR24:** System cache kết quả plugin query với TTL configurable
- **FR25:** System tái sử dụng cached results thay vì re-query nếu cache còn valid
- **FR26:** User có thể force-refresh cache cho 1 target cụ thể

### AI Synthesis & Reporting

- **FR27:** System tạo AI report với "Confirmed Facts" tách biệt "AI-generated Hypotheses"
- **FR28:** System tạo interactive mindmap HTML từ Golden Record
- **FR29:** System export Golden Record dạng structured JSON
- **FR30:** LLM tổng hợp personality traits từ behavioral patterns
- **FR31:** System failover sang backup LLM endpoint nếu primary không respond

### Safety, Ethics & Access Control

- **FR32:** System hiển thị ToS risk level (safe/tos_risk/ban_risk) cho mỗi plugin trước khi chạy
- **FR33:** System yêu cầu explicit opt-in confirmation trước khi chạy high-risk plugins
- **FR34:** System hiển thị authorized-use disclaimer khi khởi động profiling mode
- **FR35:** System không lưu API keys vào output files hay logs
- **FR36:** Golden Records ephemeral by default — không persist sau session trừ khi user chọn lưu

### Plugin Extensibility

- **FR37:** Developer thêm plugin mới bằng cách implement `IntelligencePlugin` và drop vào `Core/plugins/`
- **FR38:** System tự discover và load plugin mới không cần register thủ công
- **FR39:** Plugin mới tự nhận API key từ `.env` theo naming convention

## Non-Functional Requirements

### Performance

- **NFR1:** Pipeline Phase 1 (Holehe + Maigret) hoàn thành trong ≤ 20 phút cho 1 target
- **NFR2:** Cache lookup trả về kết quả trong ≤ 100ms
- **NFR3:** ≤ 5 concurrent HTTP requests/domain tại 1 thời điểm
- **NFR4:** LLM synthesis ≤ 60 giây; failover sang backup ≤ 2 giây nếu primary timeout
- **NFR5:** Memory footprint ≤ 512MB (chạy được trên máy cá nhân thông thường)

### Security

- **NFR6:** API keys không xuất hiện trong bất kỳ output file nào
- **NFR7:** Golden Records không gửi lên bất kỳ external server nào — tất cả xử lý local
- **NFR8:** Cache database SQLite lưu local, không sync cloud
- **NFR9:** LLM prompts không include raw API keys hay credentials trong payload
- **NFR10:** Subprocess output từ Maigret phải được sanitize trước khi parse

### Integration

- **NFR11:** Plugin Protocol backward compatible — plugin Epic 8 vẫn load được trong Epic 9
- **NFR12:** Holehe integration hoạt động với holehe ≥ 1.4.0 (async/trio API)
- **NFR13:** Maigret integration qua subprocess với Python ≥ 3.10; core vẫn Python 3.9+
- **NFR14:** LLM integration hoạt động với bất kỳ OpenAI-compatible endpoint
- **NFR15:** Cache layer transparent với plugins — plugin không cần biết cache tồn tại
