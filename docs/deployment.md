# Deployment

## Distribution Method
Mr.Holmes is designed to be pulled directly from its source repository and executed in a local or containerized environment. It relies heavily on local installation scripts rather than a standalone binary or Docker image.

## Installation Scripts
The root directory provides execution scripts catering to standard Unix environments as well as Android environments:
- `install.sh`: A comprehensive bash script to handle Python 3 installations, `pip` package installation, permissions, and directory setups.
- `install_Termux.sh`: A tailored script aimed at Android's Termux emulator environment.

## Dependencies
- **System:** `python3` and `pip` required. A local web server with PHP support is required if the user intends to use the `GUI/` viewer.
- **Python Packages:** Listed directly in `requirements.txt`. Must be installed prior to initiating the main script.

## Execution
The application starts interactively via the terminal:
```bash
python3 MrHolmes.py
```
The application dynamically reads `Display/Display.txt` to conditionally format the interface for either `Desktop` or `Mobile`.
