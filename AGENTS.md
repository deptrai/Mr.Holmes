# Mr.Holmes – Agents & Architecture Overview

## 1. Project Purpose

Mr.Holmes is an OSINT (Open Source Intelligence) tool focused on **information gathering** for:

- **Usernames**
- **Phone numbers**
- **Websites/domains** (including WHOIS and related data)
- **Persons**
- **Ports and network exposure**
- **Emails**
- **Google / Yandex dorks** for targeted searches

The tool relies on **public data sources** on the internet and uses:

- **Proxies** to anonymize requests
- **Google dorks / Yandex dorks** for advanced search patterns
- **Web scraping + JSON site definitions** for structured OSINT
- **A mix of CLI and GUI (PHP-based) interfaces**

---

## 2. High-Level Architecture

At a high level, the project is organized into these layers:

1. **Entry Point Layer**
   - `MrHolmes.py`

2. **Core Search / Analysis Agents**
   - Username, phone, website, person, ports, email, dorks, decoder, PDF, transfer, sessions.

3. **Support & Utility Agents**
   - Language/i18n, banners, clear screen, proxies, HTTP/search, logs, notifications, recap, encoding, site counters, credentials, etc.

4. **Configuration & Data Layer**
   - INI configuration, text config files, JSON site lists, language files, quotes, banners.

5. **GUI & Reporting Layer**
   - File-based reports under `GUI/Reports/...`
   - PHP GUI and database visualization layer (as described in docs).

The existing `docs/brownfield-analysis-Mr.Holmes-2025-10-08.md` further describes the architecture with a mermaid diagram; this document summarizes it in an “agents view”.

---

## 3. Entry Point Agent

### 3.1 `MrHolmes.py`

**Role:** Application entry point and high-level dispatcher.

Key responsibilities:

- Import the main menu controller and support modules:
  - `from Core.Support import Menu, Font, Language`
- Detect and validate the **display mode** (Desktop / Mobile) from `Display/Display.txt`:
  - `Main.Controll_Display()` reads the file and ensures its value is `Desktop` or `Mobile`.
- Delegate to the menu controller:
  - `Main.Menu(Mode)` → calls `Menu.Main.main(Mode)` to start the interactive CLI loop.

This “agent” is the **front door** of the CLI experience.

---

## 4. Menu & Orchestration Agent

### 4.1 `Core/Support/Menu.py` – `Main` class

**Role:** Central orchestrator that connects user inputs to specialized OSINT agents.

Key responsibilities:

- Show the **banner** and randomly-selected quotes.
- Resolve **language and localization** for menu texts using `Language.Translation`.
- Display the **main options menu** (Desktop or Mobile variant).
- Enter an infinite loop where it:
  - Shows options and prompts: `[#MR.HOLMES#]-->`
  - Converts input into an integer `sce`.
  - Dispatches to the appropriate specialized agent based on `sce`.

Main options and their agents (simplified):

- **1 – Username OSINT** → `Core.Searcher.MrHolmes.search(username, Mode)`
- **2 – Phone OSINT** → `Core.Searcher_phone.Phone_search.searcher(phone, Mode)`
- **3 – Website/Domain OSINT** → `Core.Searcher_website.Web.search(site, Mode)`
- **4 – Configuration** → `Core.config.Config.main(Mode)`
- **5 – Database GUI** → `Core.Support.Database.Controller.Gui()`
- **6 – Update** → `Core.Update.Downloader.Check_Creds()` (Windows) or run `Core/update.sh` (Unix)
- **7 – Port Scanner** → `Core.Port_Scanner.Ports.Main(target, Mode)`
- **8 – Email OSINT** → `Core.E_Mail.Mail_search.Search(email, Mode)`
- **9 – Google Dorks** → `Core.Dork.List.Main(param, Mode)`
- **10 – Person OSINT** → `Core.Searcher_person.info.Search(param, Mode)`
- **11 – Decoder utilities** → `Core.Decoder.Menu.Main(param, Mode)`
- **12 – PDF conversion** → `Core.PDF_Converter.Menu.Main(param, Mode)`
- **13 – Transfer utilities** → `Core.Transfer.Menu.Main(param, Mode)`
- **14 – Session management** → `Core.Session.Options.View()`
- **15 – Exit** → print localized exit message and terminate.

