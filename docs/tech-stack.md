# Tech Stack

## Primary Application (CLI)
- **Language:** Python 3
- **Ecosystem:** `pip` for dependency management (details in `requirements.txt`).
- **Networking:** HTTP request manipulation for OSINT gathering, coupled with proxy usage (`ip-api.com` integration).
- **Configuration:** INI files built with `configparser` and extensive JSON files for site mapping definitions.

## GUI Application
- **Language:** PHP
- **Styling:** CSS (`GUI/Css/`) and thematic styling (`GUI/Theme/`).
- **Data Intake:** Consumes `.txt`, `.mh`, and `.json` files placed in `GUI/Reports/`.

## Scripting & Automation
- **Install Scripts:** Extensive `bash` scripting via `install.sh` and `install_Termux.sh` to handle dependencies, python package installation, and execution permissions across Linux variants and Termux.
