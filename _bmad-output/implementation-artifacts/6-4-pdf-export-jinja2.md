# Story 6.4: PDF Export via Jinja2

Status: review

## Story

As a user,
I want to export investigation results ra PDF reports,
so that findings có thể chia sẻ, in ấn, và lưu trữ chuyên nghiệp.

## Acceptance Criteria

1. **AC1:** PDF export command: `python3 MrHolmes.py --export pdf --investigation <id>`
2. **AC2:** Template-based via Jinja2 → HTML → PDF (weasyprint/pdfkit)
3. **AC3:** Report includes: header, summary, findings table, tags cloud
4. **AC4:** Branding: Mr.Holmes logo, date, investigation metadata

## Tasks / Subtasks

- [x] Task 1 — Create Jinja2 HTML template
- [x] Task 2 — Implement PDF generator class
- [x] Task 3 — CLI integration (`--export pdf`)
- [x] Task 4 — Test PDF output

## Dev Notes

### Dependencies
- **REQUIRES Story 6.1** — SQLite data source
- **REQUIRES Story 5.1** — CLI args for export command

### File Structure
```
Core/reporting/
├── templates/
│   └── report.html.j2  # NEW — Jinja2 template
└── pdf_export.py        # NEW — PDF generator
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet 4.6 (Thinking)
### Completion Notes List
- Task 1: `Core/reporting/templates/report.html.j2` — Jinja2 template with branding, summary grid, findings table, tags cloud, all-sites table
- Task 2: `Core/reporting/pdf_export.py` — PdfExporter class: DB fetch → Jinja2 render → weasyprint (preferred) / pdfkit (fallback). `export()` returns Path, `render_html()` for testing without PDF renderer
- Task 3: Added `--export pdf` and `--investigation <id>` flags to `Core/cli/parser.py`. Added `has_export_target()` helper. Wired into `MrHolmes.py` before batch scan path
- Task 4: 16 unit tests in `tests/reporting/test_pdf_export.py` — 16/16 pass. Full suite: 479 passed
- Dependency: `jinja2>=3.1.0` added to requirements.txt. `weasyprint` is optional (commented)
- DB path: same as Story 6.1 singleton via `Database.get_instance()`
### File List
- Core/reporting/templates/report.html.j2 (NEW)
- Core/reporting/pdf_export.py (NEW)
- Core/cli/parser.py (MODIFIED: --export, --investigation flags + has_export_target)
- MrHolmes.py (MODIFIED: export dispatch block)
- tests/reporting/test_pdf_export.py (NEW)
- requirements.txt (MODIFIED: jinja2 added)
