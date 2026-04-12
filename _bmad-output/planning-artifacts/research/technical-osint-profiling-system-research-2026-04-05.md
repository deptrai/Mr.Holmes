---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'OSINT Complete Profiling System — Mở rộng Mr.Holmes thành hệ thống profiling hoàn chỉnh'
research_goals: 'Từ 1 manh mối (email/username/SĐT) → profiles đầy đủ: tên thật, SĐT, địa chỉ, nghề nghiệp, timeline, mạng xã hội, hành vi, tính cách, bạn bè, xu hướng'
user_name: 'Luisphan'
date: '2026-04-05'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-04-05
**Author:** Luisphan
**Research Type:** Technical

---

## Research Overview

Nghiên cứu kỹ thuật cho việc mở rộng Mr.Holmes OSINT tool thành hệ thống profiling hoàn chỉnh. Từ 1 manh mối ban đầu (email, username, SĐT) → xây dựng profiles đầy đủ bao gồm tên thật, SĐT, địa chỉ, nghề nghiệp, timeline, mạng xã hội, hành vi, tính cách, bạn bè, xu hướng.

---

## Technical Research Scope Confirmation

**Research Topic:** OSINT Complete Profiling System — Mở rộng Mr.Holmes thành hệ thống profiling hoàn chỉnh
**Research Goals:** Từ 1 manh mối (email/username/SĐT) → profiles đầy đủ

**Technical Research Scope:**

- Architecture Analysis - plugin mới, data model mở rộng, pipeline enrichment
- Implementation Approaches - holehe, maigret, instaloader, phone APIs
- Technology Stack - Python OSINT libraries, API services
- Integration Patterns - cross-platform username bridging, BFS social graph, LLM analysis
- Performance Considerations - rate limiting, caching, anti-detection

**Scope Confirmed:** 2026-04-05

---

## Technology Stack Analysis

### Thư viện Python OSINT — Công cụ chính cho Profiling

| Tool | Chức năng | Sites/APIs | Ngôn ngữ | Free? | Tích hợp Mr.Holmes |
|------|----------|-----------|----------|-------|-------------------|
| **Maigret** | Username → profiles trên 3000+ sites | 3000+ (vs Sherlock 400) | Python | ✅ | **Ưu tiên #1** — thay thế username scan 150 sites |
| **Holehe** | Email → registered services | 120+ services | Python | ✅ | **Ưu tiên #2** — đã test: 79 results |
| **Sherlock** | Username → social profiles | 400+ sites | Python | ✅ | Thay bằng Maigret (tốt hơn) |
| **PhoneInfoga** | Phone → carrier, location, owner | Numverify, Google | **Go** (v2+) | ✅ | Cần wrapper hoặc REST API call |
| **theHarvester** | Email/domain → subdomains, emails, IPs | Google, Bing, Shodan | Python | ✅ | Bổ sung cho SearxNG |
| **Socialscan** | Email/username → existence check | 20+ platforms | Python | ✅ | Bổ sung cho Holehe |

