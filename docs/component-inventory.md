# Component Inventory

This document outlines the specific OSINT agents and components discovered during the deep codebase scan.

## 1. Core OSINT Agents (Python)

| Agent Component | File | Responsibility |
| --- | --- | --- |
| **Username Searcher** | `Core/Searcher.py` | Validates usernames against hundreds of sites via JSON, triggers specific profile scrapers. |
| **Website Searcher** | `Core/Searcher_website.py` | Performs WHOIS, subdomain, and domain reconnaissance. |
| **Phone Searcher** | `Core/Searcher_phone.py` | OSINT across phone directories and databases. |
| **Email Searcher** | `Core/E_Mail.py` | Email verification and breach lookup support. |
| **Dork Generator** | `Core/Dork.py` | Orchestrates Google and Yandex dorks for targeted querying. |
| **Port Scanner** | `Core/Port_Scanner.py` | Active network mapping component. |

## 2. Shared Support Utilities

- **Menu Orchestrator:** Located in `Core/Support/Menu.py`, handles dynamic user input and UI control flow.
- **HTTP Wrapper (`Requests_Search.py`):** Centralizes `requests` logic, handles retries, timeout management, and integrates the proxy pipeline.
- **Proxy Provider (`Proxies.py`):** Configures proxy injection to ensure IP anonymity during OSINT workflows.
- **i18n Localization (`Language.py`):** Resolves console output into specific languages configured by the user.

## 3. GUI Components (PHP)

- **Report Viewers:** Logic mapping `GUI/Reports/` subdirectories (Username, Phones, etc.) into visual web pages.
- **Themes & Styling:** Standardized dark-themed CSS interfaces.
