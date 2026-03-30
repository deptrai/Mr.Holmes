# Story 8.4: CLI Menu Integration

Status: ready-for-dev

## Story
**As a** User of Mr.Holmes
**I want** to access the "Autonomous Profiler" directly from the main interactive CLI menu (Option 16)
**so that** I can seamlessly perform a deep, AI-driven, recursive OSINT scan on a specified target without writing Python scripts, and automatically receive the comprehensive Markdown report and HTML Mindmap in my Reports directory.

## Acceptance Criteria
- AC1: Provide a new file (e.g., `Core/autonomous_cli.py` or `Core/Support/Autonomous.py`) containing the interactive flow for the Autonomous Profiler.
- AC2: Prompt the user for:
    1. Target seed (e.g. `admin@facebook.com`)
    2. Target type (Must allow selecting `EMAIL`, `USERNAME`, `IP`, `DOMAIN`, `PHONE`)
    3. Maximum Depth (Default to 1, enforce valid integer `[0-3]` to prevent infinite loops)
- AC3: The CLI must invoke `RecursiveProfiler` (Story 8.1), then `LLMSynthesizer` (Story 8.2), and `MindmapGenerator` (Story 8.3) sequentially.
- AC4: Output files must be saved cleanly in a new specific report folder `GUI/Reports/Autonomous/{target}/`:
    - `raw_data.json`
    - `mindmap.html`
    - `ai_report.md`
- AC5: Update `Core/Support/Menu.py` to add `[ 16 ] Autonomous Profiler [AI]` to the main menu dispatcher.
- AC6: Add multi-language string support (via `Core.Support.Language`) for the new prompts and UI elements.

## Tasks/Subtasks
- [ ] 1. Identify where to place the new Autonomous CLI controller logic (`Core/autonomous_cli.py`).
- [ ] 2. Implement the `Input()` flow to collect Target, Type, and Depth with visual CLI styling (`Core.Support.Font`).
- [ ] 3. Implement full orchestration logic: Load plugins -> Run Profiler -> Run Mindmap -> Run LLMSynthesizer.
- [ ] 4. Implement file persistence: Save `.json`, `.html`, and `.md` artifacts into `GUI/Reports/Autonomous/<Target>/`.
- [ ] 5. Link the new CLI logic to Option `16` in `Core/Support/Menu.py` (Main `Main.main(Mode)` loop).
- [ ] 6. Ensure strings correctly go through `Language.Translation.Translate_Language` where possible.
- [ ] 7. Clean up and test visually in terminal (Run `python3 MrHolmes.py`, Option 16).

## Dev Notes
- **Environment config loading**: Ensure you load plugin API keys and LLM variables the same way they were loaded in the E2E demo script (`dotenv.load_dotenv(".env")` might be needed if not fully handled globally, or use OS enviroment).
- **Asynchronous Execution**: Ensure you use `asyncio.run()` when invoking the asynchronous orchestration logic from the synchronous `Menu.py` dispatcher.
- **Reporting path**: You might need to use `os.makedirs(folder_path, exist_ok=True)` safely.
- **Feedback**: Print intermediate progress messages (e.g. "[*] Extracting Clues...", "[*] Requesting LLM synthesis...") to keep the UX responsive.

## Dev Agent Record
- **Debug Log**:
- **Completion Notes**:

## File List
- `[NEW] Core/autonomous_cli.py`
- `[MODIFY] Core/Support/Menu.py`
- `[MODIFY] Core/Support/Language.py` (if strings defined centrally)

## Change Log
- 2026-03-31: Story created and marked ready-for-dev.
