# Mr.Holmes — Documentation Index

> **Cập nhật lần cuối:** 2026-04-05 | **Scan level:** Exhaustive | **248 Python files, ~74K LOC**

## Tổng quan dự án

| Thuộc tính | Giá trị |
|-----------|---------|
| **Loại** | Multi-part (Python CLI + PHP GUI) |
| **Ngôn ngữ chính** | Python 3.9 |
| **Kiến trúc** | Plugin system + BFS recursive profiler + LLM synthesis |
| **Entry Point** | `MrHolmes.py` (interactive + batch) |
| **Target Types** | EMAIL, USERNAME, IP, DOMAIN, PHONE |

## Tài liệu chính

- [Tổng quan dự án](project-overview.md) — Giới thiệu, mục tiêu, 8 epics, đối tượng sử dụng
- [Kiến trúc](architecture.md) — Entry points, engine, plugin system, data flow, async patterns
- [Tech Stack](tech-stack.md) — Bảng công nghệ đầy đủ (Python, AI/LLM, search, reporting)
- [Project Context](project-context.md) — Business boundaries, constraints

## Phân tích mã nguồn

- [Component Inventory](component-inventory.md) — 4 plugins, 8 engine components, 19 scrapers, CLI, reporting
- [Source Tree Analysis](source-tree-analysis.md) — Annotated directory tree, critical folders
- [Development Guide](development-guide.md) — Setup, run commands, testing, plugin development

## Vận hành & Triển khai

- [Testing Strategy](testing-strategy.md) — pytest, 569+ tests, coverage
- [Deployment](deployment.md) — Installation, Docker (SearxNG)
- [Asset Inventory](asset-inventory.md) — Site lists, dork templates, language files

## Tài liệu tham khảo

- [Brownfield Analysis](brownfield-analysis-Mr.Holmes-2025-10-08.md) — Phân tích legacy từ 2025
- [README](../README.md) — Public README
- [SECURITY](../SECURITY.md) — Security policy
- [RELEASES](../RELEASES.md) — Release notes

## Bắt đầu nhanh

```bash
# Cài đặt
pip install -r requirements.txt
cp .env.example .env  # Cấu hình API keys

# Chạy interactive
python3 MrHolmes.py

# Chạy batch (username scan)
python3 MrHolmes.py --username deptraidapxichlo

# Chạy autonomous profiler (Option 16)
python3 MrHolmes.py  # → chọn 16
```
