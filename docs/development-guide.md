# Mr.Holmes — Development Guide

## Prerequisites

- Python 3.9 trở lên
- pip (package manager)
- PHP 7.4+ (chỉ cần nếu chạy PHP GUI)
- wkhtmltopdf hoặc weasyprint (chỉ cần nếu export PDF)
- Docker (chỉ cần nếu dùng SearxNG self-hosted)

---

## Cài đặt

### 1. Clone và cài dependencies

```bash
git clone <repo-url> Mr.Holmes
cd Mr.Holmes
pip install -r requirements.txt
```

### 2. Cài dev dependencies (để chạy tests)

```bash
pip install -r requirements-dev.txt
```

`requirements-dev.txt` kế thừa `requirements.txt` — không cần cài riêng production deps.

### 3. Chạy install script (tùy chọn)

```bash
chmod +x install.sh
./install.sh          # Linux / macOS
./install_Termux.sh   # Android (Termux)
Install.cmd           # Windows
```

---

## Thiết lập môi trường

### Tạo file `.env`

Copy từ template và điền các API key cần thiết:

```bash
cp .env.example .env   # nếu có template
# hoặc tạo mới
```

Nội dung `.env` tối thiểu:

```dotenv
# === Intelligence Plugins ===
HIBP_API_KEY=your_hibp_key_here
SHODAN_API_KEY=your_shodan_key_here
LEAK_LOOKUP_KEY=your_leaklookup_key_here

# === LLM Synthesis (Autonomous Profiler) ===
MH_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
MH_LLM_API_KEY=your_google_ai_studio_key
MH_LLM_MODEL=gemini-2.0-flash-lite

# === LLM Fallback ===
MH_LLM_FALLBACK_BASE_URL=https://api.v98.store/v1
MH_LLM_FALLBACK_API_KEY=your_fallback_key
MH_LLM_FALLBACK_MODEL=deepseek-chat

# === Deep Scraping ===
# Apify token (Instagram deep scrape)
# Cấu hình trong Configuration/Configuration.ini: [Settings] apify_token=

# === Scan Tuning ===
MR_HOLMES_CONCURRENCY=20    # số site scan đồng thời (default: 20)
```

File `.env` KHÔNG được commit vào git (đã có trong `.gitignore`).

### Cấu hình `Configuration/Configuration.ini`

```ini
[Settings]
Language = English
DateFormat = %Y-%m-%d
ShowLogs = False
DatabaseEnabled = True
ProxyList = Proxies/proxy_list.txt
UseragentList = Useragents/useragent_list.txt
apify_token = none
```

### Config wizard (tùy chọn)

Thay vì sửa tay file `.env`, dùng wizard tích hợp:

```bash
python3 MrHolmes.py --config api-keys
```

---

## Chạy ứng dụng

### Interactive mode

```bash
python3 MrHolmes.py
```

Menu hiển thị 16 option. Option 16 là Autonomous Profiler.

### Batch mode (không cần tương tác)

```bash
# Scan username
python3 MrHolmes.py --username johndoe

# Scan email
python3 MrHolmes.py --email user@example.com

# Scan phone
python3 MrHolmes.py --phone +84901234567

# Export PDF investigation #1
python3 MrHolmes.py --export pdf --investigation 1

# Export CSV tất cả investigations
python3 MrHolmes.py --export csv --investigation all
```

### Autonomous Profiler trực tiếp (Option 16)

Chạy từ interactive menu → chọn `16`, hoặc implement entry point riêng:

```python
from Core import autonomous_cli
autonomous_cli.AutonomousCLI.run(Mode)
```

### PHP GUI

```bash
cd GUI
php -S localhost:8080
# Truy cập http://localhost:8080
```

---

## Chạy tests

```bash
# Tất cả tests
pytest

# Với coverage report
pytest --cov=Core --cov-report=term-missing

# Test một module cụ thể
pytest tests/test_plugins.py -v

# Test async (yêu cầu pytest-asyncio)
pytest test_epic7_suite.py -v
```

### Cấu hình pytest

`pytest.ini` ở root directory. Asyncio mode đã được cấu hình sẵn — test async function không cần decorator bổ sung ngoài `@pytest.mark.asyncio`.

---

## Thêm Intelligence Plugin mới

1. Tạo file mới trong `Core/plugins/`, ví dụ `Core/plugins/virustotal.py`

2. Implement `IntelligencePlugin` Protocol:

```python
from Core.plugins.base import IntelligencePlugin, PluginResult

class VirusTotalPlugin:
    @property
    def name(self) -> str:
        return "VirusTotal"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def check(self, target: str, target_type: str) -> PluginResult:
        if target_type not in ("IP", "DOMAIN", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Unsupported type: {target_type}",
            )
        # ... gọi VirusTotal API
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={"malicious": False, "detections": 0},
        )
```

3. `PluginManager.discover_plugins()` sẽ tự tìm và đăng ký class này — không cần sửa code khác.

4. Thêm API key vào `.env`:

```dotenv
VIRUSTOTAL_API_KEY=your_key_here
```

5. Đọc API key trong plugin:

```python
from Core.config import settings
api_key = settings.get_plugin_key("VIRUSTOTAL")
```

---

## Thêm site mới vào username scanner

Không cần viết Python code. Chỉ cần thêm entry vào `Site_lists/Username/site_list.json`:

```json
{
  "name": "NewSite",
  "url": "https://newsite.com/{}",
  "errorType": "message",
  "errorMsg": "User not found",
  "tags": ["social"]
}
```

Trường `{}` là placeholder cho username. `errorType` có thể là `"message"` (kiểm tra text trong response) hoặc `"status_code"` (kiểm tra HTTP status).

---

## Thêm platform scraper mới

1. Thêm method vào `Core/Support/Username/Scraper.py`:

```python
class info:
    @staticmethod
    def NewPlatform(report_path, username, proxy, ...):
        # scrape profile data
        pass
```

2. Đăng ký vào `ScraperRegistry` trong `Core/engine/scan_pipeline.py`:

```python
registry.register("NewPlatform", lambda p: Scraper.info.NewPlatform(
    report_path, username, p, ...
))
```

3. Tên `"NewPlatform"` phải khớp với field `"name"` trong `site_list.json`.

---

## Code quality

```bash
# Linting
flake8 Core/ --max-line-length=120

# Type hints (nếu dùng mypy)
mypy Core/engine/ Core/plugins/
```

---

## Lưu ý quan trọng

- Mọi HTTP call phải đi qua proxy pipeline của `ProxyManager` — không dùng `requests` trực tiếp trong code mới
- Secrets (API keys, passwords) KHÔNG được hardcode — luôn đọc từ `settings` hoặc environment variables
- Output tiếng Việt trong CLI phải dùng `Language.Translation.Translate_Language()` — không hardcode string UI
- SQLite database path mặc định là `GUI/Reports/mrholmes.db` — dùng `Database.get_instance()` thay vì tạo connection riêng
