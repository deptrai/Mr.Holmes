# Testing Strategy

## Current State
Presently, an exhaustive codebase scan reveals that there are **no automated testing suites** (unit, integration, or E2E) implemented in the repository.

## Future Testing Strategy Roadmap

To ensure robustness, especially when dealing with fragile OSINT scraping parameters that break when target sites change, the following strategy should be implemented:

1. **Unit Testing**
   - **Target:** `Core/Support/` utilities.
   - **Goal:** Ensure logging, proxy rotation algorithms, localization resolution (`Language.py`), and configuration parsing behave exactly as expected.
   - **Tool:** `pytest`.

2. **Integration Testing**
   - **Target:** `Core/Searcher*.py` classes (e.g., `MrHolmes.search`).
   - **Goal:** Validate the end-to-end data flow of a query traversing the OSINT agents without actually hitting real endpoints (to avoid rate limits or bans inside CI/CD).
   - **Mocking:** Use `responses` or `unittest.mock` to intercept `Requests_Search` logic and return known HTML/JSON structures for assertions.

3. **E2E / Output Validation**
   - **Target:** Output normalization.
   - **Goal:** Ensure generated reports correctly feed into the `GUI/` constraints (PHP views) so that upstream structural changes in report files don't break the web viewer.
