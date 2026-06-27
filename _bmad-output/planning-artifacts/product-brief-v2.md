# Product Brief: Mr.Holmes 2.0 — The Digital Detective

## Vision
Mr.Holmes 2.0 là bộ công cụ OSINT (Open Source Intelligence) được thiết kế như một thám tử online, hoạt động qua MCP (Model Context Protocol) để Claude Code làm "bộ não" điều tra. Từ bất kỳ seed nào (username, tên, email, SĐT, mã số thuế), hệ thống tự động xây dựng profile sâu nhất có thể bằng cách iterative: tìm thông tin → lưu → phân tích → chọn tool phù hợp → tìm tiếp.

## Problem Statement
Mr.Holmes hiện tại là công cụ "one-shot" — chạy scan một lần, trả kết quả, không có iterative investigation. HTTP requests bị Cloudflare/captcha block (31/150 sites). Chỉ 9 plugins, thiếu nguồn Việt Nam. Không có memory giữa các lần chạy. AI orchestrator chưa tận dụng được vì không có MCP interface.

## Target Users
- OSINT researchers sử dụng Claude Code
- Cybersecurity analysts
- Private investigators
- Journalists
- Red team operators

## Solution Overview
Mr.Holmes = **tool collection** expose qua MCP server. Claude Code = **AI orchestrator** tự quyết định tìm gì tiếp, kết nối thông tin, đặt giả thuyết, hỏi user khi cần. Tận dụng tối đa Claude Code's reasoning, memory, human-in-the-loop capabilities.

## Key Differentiators
- AI-driven iterative investigation (Claude Code = brain)
- MCP-native — seamless integration với Claude Code
- 3000+ site coverage (Maigret integration)
- Browser automation (Playwright) bypass bot detection
- Free + paid source aggregation
- Vietnamese public records support
- Evidence store với SQLite — queryable history, resume capability

## Success Metrics
- MCP server exposes 30+ tools
- Investigation từ username → full profile trong <5 phút
- 1400+ tests pass, CI green
- Documentation đầy đủ (Plugin SDK, MCP guide, investigation playbook)

## Scope

### In Scope
- MCP server (expose 30 tools từ existing plugins + new ones)
- Playwright browser automation plugin
- 5-10 new plugins (Vietnamese sources, breach DBs, social media)
- Enhanced SQLite schema (evidence, hypotheses, audit_log)
- BMad OSINT skills (investigation playbooks)
- Documentation (MCP guide, Plugin SDK update, investigation guide)

### Out of Scope
- Web dashboard (React frontend)
- Mobile app
- Real-time monitoring/alerting
- Custom AI model training
- Neo4j/graph database

## Timeline
- Sprint 1: MCP Server + core tools (expose existing 9 plugins)
- Sprint 2: Evidence Store + Playwright browser plugin
- Sprint 3: New plugins (Vietnamese, breach, social media)
- Sprint 4: BMad OSINT skills + documentation
