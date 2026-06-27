# Hướng dẫn Tích hợp Mr.Holmes MCP

## Tổng quan
Mr.Holmes 2.0 expose các công cụ OSINT qua MCP (Model Context Protocol), cho phép Claude Code đóng vai trò một thám tử AI điều phối các cuộc điều tra.

## Bắt đầu nhanh

### 1. Cài đặt dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. Cấu hình Claude Code
Thêm vào `.devin/config.json` trong project của bạn:

\`\`\`json
{
  "mcpServers": {
    "mr-holmes": {
      "command": "python3.10",
      "args": ["-m", "Core.mcp.server"],
      "cwd": "/path/to/Mr.Holmes"
    }
  }
}
\`\`\`

### 3. Cấu hình API keys (tùy chọn)
Copy `.env.example` sang `.env` và điền API keys:

\`\`\`bash
cp .env.example .env
# Chỉnh sửa .env với API keys của bạn
\`\`\`

Các API key tùy chọn:
- `MH_HAVEIBEENPWNED_API_KEY` — dữ liệu breach từ HIBP
- `MH_LEAKLOOKUP_API_KEY` — LeakLookup
- `MH_SHODAN_API_KEY` — Shodan
- `MH_NUMVERIFY_API_KEY` — tra cứu số điện thoại Numverify
- `MH_INTELX_API_KEY` — tìm kiếm breach IntelX

### 4. Kiểm tra kết nối
Trong Claude Code, hỏi: "List available Mr.Holmes plugins"
Claude sẽ gọi `list_plugins` và hiển thị 10+ plugin.

### 5. Chạy investigation đầu tiên
Hỏi Claude: "Investigate username torvalds"
Claude sẽ:
1. Tạo một case điều tra
2. Chạy Maigret (500+ sites)
3. Kiểm tra GitHub profile
4. Trích xuất email → kiểm tra breach
5. Tạo dorks
6. Lưu tất cả bằng chứng
7. Xuất báo cáo tiếng Việt

## Các công cụ có sẵn

### Username OSINT
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| search_username | Tìm trên 500+ sites | Không |
| run_maigret | Maigret 509 sites | Không |
| scrape_profile | Scrape bằng browser (Playwright) | Không |

### Email OSINT
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| search_email | Holehe — sites đã đăng ký | Không |
| check_breach | Kiểm tra breach HIBP | Có |
| check_leak | LeakLookup | Có |
| validate_email | Kiểm tra format | Không |

### Phone OSINT
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| search_phone | Numverify carrier/location | Có |
| validate_phone | Kiểm tra format | Không |

### Domain/IP OSINT
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| search_domain | Phân giải DNS | Không |
| scan_ports | Quét port | Không |
| shodan_lookup | Dịch vụ Shodan | Có |
| whois_lookup | Dữ liệu WHOIS | Không |

### Person OSINT
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| search_person | Tìm người qua SearxNG | Không |
| generate_dorks | Google/Yandex dorks | Không |
| run_searxng | Truy vấn SearxNG tùy chỉnh | Không |

### Entity Resolution
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| resolve_entities | Gộp thành golden record | Không |
| run_profiler | BFS mở rộng entity | Không |

### Evidence Store
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| create_investigation | Tạo case mới | Không |
| save_evidence | Lưu bằng chứng | Không |
| query_evidence | Truy vấn bằng chứng | Không |
| get_investigation | Toàn bộ case file | Không |
| list_investigations | Tất cả case | Không |

### Utility
| Tool | Mô tả | Cần API Key |
|------|-------|-------------|
| decode_text | Base64/MD5/SHA256 | Không |
| list_plugins | Liệt kê plugin có sẵn | Không |
| run_plugin | Chạy plugin cụ thể | Tùy |

## Quy trình điều tra

\`\`\`
User: "Tìm thông tin về deptraidapxich"

Claude Code:
  → create_investigation("deptraidapxich", "username")
  → run_maigret("deptraidapxich") → 3 profiles found
  → run_plugin("GitHub", "deptraidapxich", "username") → not found
  → run_plugin("Reddit", "deptraidapxich", "username") → not found
  → generate_dorks("deptraidapxich", "google")
  → save_evidence(...) cho mỗi kết quả
  → Phân tích: "Tìm thấy 3 profiles trên Odysee, Wowhead, Mastodon"
  → Hỏi user: "Bạn có biết email của người này không?"
  → User cung cấp email
  → search_email(email) → 5 registered sites
  → check_breach(email) → 2 breaches
  → save_evidence(...)
  → get_investigation(id) → full case
  → Xuất báo cáo tiếng Việt
\`\`\`

## Browser Automation (tùy chọn)

Cho các site chặn HTTP request (Instagram, Twitter, TikTok):

\`\`\`bash
pip install playwright
playwright install chromium
\`\`\`

Tool `scrape_profile` sẽ tự động dùng Playwright khi có sẵn.

## Khắc phục sự cố

### MCP server không kết nối
- Kiểm tra Python path: `which python3.10`
- Kiểm tra đường dẫn Mr.Holmes trong config
- Chạy thủ công: `python3.10 -m Core.mcp.server`

### Lỗi API key
- Kiểm tra file `.env` tồn tại và có key đúng
- Chạy: `python3.10 -c "from Core.config.settings import settings; print(settings.get_plugin_key('HaveIBeenPwned'))"`

### Playwright không hoạt động
- Cài đặt: `pip install playwright && playwright install chromium`
- Kiểm tra: `python3.10 -c "from playwright.async_api import async_playwright; print('OK')"`