This class is effectively the **“Controller/Router Agent”** of the CLI.

---

## 5. Core Search & Analysis Agents

### 5.1 Username OSINT Agent – `Core/Searcher.py` (`MrHolmes` class)

**Role:** Perform username reconnaissance across many websites and social platforms.

Key capabilities:

- Use **site list JSON** files under `Site_lists/Username/` to define:
  - URLs, error patterns, tags, and scraping rules per site.
- Orchestrate **HTTP requests** via `Core.Support.Requests_Search` and **proxy** setup via `Core.Support.Proxies`.
- Optionally perform **profile scraping** via `Core.Support.Username.Scraper` for platforms like Instagram, Twitter, TikTok, GitHub, GitLab, NGL, Tellonym, Gravatar, Chess.
- Manage **reports and recap files** under `GUI/Reports/Usernames/{username}`.
- Manage **NSFW optional search** with additional site lists.
- Log attempts and results via `Core.Support.Logs` and produce recap `.txt` / `.mh` files.

### 5.2 Phone OSINT Agent – `Core/Searcher_phone.py`

**Role:** Search and analyze phone numbers across multiple sources.

Capabilities (pattern similar to username agent):

- Use dedicated **site lists** for phone-related searches.
- Orchestrate requests via the same support stack (proxies, Requests_Search, logs).
- Produce reports under `GUI/Reports/Phones/...` (exact structure defined in that module).

### 5.3 Website / Domain OSINT Agent – `Core/Searcher_website.py`

**Role:** Investigate websites and domains.

Typical responsibilities (based on patterns and docs):

- Use **WHOIS** APIs (and/or CLI tools) to gather domain registration data.
- Use site lists and dorks tailored for domain discovery.
- Generate reports under `GUI/Reports/Websites/...`.

### 5.4 Person OSINT Agent – `Core/Searcher_person.py`

**Role:** Higher-level person investigation (beyond username only).

Capabilities:

- Combine multiple data sources to profile individuals.
- Use site lists and scrapers to collect information related to a person’s name or alias.

### 5.5 Port Scanner Agent – `Core/Port_Scanner.py`

**Role:** Scan ports on a given host and evaluate its network exposure.

- Wraps around scanning logic (likely custom or using standard libraries) to show open ports and services.

### 5.6 Email OSINT Agent – `Core/E_Mail.py`

**Role:** Investigate email addresses.

- Use configuration settings for SMTP / email behaviors.
- Check presence / usage of an email across selected online services.

### 5.7 Dorks Agent – `Core/Dork.py` + `Core/Searcher.MrHolmes.Google_dork` & `Yandex_dork`

**Role:** Generate and run **Google / Yandex dorks**.

- Use specific text files like `Site_lists/Username/Google_dorks.txt` or `.../Yandex_dorks.txt`.
- Produce dork lists in `GUI/Reports/Usernames/Dorks/`.

### 5.8 Decoder Agent – `Core/Decoder.py`

**Role:** Provide various encode/decode / OSINT helper utilities (exact features defined per submenu).

### 5.9 PDF Converter Agent – `Core/PDF_Converter.py`

**Role:** Convert results or data into PDF reports.

- Likely reads text or structured data and renders them into PDF output.

### 5.10 Transfer Agent – `Core/Transfer.py`

**Role:** Handle file transfer / result packaging workflows.

- Allows moving/exporting generated reports to other locations.

### 5.11 Session Agent – `Core/Session.py`

**Role:** Manage user sessions and saved states.

- `Session.Options.View()` displays current sessions / stored information.

---

## 6. Support & Utility Agents

### 6.1 Language & i18n – `Core/Support/Language.py`

**Role:** Centralized translation and language management.

- `Language.Translation.Get_Language()` and `Get_Language2()` resolve current CLI language settings.
- `Translate_Language(filename, section, key, default)` loads the right text from language files.
- Used widely in menu, searchers, configuration prompts, and error messages.

