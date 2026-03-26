# Source Tree Analysis

## Annotated Directory Structure

The Mr.Holmes codebase is organized into several distinct functional areas, separating core logic from GUI presentation and underlying configurations.

```text
Mr.Holmes/
├── MrHolmes.py              # Main Entry Point (Python CLI)
├── Core/                    # Core Python Application Logic
│   ├── Searcher*.py         # Agent scripts (Username, Phone, Web, Person, etc.)
│   ├── Port_Scanner.py      # Network scanning agent
│   ├── Update.py            # Self-updating agent
│   └── Support/             # Shared Utilities (Proxies, HTTP, i18n, Fonts)
├── Configuration/           # Static INI based configurations
├── GUI/                     # Web-based UI layer (PHP)
│   ├── index.php            # UI Entry Point
│   ├── Actions/             # PHP request controllers
│   ├── Database/            # GUI DB abstractions
│   ├── Reports/             # Data output layer (JSON/TXT/MH) from Python agents
│   └── Theme/               # UI Styling components
├── Site_lists/              # Declarative JSON target definitions for OSINT
├── Banners/ & Quotes/       # Terminal ASCII aesthetics
├── Transfer/                # Output package and transfer utilities
└── Install scripts          # install.sh / install_Termux.sh / Install.cmd
```

## Critical Folders Explained
- **`Core/`**: The brain of the application. Contains all modular OSINT agents. If a new OSINT feature is added (e.g., Crypto tracking), it belongs here.
- **`Site_lists/`**: The operational muscle. It externalizes the scraping logic (URLs, error conditions, tags) into JSON, keeping the Python agents agnostic.
- **`GUI/`**: A standalone PHP application that strictly reads and visualizes data deposited into the `Reports/` directory. It does not actively trigger OSINT scans itself.
- **`GUI/Reports/`**: The bridge interface. Python writes data here, PHP reads it.
