# Mr.Holmes — Tech Stack

## Runtime & Core Libraries

| Category | Technology | Version | Mục đích |
|----------|-----------|---------|----------|
| Language | Python | 3.9+ | Runtime chính |
| Async HTTP | aiohttp | >=3.9.0 | Async scan 150+ sites đồng thời |
| Async files | aiofiles | >=23.0 | Non-blocking file I/O |
| Sync HTTP | requests | >=2.31.0 | Legacy scrapers, proxy identity lookup |
| HTML parsing | beautifulsoup4 | 4.9.3 | Parse profile pages của platform scrapers |
| Phone lookup | phonenumbers | 8.12.25 | Carrier, region, line type từ số điện thoại |
| Configuration | python-dotenv | >=1.0.0 | Load `.env` file cho API keys và secrets |
| CLI output | rich | >=13.0 | Progress bars, colored tables, spinners |
| Tor/Proxy | stem | >=1.4.0 | Tor circuit renewal (tùy chọn) |

---

## AI & Search

| Category | Technology | Mục đích |
|----------|-----------|----------|
| LLM Primary | Google AI Studio (Gemini) | Synthesis OSINT report — OpenAI-compatible endpoint |
| LLM Fallback | v98store endpoint | Failover khi primary quota exceeded |
| Web Search Primary | SearxNG (Docker) | Privacy-preserving search, self-hosted |
| Web Search Fallback | duckduckgo-search >=7.0 | DDG API khi SearxNG unavailable |

`LLMSynthesizer` gọi bất kỳ OpenAI-compatible API endpoint nào. Cấu hình qua biến môi trường `MH_LLM_BASE_URL`, `MH_LLM_API_KEY`, `MH_LLM_MODEL` (xem thêm phần `.env` trong [development-guide.md](./development-guide.md)).

---

## Reporting & Export

| Category | Technology | Version | Mục đích |
|----------|-----------|---------|----------|
| Database | SQLite (`mrholmes.db`) | — | Lưu investigations + findings |
| Template engine | Jinja2 | >=3.1.0 | PDF template rendering |
| PDF generation | weasyprint | >=60.0 (optional) | HTML → PDF conversion |
| PDF fallback | pdfkit | 1.0.0 | wkhtmltopdf wrapper |
| Mindmap | vis-network.js | CDN | Interactive HTML graph visualization |
| QR Codes | PyQRCode | 1.2.1 | QR generation cho kết quả |

---

## Deep Scraping

| Technology | Version | Mục đích |
|-----------|---------|----------|
| apify-client | >=1.8.0,<2.0.0 | Instagram deep scrape qua Apify Actor API (bypass anti-bot) |
| holehe | — | Email-to-service lookup (kiểm tra email đã đăng ký service nào) |

---

## Testing

| Category | Technology | Version | Mục đích |
|----------|-----------|---------|----------|
| Test runner | pytest | >=8.0 | Unit + integration tests |
| Async tests | pytest-asyncio | >=0.23 | Test async coroutines |
| HTTP mocking | aioresponses | >=0.7.6 | Mock aiohttp requests trong tests |
| Coverage | pytest-cov | >=4.1.0 | Coverage reporting |
| Linting | flake8 | >=7.0.0 | Code style enforcement |

---

## Infrastructure

| Category | Technology | Mục đích |
|----------|-----------|----------|
| CI/CD | GitHub Actions | Automated testing + linting |
| Search engine | SearxNG (Docker) | Self-hosted search (`GUI/searxng/`) |
| GUI server | PHP | Web dashboard đọc từ `GUI/Reports/` + `mrholmes.db` |
| Package manager | pip | Python dependency management |

---

## Cấu hình file quan trọng

| File | Mục đích |
|------|----------|
| `requirements.txt` | Production dependencies |
| `requirements-dev.txt` | Dev/test dependencies (inherits `requirements.txt`) |
| `Configuration/Configuration.ini` | Non-secret settings: language, date format, SMTP, proxy path |
| `.env` | API keys và secrets — KHÔNG commit vào git |
| `pytest.ini` | pytest configuration |
| `GUI/searxng/` | SearxNG Docker configuration |