### 6.2 Visual & UX Support

- **Fonts & Colors** – `Core.Support.Font`
- **Clear Screen** – `Core.Support.Clear.Screen`
- **Banners & Quotes** – `Core.Support.Banner_Selector`, files under `Banners/` and `Quotes/`
- **Date & Time Formatting** – `Core.Support.DateFormat`
- These components act as **“Presentation Agents”** to keep UX consistent.

### 6.3 Networking & Proxies

- **Proxies** – `Core.Support.Proxies`
  - Manages `final_proxis`, `choice3`, and proxy identity location via `ip-api.com`.
- **Requests_Search** – `Core.Support.Requests_Search`
  - Standardized HTTP request handling, retries, and error handling.
- **Dorks** – `Core.Support.Dorks`
- **Site Counter** – `Core.Support.Site_Counter`

These agents orchestrate the low-level HTTP and proxy behavior that all OSINT agents share.

### 6.4 Data & File Handling

- **Logs** – `Core.Support.Logs`
- **Notification** – `Core.Support.Notification`
- **Recap** – `Core.Support.Recap`
- **Encoding** – `Core.Support.Encoding`
- **FileTransfer** – `Core.Support.FileTransfer`
- **Creds** – `Core.Support.Creds`

They provide reusable services for persistence, recap summaries, credentials, and auxiliary utilities.

---

## 7. Configuration & Data Layer

### 7.1 Configuration

- **Main configuration** – `Configuration/Configuration.ini` controlled via `Core.config.Config`.
- **Display mode** – `Display/Display.txt` read by `MrHolmes.Main.Controll_Display()`.
- **Language files** – located under language folders used by `Language.Translation`.

The `Config` agent supports:

- Editing email recipient, password, and destination.
- Writing config changes safely via `configparser`.

### 7.2 Site Definition & OSINT Sources

- **Site lists** – JSON files under `Site_lists/...` for username, phone, NSFW, etc.
- **Dork lists** – text files with Google/Yandex queries.
- These define:
  - Target URLs
  - Request patterns
  - Error strings
  - Whether a site is scrapable
  - Tags and metadata for grouping.

### 7.3 Reports & Recap Files

- All OSINT flows write into `GUI/Reports/...`, for example:
  - `GUI/Reports/Usernames/{username}/...`
  - Recap `.txt` and `.mh` summarizing findings.
- JSON structured results live side-by-side with text.

### 7.4 GUI & Database Layer (PHP-based)

From the brownfield analysis:

- There is a **PHP GUI** that acts as a visualization and control layer:
  - Controllers (actions)
  - Database views
  - Reports as GUI pages
- It reads the generated reports and JSON data and presents them to the user.

This effectively behaves as a **separate “Visualization Agent”** that consumes CLI-generated artifacts.

---

## 8. End-to-End Flow (Typical Username Investigation)

1. User runs `python3 MrHolmes.py`.
2. `MrHolmes.Main.Controll_Display()` validates `Display/Display.txt` (Desktop/Mobile).
3. `Menu.Main.main(Mode)` shows main menu.
4. User selects **option 1 (Username)**.
5. `Searcher.MrHolmes.search(username, Mode)` is called.
6. Searcher:
   - Cleans previous reports for that username.
   - Asks for proxy usage and configures `Proxies` if enabled.
   - Writes initial report headers and date.
   - Counts available sites (using site list JSON).
   - Iterates all sites and performs HTTP checks via `Requests_Search`, with per-site metadata.
   - Optionally enables NSFW search with a second site list.
   - Saves results and recap to text, `.mh`, JSON.
   - Optionally triggers scraping (Instagram/Twitter/TikTok/etc.).
7. User can then:
   - Open reports directly from filesystem.
   - Use GUI to visualize / explore the data.

Similar flows apply for phone, websites, email, etc.

---

## 9. Proposed Enhancements & New Features

### 9.1 UX & CLI Improvements

