---
project_name: Mr.Holmes
version: 1.0.0
date: 2026-03-26
status: draft
stepsCompleted: [init, discovery, vision, executive-summary, success, journeys, domain, innovation, project-type, scoping, functional, nonfunctional, polish, complete]
---

# PRD: Mr.Holmes OSINT Engine Modernization

## Executive Summary

Mr.Holmes là công cụ OSINT (Open Source Intelligence) mã nguồn mở cho phép thu thập thông tin công khai về usernames, phone numbers, emails, websites và ports. Hiện tại, hệ thống gặp bottleneck hiệu suất nghiêm trọng do kiến trúc synchronous, code monolithic khó maintain, và thiếu test coverage.

**Mục tiêu:** Chuyển đổi Mr.Holmes từ một script OSINT cá nhân thành OSINT Autonomous Agent chuyên nghiệp — nhanh, ổn định, tự động hóa đệ quy, có test coverage — sẵn sàng cho community contribution và mở rộng.

## Vision

Trở thành **công cụ OSINT CLI hàng đầu** với:
- Tốc độ quét concurrent nhanh gấp 10-30x
- Trở thành Autonomous Agent có khả năng đệ quy tự chắp nối manh mối và báo cáo bằng LLM
- Kiến trúc plugin-based dễ mở rộng
- Chất lượng enterprise-grade với test coverage và structured logging

## Target Users

- OSINT Researchers
- Cybersecurity Analysts
- Ethical Hackers
- Private Investigators
- Automation/DevSecOps Engineers (batch mode)

## Success Criteria

| Metric | Hiện tại | Mục tiêu |
|--------|----------|----------|
| Scan 300 sites | 15-25 phút | < 60 giây |
| Test coverage | 0% | > 60% |
| Thêm 1 scraper mới | ~20 LOC copy-paste | 1 dòng registry |
| Method max LOC | 500 LOC (God Method) | < 50 LOC |
| Error handling | Silent `pass` | Structured logging |

## Functional Requirements

### Scanning Engine

- FR1: Hệ thống có thể quét đồng thời (concurrent) nhiều target sites thay vì tuần tự
- FR2: Hệ thống có thể giới hạn số lượng concurrent requests qua configurable semaphore
- FR3: User có thể nhận kết quả scan theo thứ tự nhất quán bất kể thứ tự hoàn thành
- FR4: Hệ thống có thể phát hiện và retry khi gặp rate limiting (403, 429)
- FR5: Hệ thống có thể tự động backoff với exponential delay + jitter khi bị block

### Proxy Management

- FR6: Hệ thống có thể tự động rotate proxy khi proxy hiện tại chết
- FR7: Hệ thống có thể health-check proxy trước khi sử dụng
- FR8: User có thể cấu hình danh sách proxy sources

### Scraper System

- FR9: Developer có thể thêm scraper mới chỉ bằng cách đăng ký vào registry
- FR10: Hệ thống có thể dispatch scrapers concurrent cho các sites đã tìm thấy
- FR11: Mỗi scraper có thể retry với fallback (bỏ proxy) khi connection error

### Data & Reporting

- FR12: Hệ thống có thể lưu kết quả vào cả file reports lẫn SQLite database
- FR13: User có thể export báo cáo ra PDF, CSV, JSON
- FR14: Hệ thống có thể tìm kiếm và filter kết quả cross-case từ database
- FR15: PHP GUI có thể đọc dữ liệu từ SQLite thay vì flat files

### CLI & UX

- FR16: User có thể chạy Mr.Holmes ở batch mode qua CLI flags (non-interactive)
- FR17: User có thể thấy progress bars và table layout trên terminal
- FR18: Hệ thống có thể validate input (sanitize username, kiểm tra integer input)

### Security & Configuration

- FR19: Hệ thống có thể load secrets từ `.env` thay vì plaintext `.ini`
- FR20: Hệ thống có thể structured logging với levels (DEBUG, INFO, WARNING, ERROR)
- FR21: Developer có thể chạy unit tests với mock HTTP responses

### External Intelligence

- FR22: User có thể check email breach history qua HaveIBeenPwned API
- FR23: User có thể tra cứu IP/port intelligence qua Shodan API
- FR24: User có thể cấu hình API keys cho external services
- FR25: User có thể tra cứu data breach thông qua API miễn phí của Leak-Lookup (Fallback cho HIBP)
- FR26: Hệ thống có thể thực hiện Dorking ẩn danh không lo Captcha thông qua metasearch SearxNG

### Autonomous Profiler (Epic 8)

- FR27: Hệ thống có thể tự động quét đệ quy (recursive scan) từ một hạt giống thông tin gốc tùy chỉnh theo độ sâu (depth).
- FR28: Hệ thống có thể tổng hợp và phân tích báo cáo tri thức tự động thông qua các API tương thích OpenAPI của LLM.
- FR29: Hệ thống có thể xuất kết quả dưới định dạng Mindmap (Interactive HTML Graph), JSON, và PDF.

## Non-Functional Requirements

- NFR1: Scan 300 sites phải hoàn thành trong < 2 phút (với semaphore=20)
- NFR2: Memory usage không vượt quá 200MB cho 1 session
- NFR3: Unit test coverage đạt tối thiểu 60% cho core modules
- NFR4: Backward compatible với PHP GUI trong giai đoạn chuyển tiếp (dual-write)
- NFR5: Hỗ trợ Python 3.9+
- NFR6: Zero plaintext secrets trong source code và config files
- NFR7: Structured error messages — không có "Something went wrong" chung chung
