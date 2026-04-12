---
title: "Product Brief: Mr.Holmes Epic 9 — Complete OSINT Profiling System"
status: "final"
created: "2026-04-05"
updated: "2026-04-05"
inputs:
  - "_bmad-output/planning-artifacts/research/technical-osint-profiling-system-research-2026-04-05.md"
  - "docs/architecture.md"
  - "docs/component-inventory.md"
  - "docs/project-overview.md"
---

# Product Brief: Mr.Holmes Epic 9 — Complete OSINT Profiling System

## Tóm tắt điều hành

Mr.Holmes hiện là một OSINT tool mã nguồn mở, quét username trên 150 sites và kiểm tra email trong cơ sở dữ liệu rò rỉ. Tuy nhiên, khi một nhà điều tra chỉ có 1 email — ví dụ `deptraidapxichlo@gmail.com` — hệ thống dừng lại ở danh sách URL và breach names. Không có tên thật. Không có số điện thoại. Không có ảnh. Không có timeline hành vi.

**Epic 9 biến Mr.Holmes từ "tìm thấy ở đâu" thành "biết họ là ai".**

Bằng cách tích hợp Maigret (3000+ sites), Holehe (120+ services), và xây dựng hệ thống Entity Resolution, Mr.Holmes sẽ tự động tổng hợp từ 10+ nguồn thành một Golden Record — hồ sơ thống nhất với tên thật, SĐT, vị trí, nghề nghiệp, sở thích, tính cách, và mối quan hệ xã hội. Tất cả từ 1 manh mối ban đầu. Miễn phí. Mã nguồn mở.

Đây là lúc phù hợp: các OSINT framework thương mại (Maltego $6,600/năm, SpiderFoot paid tier) đã chứng minh nhu cầu, nhưng không có giải pháp open-source nào cung cấp trải nghiệm **"1 input → complete profile"** với entity resolution và AI personality analysis.

## Vấn đề

Một OSINT analyst nhận được 1 email cần điều tra. Quy trình hiện tại:

1. Chạy Mr.Holmes → được 19 platform URLs + 5 breach names
2. **Thủ công** mở từng URL, kiểm tra bio, ảnh, followers
3. **Thủ công** thử username trên Instagram, Discord (biết email đăng ký nhưng không biết username)
4. **Thủ công** search Google dorks tìm tên thật, SĐT
5. **Thủ công** ghép nối tất cả thành 1 hồ sơ

Quy trình này mất **2-4 giờ** cho 1 target. Và analyst vẫn bỏ sót — Holehe cho thấy `deptraidapxichlo@gmail.com` đăng ký trên **79 services** (bao gồm Instagram, Discord, Strava, Venmo) mà username scan 150 sites chỉ tìm được **19**.

**60+ platforms bị bỏ sót. Tên thật, SĐT, GPS location — tất cả nằm ngoài tầm với.**

## Giải pháp

Epic 9 xây dựng **pipeline enrichment 4 tầng tự động**:

**Tầng 1 — Seed Input:** Nhận 1 email, username, hoặc SĐT

**Tầng 2 — Identity Expansion:** Holehe kiểm tra 120+ services (phát hiện recovery phone/email), Maigret quét 3000+ sites (extract tên, bio, ảnh), LeakLookup + HIBP tìm breach data

**Tầng 3 — Deep Enrichment:** GitHub API trích xuất tên thật từ commits, Instaloader lấy bio + GPS posts, Reddit PRAW phân tích interests, Numverify xác minh SĐT

**Tầng 4 — AI Synthesis:** Entity Resolver merge tất cả thành Golden Record (ProfileEntity), LLM phân tích personality + hành vi, tạo báo cáo tình báo chuyên nghiệp + interactive mindmap

## Điểm khác biệt

| | Mr.Holmes Epic 9 | Maltego | SpiderFoot |
|---|---|---|---|
| **Coverage** | 3000+ sites | 500+ | 200+ |
| **Entity Resolution** | Auto Golden Record | Manual (paid) | Không có |
| **AI Personality** | LLM analysis | Không có | Không có |
| **GPS từ content** | Instagram posts | Hạn chế | Không có |
| **Giá** | **Miễn phí, mã nguồn mở** | $6,600/năm | Paid tier |