- **Rich CLI / TUI:**
  - Use libraries like `rich` / `textual` (or similar) for better tables, progress bars, and colored output.
  - Paginate long lists of sites and results.
- **Non-interactive / batch mode:**
  - Add command-line flags so investigations can run without manual prompts (useful for automation / CI or cron jobs).
  - Example: `--mode desktop --type username --target myuser --proxy on --nsfw off`.

### 9.2 Configuration & Security

- **Centralized secrets management:**
  - Move SMTP credentials and API keys out of `Configuration.ini` into `.env` or OS-level secrets.
  - Provide a small setup wizard to initialize config in a secure way.
- **Proxy provider abstraction:**
  - Abstract proxy sources so users can plug in different proxy lists or APIs.
  - Add **health checks** and automatic rotation for failing proxies.
- **Rate limiting & retry strategies:**
  - Centralize HTTP rate-limit handling in `Requests_Search` with exponential backoff.

### 9.3 OSINT Coverage Extensions

- **Pluggable OSINT providers:**
  - Define a **plugin interface** for new OSINT sources (social networks, forums, code platforms, etc.).
  - Allow new sources to be added only by **editing JSON/YAML files** and minimal Python glue.
- **Email breach checks:**
  - Integrate with services like *Have I Been Pwned* (requires external API key) to check breach exposure.
- **Metadata enrichment:**
  - Enrich results with geolocation, language, and risk scoring based on tags (e.g., financial, social, developer).

### 9.4 Data Model & Storage

- **Unified schema for findings:**
  - Normalize all results (username, phone, website, etc.) into a common JSON schema: `subject`, `type`, `source`, `evidence_url`, `status`, `tags`, `timestamp`.
- **Central database:**
  - Introduce an optional SQLite or lightweight DB layer so users can:
    - Search across all past investigations.
    - Filter by subject, tag, or date.
- **Better exports:**
  - Export to CSV, JSON, PDF, and HTML report formats from a single command.

### 9.5 Web GUI 2.0

- **REST API layer:**
  - Wrap the core CLI flows in a REST API (e.g., using FastAPI/Flask) while still keeping PHP GUI backward-compatible.
- **Modern frontend:**
  - Gradually replace/augment the PHP GUI with a modern frontend (React/Vue/Svelte) connected to the REST API.
- **Multi-user features:**
  - Authentication / authorization.
  - Per-user investigations and saved views.

### 9.6 Performance & Reliability

- **Async HTTP requests:**
  - Use `asyncio` + an async HTTP client to parallelize site checks and drastically reduce scan time.
- **Caching:**
  - Cache DNS resolutions and certain HTTP responses to avoid repeated lookups during a single session.
- **Robust error handling:**
  - Standardize exception handling and retries in `Requests_Search` and scraper modules.

### 9.7 Developer Experience & Quality

- **Automated tests:**
  - Unit tests for core utilities and agents.
  - Integration tests for full flows, with HTTP mocked.
- **Logging & observability:**
  - Structured logging with log levels and optional JSON logging for integrations.
- **Plugin SDK & documentation:**
  - Provide developer docs describing how to add new OSINT sources or agents.

### 9.8 Compliance, Ethics & Safety

- **Usage and consent tracking:**
  - Log user acceptance of legal disclaimers and intended use (research, red teaming, etc.).
- **Safe mode:**
  - Switch to exclude NSFW / legally sensitive sources by default; user must explicitly enable them.
- **Audit trail:**
  - Optional feature to record what queries were run and when, for internal compliance.

---

## 10. Summary

The Mr.Holmes project is organized around a **central menu agent** that routes user choices to specialized **OSINT agents** (username, phone, website, person, etc.), all powered by a strong **support layer** (proxies, HTTP, i18n, logs) and a **file-based reporting system** that can feed into a GUI.

The proposed enhancements focus on:

- Improving **UX and automation**
- Strengthening **configuration and security**
- Expanding **OSINT coverage**
- Normalizing **data and storage**
- Modernizing the **GUI & API surface**
- Raising **quality, reliability, and compliance**

This document should serve as a high-level map of the system and as a starting point for future refactoring, modernization, and feature planning.
