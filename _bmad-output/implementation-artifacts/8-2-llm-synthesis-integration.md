# Story 8.2: LLM Synthesis Integration

Status: review

## Story
**As an** OSINT Investigator
**I want** the system to automatically synthesize the raw JSON graph collected by the Recursive Profiler into a readable, professional analyst report
**So that** I don't have to manually read hundreds of raw data records — the AI tells me what it means.

## Acceptance Criteria
- [x] Implement `Core/engine/llm_synthesizer.py` containing a `LLMSynthesizer` class.
- [x] The synthesizer must accept a `ProfileGraph` dict (output from `RecursiveProfiler.run_profiler()`) as input.
- [x] The synthesizer calls an OpenAI-compatible API endpoint (configured via env vars `MH_LLM_BASE_URL`, `MH_LLM_API_KEY`, `MH_LLM_MODEL`).
- [x] The synthesizer uses a structured system prompt that instructs the LLM to act as an OSINT Analyst and produce a professional Markdown report.
- [x] The produced report must contain sections: Executive Summary, Entities Discovered, Key Relationships, Risk Assessment, Recommended Next Steps.
- [x] If LLM credentials are missing or the API call fails, the synthesizer gracefully returns a fallback plaintext summary (no crash).
- [x] The synthesizer must be asynchronous (`async def synthesize()`).
- [x] The class must be independently testable with a mock HTTP client — no real API calls needed in tests.

## Project Context Reference
- Epic context: Epic 8 - Autonomous Profiler (Deep OSINT Agent)
- Story 8.1 output (`RecursiveProfiler.run_profiler()`) is the input for this story.
- FR28: "Hệ thống có thể tổng hợp và phân tích báo cáo tri thức tự động thông qua các API tương thích OpenAI của LLM."
- Dependencies: `aiohttp` (already in requirements), `openai` SDK or raw HTTP call.

## Implementation Sandbox

### API Contract
- Environment variables:
  - `MH_LLM_BASE_URL`: Base URL for OpenAI-compatible endpoint (e.g., `https://api.openai.com/v1` or local Ollama `http://localhost:11434/v1`)
  - `MH_LLM_API_KEY`: API key (use `"ollama"` for local Ollama)
  - `MH_LLM_MODEL`: Model name (e.g., `gpt-4o`, `gemma3:latest`, `deepseek-r1`)

### Approach
- Use raw `aiohttp` POST to `/chat/completions` (OpenAI-compatible format) to avoid hard dependency on `openai` SDK.
- Build a structured prompt from `ProfileGraph` dict:
  - Count nodes, list unique target types, list top discovered emails/IPs.
  - Include plugin results summary (success/fail counts per plugin).
- System prompt: "You are an elite OSINT analyst. You receive structured reconnaissance data in JSON. Produce a professional intelligence report in Markdown..."
- Batch approach: send all data in one call to minimize API cost.

### Input signature
```python
async def synthesize(self, graph: dict) -> SynthesisResult:
    # graph is output from RecursiveProfiler.run_profiler()
```

### Output dataclass
```python
@dataclass
class SynthesisResult:
    is_success: bool
    report_markdown: str  # Full markdown report
    model_used: str
    error_message: str | None = None
```

## File List
- `Core/engine/llm_synthesizer.py` [NEW] — LLMSynthesizer class with aiohttp POST + fallback report
- `tests/engine/test_llm_synthesizer.py` [NEW] — 17 unit tests (import, dataclass, success, fallback, prompt)

## Dev Agent Record

### Implementation Plan
- Raw `aiohttp` POST to `/chat/completions` endpoint — no `openai` SDK dependency
- `SynthesisResult` dataclass mirrors `PluginResult` pattern from Story 8.1
- `_build_user_prompt()` summarizes graph data compactly (node/edge counts, plugin stats, entity sample) to minimize LLM tokens
- `_SYSTEM_PROMPT` instructs LLM to produce fixed 5-section Markdown report
- `_build_fallback_report()` generates machine-readable summary when LLM unavailable
- Constructor falls back to `os.environ` for all 3 config vars

### Completion Notes
- 17/17 new tests PASS (RED → GREEN cycle completed)
- Zero additional regressions in existing test suite
- `temperature=0.3` for deterministic, factual reporting
- Timeout=120s to accommodate slow remote LLM providers

## Change Log
- 2026-03-30: Story 8.2 created and implemented. Status → review.
