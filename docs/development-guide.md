# Development Guide

## Environment Setup
1. **Prerequisites:**
   - UNIX-based OS (macOS/Linux) or Android (Termux)
   - Python 3.8+
   - PHP 7.4+ (If running the GUI)
2. **Installation:**
   ```bash
   git clone <repo-url> Mr.Holmes
   cd Mr.Holmes
   chmod +x install.sh
   ./install.sh
   ```

## Local Development Commands
- **Run the CLI Interface:**
  ```bash
  python3 MrHolmes.py
  ```
- **Run the PHP GUI Environment:**
  Navigate to the `GUI` folder and spin up a local PHP server:
  ```bash
  cd GUI
  php -S localhost:8080
  ```

## Adding New Target Sites (No-Code Extension)
Developers can extend the OSINT capabilities of Mr.Holmes without writing Python code by updating the JSON configurations in `Site_lists/`.

Example for adding a new Username target:
1. Open `Site_lists/Username/Sites.json`
2. Add a new object defining the URL schema (using `{}` as a placeholder for the username), the error message indicating non-existence, and tags.

## Contribution Guidelines
- **Modularity:** New OSINT tools should be encapsulated as new `.py` files inside `Core/` and wired into `Core/Support/Menu.py`.
- **i18n:** Avoid directly writing English or Vietnamese text into the UI. Always define keys in the `Lang/` files and fetch them centrally via `Core.Support.Language`.
- **Proxies:** Ensure all HTTP calls inherit the active proxy configuration pipeline setup by `Core.Support.Proxies` to prevent IP leakage.