_Sources: [OSINT Bible](https://github.com/frangelbarrera/OSINT-BIBLE), [Maigret PyPI](https://pypi.org/project/maigret/), [Bellingcat Toolkit](https://bellingcat.gitbook.io/toolkit/more/all-tools/maigret)_

### Maigret vs Sherlock vs Mr.Holmes hiện tại

| Tiêu chí | Mr.Holmes (hiện tại) | Sherlock | Maigret |
|----------|---------------------|---------|---------|
| **Sites checked** | 150 | 400+ | **3000+** |
| **Profile extraction** | 19 sites (API-based) | ❌ Username only | ✅ Tên, ảnh, bio, links |
| **Report formats** | TXT, JSON | TXT, CSV | **HTML, PDF, TXT, JSON, XMind mindmap** |
| **Auto-discovery** | ✅ BFS clue extraction | ❌ | ✅ Tìm IDs → search tiếp |
| **Tor/I2P** | ❌ | ❌ | ✅ |
| **False positive handling** | Basic (status code) | Medium | **Advanced** (multi-strategy) |

_Sources: [Maigret README](https://github.com/soxoj/maigret/blob/main/README.md), [Maigret Grokipedia](https://grokipedia.com/page/Maigret_OSINT_tool)_

### API Services — Free Tier cho OSINT

| Service | Chức năng | Free Tier | API Type |
|---------|----------|-----------|----------|
| **Hunter.io** | Email finder + verification | 25 requests/month | REST |
| **Numverify** | Phone validation + geolocation | 100 requests/month | REST |
| **BreachDirectory** | Breach database search | Limited free | REST |
| **IntelX** | Leak search, dark web | 10 requests/day | REST |
| **GitHub API** | User/commit search by email | 60 req/h (no key), 5000/h (key) | REST |
| **Nominatim** | Geocoding (address ↔ GPS) | Free (rate limited) | REST |

_Sources: [Hunter.io API](https://hunter.io/api/email-finder), [cipher387/API-s-for-OSINT](https://github.com/cipher387/API-s-for-OSINT)_

### Social Media Scraping — Thư viện chuyên dụng

| Platform | Thư viện | Dữ liệu | Trạng thái (2026) |
|----------|---------|---------|-------------------|
| **Instagram** | Instaloader | Bio, ảnh, posts, followers, following, stories, GPS | ✅ Đang hoạt động |
| **TikTok** | tiktok-scraper, TikTokApi | Bio, video count, followers, likes | ⚠️ Anti-bot thay đổi |
| **Twitter/X** | Nitter scraping, snscrape | Tweets, bio, followers | ⚠️ Cần proxy |
| **Reddit** | PRAW (Python Reddit API) | Posts, comments, subreddits, karma | ✅ Official API |
| **YouTube** | youtube-dl, YouTube Data API v3 | Channel info, videos, subscribers | ✅ Official API |
| **LinkedIn** | linkedin-api (unofficial) | Profile, experience, education | ⚠️ Account lock risk |

_Sources: [Social-Media-OSINT-Tools-Collection](https://github.com/osintambition/Social-Media-OSINT-Tools-Collection), [ShadowDragon](https://shadowdragon.io/blog/best-osint-tools/)_

### AI/LLM trong OSINT — Xu hướng 2025-2026

Các nền tảng OSINT hàng đầu đã tích hợp AI:
- **Babel X**: NLP đa ngôn ngữ (200+ ngôn ngữ) cho social media analysis
- **ShadowDragon**: ML clustering cho social graph discovery
- **Social Links**: AI entity resolution + relationship mapping

Mr.Holmes hiện đã có LLM synthesis (Gemini/GPT) — cần mở rộng thêm:
- **Personality analysis** từ writing style (posts, comments)
- **Behavioral profiling** từ activity timestamps, platforms used
- **Entity resolution** (merge duplicate identities across platforms)
- **Sentiment analysis** trên content

_Sources: [AI-Powered OSINT Tools 2026](https://www.webasha.com/blog/ai-powered-osint-tools-in-2025-how-artificial-intelligence-is-transforming-open-source-intelligence-gathering), [SOCMINT](https://www.osint.industries/post/social-media-intelligence-socmint-in-modern-investigations)_

### PhoneInfoga — Phone OSINT (Lưu ý quan trọng)

⚠️ **PhoneInfoga v2+ đã chuyển sang Go** — không còn là Python library.
- Cần gọi qua REST API (PhoneInfoga serve mode) hoặc subprocess
- Trạng thái: "stable but unmaintained" — có thể bị archive
- **Giải pháp thay thế**: Tự xây dựng phone plugin sử dụng Numverify API + phonenumbers library (đã có trong Mr.Holmes)

_Sources: [PhoneInfoga GitHub](https://github.com/sundowndev/phoneinfoga), [PhoneInfoga Docs](https://sundowndev.github.io/phoneinfoga/)_

---

## Integration Patterns Analysis

### Pipeline Architecture — Multi-Stage OSINT Enrichment

Dựa trên nghiên cứu về các framework OSINT hàng đầu (Silica-X, DataSploit, Social-Analyzer), mô hình tích hợp tối ưu cho Mr.Holmes:

```
Stage 1: SEED INPUT          Stage 2: IDENTITY EXPANSION       Stage 3: DEEP ENRICHMENT        Stage 4: SYNTHESIS
─────────────────            ──────────────────────────        ────────────────────────         ──────────────────
email/username/phone   →     Holehe (email→79+ services)  →   Instaloader (IG profile)    →   LLM Personality Analysis
                             Maigret (username→3000+ sites)    PRAW (Reddit posts)             Entity Resolution
                             BFS clue extraction               YouTube Data API                 Behavioral Timeline
                             auto:email-prefix/domain          GitHub API (commits→name)        Relationship Mapping
                                                               Numverify (phone→location)       Risk Assessment
```

_Sources: [Social-Analyzer](https://typevar.dev/articles/qeeqbox/social-analyzer), [Silica-X](https://github.com/topics/osint-python), [OSINT Methodology](https://footprintiq.app/username-osint-guide)_

### Cross-Platform Identity Bridge — Mấu chốt kỹ thuật

**Vấn đề:** Holehe xác nhận email `deptraidapxichlo@gmail.com` đăng ký trên Instagram, Discord, GitHub... nhưng username trên các platform đó có thể khác "deptraidapxichlo".

**Giải pháp kỹ thuật — 3 tầng:**

| Tầng | Kỹ thuật | Độ tin cậy | Ví dụ |
|------|---------|-----------|-------|
| **1. Direct match** | Thử username đã biết trên service xác nhận | Cao | Holehe confirms IG → try `deptraidapxichlo` on IG |
| **2. Correlation signals** | So sánh profile data (ảnh, bio, timezone) | Trung bình | Same avatar hash across platforms = same person |
| **3. Recovery info** | "Forgot password" partial phone/email hints | Cao | Spotify shows `+84 *** **69` → phone clue |

**Implementation approach cho Mr.Holmes:**

```python
# Proposed: CrossPlatformBridge plugin
class CrossPlatformBridge:
    async def bridge(self, email: str, confirmed_services: list[str]) -> list[PlatformAccount]:
        results = []
        for service in confirmed_services:
            # Tầng 1: Try known usernames
            for username in known_usernames:
                account = await self._check_username_on_service(service, username)
                if account: results.append(account)

            # Tầng 2: Correlation via avatar hash
            if not results:
                avatar_hash = await self._get_avatar_hash(service, email)
                matches = self._correlate_avatars(avatar_hash, existing_profiles)
                results.extend(matches)
        return results
```

_Sources: [Username OSINT Guide 2026](https://footprintiq.app/username-osint-guide), [Maigret auto-discovery](https://bellingcat.gitbook.io/toolkit/more/all-tools/maigret)_

### Plugin Integration Map — Cách các tool kết nối

```
                    ┌─────────────────┐
                    │   RecursiveProfiler (BFS)   │
                    │   max_depth=2, semaphore=5  │
                    └──────────┬──────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
   │ EXISTING     │     │ NEW (Epic 9) │     │ NEW (Epic 9) │
   │ Plugins      │     │ Plugins      │     │ Enrichers    │
   ├──────────────┤     ├──────────────┤     ├──────────────┤
   │ LeakLookup   │     │ HolehPlugin  │     │ MaigretPlugin│
   │ HIBP         │     │ GitHubPlugin │     │ InstaPlugin  │
   │ Shodan       │     │ HunterPlugin │     │ RedditPlugin │
   │ SearxNG      │     │ NumverifyPlg │     │ YouTubePlugin│
   └──────────────┘     └──────────────┘     └──────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │   ProfileGraph (unified)     │
                    │   nodes + edges + metadata   │
                    └──────────┬──────────────────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
        ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
        │ MindmapGen  │ │ LLMSynth   │ │ ProfileDB   │
        │ (vis.js)    │ │ (Gemini)   │ │ (SQLite)    │
        └─────────────┘ └────────────┘ └─────────────┘
```

### Data Format — ProfileEntity (mới)

Hiện tại ProfileGraph chỉ có nodes (target, type, depth) + edges. Cần mở rộng:

```python
@dataclass
class ProfileEntity:
    """Unified profile entity — tổng hợp từ nhiều sources."""
    target: str                          # email/username/phone
    target_type: str                     # EMAIL/USERNAME/PHONE

    # Identity
    real_name: str | None = None         # Từ GitHub commits, Maigret, IG bio
    display_names: list[str] = field(default_factory=list)  # Aliases
    avatar_urls: list[str] = field(default_factory=list)    # Profile pics

    # Contact
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)

    # Location
    country: str | None = None           # Từ phone (phonenumbers), Strava, IP geo
    city: str | None = None
    gps_coordinates: list[tuple] = field(default_factory=list)  # Từ IG posts, Strava

    # Professional
    occupation: str | None = None        # Từ LinkedIn/Xing, bio analysis
    company: str | None = None
    skills: list[str] = field(default_factory=list)  # Từ GitHub, PyPi

    # Social
    platforms: dict[str, str] = field(default_factory=dict)  # {platform: profile_url}
    followers_total: int = 0
    interests: list[str] = field(default_factory=list)       # Từ tags, subreddits

    # Behavioral
    active_hours: list[int] = field(default_factory=list)    # Hour distribution
    primary_language: str | None = None  # Từ post analysis
    account_ages: dict[str, str] = field(default_factory=dict)  # {platform: created_date}

    # Metadata
    confidence: float = 0.0             # 0-1 overall confidence
    sources: list[str] = field(default_factory=list)  # Source provenance
    last_updated: str = ""
```

### Rate Limiting Strategy — Multi-Source Orchestration

| Source | Rate Limit | Strategy |
|--------|-----------|----------|
| Maigret | Self-throttled (built-in) | Run as subprocess, 1 call/target |
| Holehe | ~2 req/s (per service) | Built-in throttle, 1 call/email |
| GitHub API | 60/h (no key) | API key → 5000/h |
| Hunter.io | 25/month | Cache aggressively, verify-only mode |
| Numverify | 100/month | Cache results, batch lookups |
| Instaloader | ~1 req/2s | Session-based, proxy rotation |
| Reddit PRAW | 60 req/min | Official OAuth, respectful |
| YouTube API | 10,000 units/day | Quota management per API call cost |

**Chiến lược chung:** Dùng `asyncio.Semaphore` per-source (đã có pattern trong Mr.Holmes) + local cache (SQLite) cho repeated lookups.

_Sources: [API-s-for-OSINT](https://github.com/cipher387/API-s-for-OSINT), [Holehe Apify API](https://apify.com/anshumanatrey/holehe-email-osint/api/python)_

---

## Architectural Patterns Analysis

### Pattern 1: Multi-Stage Enrichment Pipeline (Đề xuất cho Mr.Holmes)

Lấy cảm hứng từ Recon-ng (Metasploit-style modules), OSXNT (modular toolkit), và GHunt (JSON output chaining):

```
┌──────────────────────────────────────────────────────────────────┐
│                     ENRICHMENT PIPELINE                          │
│                                                                  │
│  Stage 1         Stage 2           Stage 3          Stage 4      │
│  ┌─────────┐    ┌──────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ SEED    │    │ IDENTITY     │  │ DEEP        │  │SYNTHESIS│ │
│  │ RESOLVE │───▶│ EXPANSION    │──▶│ ENRICHMENT  │──▶│ & AI    │ │
│  │         │    │              │  │             │  │         │ │
│  │email    │    │Holehe(email) │  │Instaloader  │  │LLM      │ │
│  │username │    │Maigret(user) │  │PRAW(Reddit) │  │Entity   │ │
│  │phone    │    │LeakLookup    │  │YouTube API  │  │Resolve  │ │
│  │         │    │HIBP          │  │GitHub API   │  │Timeline │ │
│  │         │    │SearxNG       │  │Numverify    │  │Mindmap  │ │
│  └─────────┘    └──────────────┘  └─────────────┘  └─────────┘ │
│       │                │                │               │        │
│       ▼                ▼                ▼               ▼        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              ProfileEntity (Golden Record)                 │  │
│  │  real_name, phones, emails, platforms, location,           │  │
│  │  occupation, interests, behavioral_data, relationships     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

_Sources: [OSXNT](https://medium.com/@darep682/osxnt-open-source-osint-tools-dbed51413662), [Recon-ng modules](https://github.com/lockfale/OSINT-Framework), [GHunt chaining](http://www.blog.brightcoding.dev/2026/02/03/ghunt-the-revolutionary-osint-framework-for-google-intelligence)_

### Pattern 2: Entity Resolution — "Golden Record" cho OSINT

Kỹ thuật identity resolution từ data science áp dụng cho OSINT profiling:

**Workflow:**
1. **Canonicalization** — Chuẩn hóa data: "deptraidapxichlo" = "DepTraiDapXichLo" = "DEPTRAIDAPXICHLO"
2. **Blocking** — Nhóm candidates theo shared attributes (email domain, username prefix, avatar hash)
3. **Matching** — So sánh entities bằng multi-signal scoring:
   - Username similarity (Jaro-Winkler distance)
   - Avatar hash match (perceptual hashing — pHash)
   - Bio text similarity (cosine similarity)
   - Temporal correlation (same timezone activity pattern)
   - Contact overlap (shared email/phone across platforms)
4. **Merging** — Tạo "Golden Record" (ProfileEntity) từ tất cả sources
5. **Confidence scoring** — 0.0-1.0 cho mỗi merged field

```python
# Proposed entity resolution logic
class EntityResolver:
    WEIGHT_USERNAME_MATCH = 0.3
    WEIGHT_AVATAR_MATCH = 0.25
    WEIGHT_BIO_SIMILARITY = 0.2
    WEIGHT_TIMEZONE_MATCH = 0.15
    WEIGHT_CONTACT_OVERLAP = 0.1

    def resolve(self, candidates: list[RawProfile]) -> ProfileEntity:
        """Merge multiple RawProfile objects into one Golden Record."""
        golden = ProfileEntity()
        for field in ProfileEntity.__dataclass_fields__:
            values = [getattr(c, field) for c in candidates if getattr(c, field)]
            golden.__setattr__(field, self._pick_best(values))
            golden.confidence = self._compute_confidence(candidates)
        return golden
```

_Sources: [Entity Resolution (Semantic Visions)](https://www.semantic-visions.com/insights/entity-resolution), [Multi-Source Identity Resolution in OSINT](https://publicinsights.uk/blog/the-importance-of-multi-source-identity-resolution-in-osint), [Identity Graphs (Senzing)](https://senzing.com/what-is-identity-resolution-defined/)_

### Pattern 3: Plugin Categories — Phân loại plugin theo stage

| Category | Plugin | Stage | Input → Output | Priority |
|----------|--------|-------|-----------------|----------|
| **Breach Intel** | LeakLookup | 2 | EMAIL/USER → breach domains | ✅ Có |
| **Breach Intel** | HIBP | 2 | EMAIL → breach names + dates | ✅ Có |
| **Email Discovery** | HolehPlugin | 2 | EMAIL → registered services list | 🔴 Epic 9.1 |
| **Username Discovery** | MaigretPlugin | 2 | USERNAME → 3000+ site profiles | 🔴 Epic 9.2 |
| **Network Intel** | Shodan | 2 | IP → ports, hostnames, vulns | ✅ Có |
| **Search Intel** | SearxNG | 2 | ANY → osint_urls | ✅ Có |
| **Email Verify** | HunterPlugin | 3 | EMAIL → name, company, verified | 🟡 Epic 9.3 |
| **Phone Intel** | NumverifyPlugin | 3 | PHONE → country, carrier, valid | 🟡 Epic 9.4 |
| **Social Deep** | InstaPlugin | 3 | USERNAME → bio, photos, GPS | 🟡 Epic 9.5 |
| **Social Deep** | RedditPlugin | 3 | USERNAME → posts, karma, subs | 🟡 Epic 9.6 |
| **Social Deep** | YouTubePlugin | 3 | USERNAME → channel, videos | 🟡 Epic 9.7 |
| **Code Intel** | GitHubPlugin | 3 | EMAIL/USER → repos, commits, name | 🔴 Epic 9.8 |
| **AI Analysis** | PersonalityPlugin | 4 | TEXT → personality traits, sentiment | 🟢 Epic 9.9 |
| **AI Analysis** | EntityResolver | 4 | RawProfiles → Golden Record | 🟢 Epic 9.10 |

### Pattern 4: Caching & Persistence — SQLite-backed

Mr.Holmes đã có SQLite (mrholmes.db). Mở rộng schema:

```sql
-- Cache API responses (tránh re-query)
CREATE TABLE osint_cache (
    cache_key TEXT PRIMARY KEY,          -- sha256(plugin + target + params)
    plugin_name TEXT NOT NULL,
    target TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                -- TTL per source
    hit_count INTEGER DEFAULT 0
);

-- Golden Record storage
CREATE TABLE profile_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seed_target TEXT NOT NULL,            -- Original search seed
    real_name TEXT,
    display_names TEXT,                   -- JSON array
    emails TEXT,                          -- JSON array
    phones TEXT,                          -- JSON array
    country TEXT,
    city TEXT,
    occupation TEXT,
    platforms TEXT,                       -- JSON: {platform: url}
    interests TEXT,                       -- JSON array
    confidence REAL DEFAULT 0.0,
    raw_graph_json TEXT,                  -- Full ProfileGraph
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Pattern 5: Async Orchestration — Per-Stage Semaphore

```python
class EnrichmentOrchestrator:
    """Multi-stage orchestration with per-source rate limiting."""

    STAGE_CONFIG = {
        "expansion": {"semaphore": 5, "plugins": ["HolehPlugin", "MaigretPlugin", "LeakLookup", "HIBP"]},
        "enrichment": {"semaphore": 3, "plugins": ["InstaPlugin", "RedditPlugin", "GitHubPlugin"]},
        "synthesis": {"semaphore": 1, "plugins": ["LLMSynthesizer", "EntityResolver"]},
    }

    async def run(self, seed: str, seed_type: str) -> ProfileEntity:
        graph = ProfileGraph()
        for stage_name, config in self.STAGE_CONFIG.items():
            sem = asyncio.Semaphore(config["semaphore"])
            plugins = self._load_plugins(config["plugins"])
            results = await self._run_stage(plugins, graph, sem)
            graph = self._merge_results(graph, results)
        return EntityResolver().resolve(graph)
```

### Đánh giá khả thi tổng thể

| Tính năng | Khả thi | Effort | Impact | Ưu tiên |
|----------|---------|--------|--------|---------|
| HolehPlugin (email→services) | ✅ Cao | 1-2 ngày | 🔥 Rất cao | P0 |
| MaigretPlugin (username→3000 sites) | ✅ Cao | 2-3 ngày | 🔥 Rất cao | P0 |
| GitHubPlugin (email/user→name) | ✅ Cao | 1 ngày | 🔥 Cao | P1 |
| NumverifyPlugin (phone→geo) | ✅ Cao | 1 ngày | Trung bình | P1 |
| InstaPlugin (Instaloader) | ⚠️ TB | 2-3 ngày | 🔥 Cao | P1 |
| RedditPlugin (PRAW) | ✅ Cao | 1 ngày | Trung bình | P2 |
| YouTubePlugin (Data API) | ✅ Cao | 1 ngày | Trung bình | P2 |
| HunterPlugin (email→name) | ✅ Cao | 1 ngày | Cao | P2 |
| ProfileEntity data model | ✅ Cao | 1-2 ngày | 🔥 Foundation | P0 |
| EntityResolver (AI merge) | ⚠️ TB | 3-5 ngày | 🔥 Rất cao | P1 |
| Cross-Platform Bridge | ⚠️ Khó | 5+ ngày | 🔥 Rất cao | P2 |
| Personality Analysis (LLM) | ✅ Cao | 2 ngày | Cao | P2 |
| Cache layer (SQLite) | ✅ Cao | 1 ngày | Cao | P1 |

**Tổng estimate: ~25-35 ngày dev cho toàn bộ Epic 9**

---

## Implementation Research — Code Blueprints

### Plugin 1: HolehPlugin (P0 — 1-2 ngày)

```python
# Core/plugins/holehe_plugin.py
class HolehPlugin(IntelligencePlugin):
    SUPPORTED_TYPES = {"EMAIL"}
    name = "Holehe"
    requires_api_key = False

    async def check(self, target: str, target_type: str) -> PluginResult:
        import httpx
        from holehe.core import get_functions
        results = []
        async with httpx.AsyncClient() as client:
            modules = get_functions(holehe.modules)
            for module in modules:
                await module(target, client, results)
        registered = [r for r in results if r.get("exists")]
        return PluginResult(
            plugin_name=self.name, is_success=True,
            data={
                "data_found": len(registered) > 0,
                "registered_services": [r["name"] for r in registered],
                "recovery_phones": [r["phoneNumber"] for r in registered if r.get("phoneNumber")],
                "recovery_emails": [r["emailrecovery"] for r in registered if r.get("emailrecovery")],
                "total_checked": len(results),
                "metadata": {"total_registered": len(registered)},
            })
```

**Holehe data structure trả về:** `{"name": str, "exists": bool, "emailrecovery": str|None, "phoneNumber": str|None}`
- `emailrecovery` và `phoneNumber` là partial obfuscated → **clue extraction mới cho BFS!**
- Ví dụ: `phoneNumber: "+84 *** **69"` → manh mối phone number

_Sources: [holehe GitHub](https://github.com/megadose/holehe), [holehe PyPI](https://pypi.org/project/holehe/), [holehe core.py](https://github.com/megadose/holehe/blob/master/holehe/core.py)_

### Plugin 2: MaigretPlugin (P0 — 2-3 ngày)

```python
# Core/plugins/maigret_plugin.py — Wrapper quanh maigret CLI/library
import asyncio, subprocess, json

class MaigretPlugin(IntelligencePlugin):
    SUPPORTED_TYPES = {"USERNAME"}
    name = "Maigret"
    requires_api_key = False

    async def check(self, target: str, target_type: str) -> PluginResult:
        # Chạy maigret subprocess (stable hơn import trực tiếp)
        proc = await asyncio.create_subprocess_exec(
            "maigret", target, "--json", "nul", "--timeout", "10",
            "--top-sites", "500", "--no-progressbar",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        data = json.loads(stdout)
        # Extract profile URLs + personal data
        found_sites = [...]  # Parse maigret JSON output
        return PluginResult(...)
```

**Lưu ý:** Maigret yêu cầu Python ≥3.10, Mr.Holmes dùng 3.9 → cần subprocess wrapper hoặc upgrade Python.

**Output format:** JSON với `username`, `sites` (list of site objects with `url_user`, `status`, `tags`), tự động extract `ids` cho auto-search.

_Sources: [Maigret docs](https://maigret.readthedocs.io/), [Maigret usage examples](https://maigret.dev/docs/usage-examples/), [Maigret PyPI](https://pypi.org/project/maigret/)_

### Plugin 3: GitHubPlugin (P1 — 1 ngày)

```python
# Core/plugins/github_plugin.py
class GitHubPlugin(IntelligencePlugin):
    SUPPORTED_TYPES = {"EMAIL", "USERNAME"}
    name = "GitHub"
    requires_api_key = False  # 60 req/h free, 5000 with token

    async def check(self, target: str, target_type: str) -> PluginResult:
        if target_type == "EMAIL":
            # Search commits by email → extract author name
            url = f"https://api.github.com/search/commits?q=author-email:{target}"
            # Parse commit.author.name → real_name discovery!
        elif target_type == "USERNAME":
            url = f"https://api.github.com/users/{target}"
            # Parse: name, bio, location, company, blog, twitter_username
```

### Plugin 4: InstaPlugin via Instaloader (P1 — 2-3 ngày)

```python
# Core/plugins/instagram_plugin.py
import instaloader

class InstagramPlugin(IntelligencePlugin):
    SUPPORTED_TYPES = {"USERNAME"}
    name = "Instagram"

    async def check(self, target: str, target_type: str) -> PluginResult:
        L = instaloader.Instaloader()
        try:
            profile = instaloader.Profile.from_username(L.context, target)
            return PluginResult(data={
                "full_name": profile.full_name,      # TÊN THẬT!
                "biography": profile.biography,
                "followers": profile.followers,
                "following": profile.followees,
                "posts_count": profile.mediacount,
                "is_private": profile.is_private,
                "profile_pic_url": profile.profile_pic_url,
                "external_url": profile.external_url,
            })
        except instaloader.exceptions.ProfileNotExistsException:
            return PluginResult(data={"data_found": False})
```

**⚠️ Giới hạn:** Rate limit ~1-2 req/30s. Cần login cho followers list. Proxy rotation recommended.

_Sources: [Instaloader docs](https://instaloader.github.io/as-module.html), [Instaloader examples](https://instaloader.github.io/codesnippets.html)_

### BFS Clue Extraction Mở Rộng

Cần update `_extract_clues_from_result()` trong `autonomous_agent.py`:

```python
# Thêm extraction cho holehe recovery data
if data.get("recovery_phones"):
    for phone in data["recovery_phones"]:
        # Parse partial phone: "+84 *** **69" → extract country code
        clues.append((phone, "PHONE"))

if data.get("recovery_emails"):
    for email in data["recovery_emails"]:
        clues.append((email, "EMAIL"))

if data.get("registered_services"):
    # Holehe found 79 services → thêm vào graph metadata
    # (không phải DOMAIN target, mà là service_presence attribute)

if data.get("full_name"):
    # Real name discovery! Store as metadata, trigger person search
    pass

if data.get("platforms") and isinstance(data["platforms"], dict):
    for platform, url in data["platforms"].items():
        clues.append((url, "URL"))
```

---

## Research Synthesis — Final Recommendations

### Epic 9: Complete OSINT Profiling System — Implementation Roadmap

#### Phase 1: Foundation (Tuần 1-2) — P0 Items

| Story | Tên | Effort | Deliverable |
|-------|-----|--------|-------------|
| 9.1 | ProfileEntity Data Model | 1-2 ngày | `Core/models/profile_entity.py` + SQLite schema migration |
| 9.2 | HolehPlugin | 1-2 ngày | `Core/plugins/holehe_plugin.py` — email→120+ services |
| 9.3 | MaigretPlugin | 2-3 ngày | `Core/plugins/maigret_plugin.py` — username→3000+ sites |
| 9.4 | BFS Clue Extraction v2 | 1 ngày | Update `autonomous_agent.py` cho recovery phone/email/name |
| 9.5 | Cache Layer | 1 ngày | `osint_cache` table + check-before-query logic |

**Phase 1 output:** Từ 1 email → biết 79+ services + 3000+ site profiles + breach data. Graph tăng từ ~30 nodes → 100+ nodes.

#### Phase 2: Deep Enrichment (Tuần 3-4) — P1 Items

| Story | Tên | Effort | Deliverable |
|-------|-----|--------|-------------|
| 9.6 | GitHubPlugin | 1 ngày | email→commits→real name, username→bio/location |
| 9.7 | NumverifyPlugin | 1 ngày | phone→country/carrier/validity |
| 9.8 | InstagramPlugin (Instaloader) | 2-3 ngày | username→full_name/bio/followers/GPS |
| 9.9 | EntityResolver v1 | 3 ngày | Merge multi-source → Golden Record |
| 9.10 | Enhanced LLM Synthesis | 1 ngày | Prompt v2 với ProfileEntity data |

**Phase 2 output:** Golden Record với tên thật, location, occupation, interests. AI report dựa trên enriched data.

#### Phase 3: Social Intelligence (Tuần 5-6) — P2 Items

| Story | Tên | Effort | Deliverable |
|-------|-----|--------|-------------|
| 9.11 | RedditPlugin (PRAW) | 1 ngày | username→posts/karma/subreddits |
| 9.12 | YouTubePlugin | 1 ngày | channel→videos/subscribers |
| 9.13 | HunterPlugin | 1 ngày | email→name/company verification |
| 9.14 | CrossPlatformBridge v1 | 3-5 ngày | email-confirmed services → username discovery |
| 9.15 | Personality Analysis (LLM) | 2 ngày | Text content → traits/sentiment/behavior |
| 9.16 | Timeline Generator | 2 ngày | Account ages + activity → chronological view |

**Phase 3 output:** Profile hoàn chỉnh: tên thật, SĐT, location, nghề nghiệp, timeline, sở thích, tính cách, social graph.

### Risk Assessment

| Rủi ro | Mức độ | Giảm thiểu |
|--------|--------|-----------|
| Maigret yêu cầu Python ≥3.10 | 🟡 Trung bình | Subprocess wrapper hoặc upgrade Python |
| Instagram rate limiting ngày càng nghiêm ngặt | 🔴 Cao | Proxy rotation, session caching, respectful delays |
| PhoneInfoga v2 là Go, không Python | 🟡 Trung bình | Tự build phone plugin dùng Numverify + phonenumbers |
| Holehe API có thể thay đổi | 🟡 Trung bình | Pin version, fallback graceful |
| Legal/ethical concerns | 🔴 Cao | Chỉ thu thập public data, respecting robots.txt, rate limits |
| BFS explosion với nhiều plugins mới | 🟡 Trung bình | Max clues cap (đã có: 15), configurable per-plugin |

### Kết luận

Mr.Holmes đã có **foundation tốt** (plugin protocol, BFS engine, LLM synthesis, mindmap). Epic 9 mở rộng bằng cách:

1. **Thêm plugins** (Holehe, Maigret, GitHub, Insta, Reddit, YouTube) → plug vào plugin system hiện có
2. **Nâng cấp data model** (ProfileNode → ProfileEntity) → richer profiling
3. **Entity resolution** → merge multi-source thành Golden Record
4. **AI analysis** → personality, behavior, timeline
5. **Cross-platform bridge** → gap bridging khó nhất nhưng impact cao nhất

**Estimated total effort: 25-35 ngày development cho full Epic 9.**

---

_Research completed: 2026-04-05_
_Sources verified via web search across GitHub, PyPI, Bellingcat, official documentation_
