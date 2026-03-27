# Story 6.4: PDF Export via Jinja2

Status: ready-for-dev

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

- [ ] Task 1 — Create Jinja2 HTML template
- [ ] Task 2 — Implement PDF generator class
- [ ] Task 3 — CLI integration (`--export pdf`)
- [ ] Task 4 — Test PDF output

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
### Agent Model Used
### Completion Notes List
### File List