**Lợi thế cạnh tranh:** Kết hợp coverage cao nhất (Maigret 3000+ sites) + entity resolution tự động + AI personality analysis — tất cả miễn phí. Không có tool open-source nào cung cấp trải nghiệm tương đương.

## Đối tượng sử dụng

**Chính:** OSINT researchers và cybersecurity analysts — những người cần xây dựng hồ sơ nhanh chóng từ manh mối tối thiểu. Khoảnh khắc "aha" là khi hệ thống tự tìm ra tên thật từ GitHub commits mà analyst chưa bao giờ nghĩ đến.

**Phụ:** Ethical hackers (reconnaissance phase), private investigators (tra cứu danh tính), và nhà báo điều tra.

## Thước đo thành công

- **Coverage:** 150 → 3000+ sites (20x)
- **Enrichment depth:** URL only → tên thật, SĐT, location, personality (5x richer)
- **Thời gian:** 2-4 giờ thủ công → 15-20 phút tự động (first pass) + async enrichment
- **Entity resolution confidence:** Trung bình ≥ 0.75 cho merged profiles
- **Cache hit rate:** ≥ 60% (giảm API calls lặp lại)

## Phạm vi

**Trong phạm vi (3 phases, 16 stories, ~25-35 ngày):**

- **Phase 1 (Tuần 1-2):** ProfileEntity model, HolehPlugin, MaigretPlugin, Cache layer, BFS v2
- **Phase 2 (Tuần 3-4):** GitHub, Numverify, Instagram plugins, EntityResolver, Enhanced LLM
- **Phase 3 (Tuần 5-6):** Reddit, YouTube, Hunter plugins, Cross-Platform Bridge, Personality Analysis, Timeline

**Ngoài phạm vi:**
- Social graph crawling (friends-of-friends)
- Dark web monitoring
- Real-time surveillance / continuous monitoring
- LinkedIn scraping (account lock risk quá cao)
- Credential testing / password spraying

## Sử dụng có trách nhiệm & Tuân thủ pháp luật

**Mr.Holmes CHỈ được sử dụng cho mục đích được ủy quyền:**
- Xác minh danh tính cá nhân (tài khoản của chính bạn)
- Nghiên cứu cybersecurity (có sự đồng ý của target)
- Điều tra pháp luật (được ủy quyền)
- Nhà báo điều tra (lợi ích công cộng)

**KHÔNG được sử dụng cho:** Stalking, doxing, phishing, phân biệt đối xử, giám sát trái phép.

**Biện pháp bảo vệ tích hợp:**
- Mỗi plugin hiển thị mức rủi ro ToS (🟢 Safe / 🟡 ToS Risk / 🔴 Ban Risk)
- Instagram plugin (Instaloader) là opt-in, cần xác nhận rõ ràng trước khi chạy
- Golden Records mặc định ephemeral (chỉ tồn tại trong session)
- Tất cả LLM insights được đánh dấu "AI-generated hypothesis" — không phải facts
- Data retention policy: auto-delete sau 30 ngày trừ khi user giữ lại
- Tuân thủ GDPR/CCPA: self-hosted data, user kiểm soát hoàn toàn

## Tầm nhìn

Nếu Epic 9 thành công, Mr.Holmes trở thành **nền tảng OSINT profiling hoàn chỉnh đầu tiên miễn phí** — đối thủ trực tiếp của Maltego trong segment open-source. Trong 2-3 năm:

- **Plugin marketplace:** Cộng đồng đóng góp plugins cho các nguồn dữ liệu mới
- **Graph visualization nâng cao:** Neo4j-backed relationship mapping
- **Continuous monitoring:** Theo dõi thay đổi profile theo thời gian
- **API mode:** Mr.Holmes như microservice cho các tool khác tích hợp
- **Multi-target correlation:** Phân tích mối quan hệ giữa nhiều targets
