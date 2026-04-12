# Story 9.16: Personality Analysis & Behavioral Timeline

Status: ready-for-dev

## Story

As an OSINT analyst,
I want the AI report to include Big-5 personality trait analysis and a behavioral timeline,
so that I can understand not just who the target is but how they behave and when they are active.

## Acceptance Criteria

1. `PersonalityAnalyzer` class tại `Core/engine/personality_analyzer.py`:
   - `analyze(profile: ProfileEntity) -> PersonalityReport` — sync method (LLM call bên trong)
   - Input: `ProfileEntity` với `bios`, `active_hours`, writing_samples (từ Reddit)
   - Output: `PersonalityReport` dataclass

2. `PersonalityReport` dataclass:
   ```python
   @dataclass
   class PersonalityReport:
       big5: dict[str, str]          # {"openness": "High", "conscientiousness": "Medium", ...}
       big5_evidence: dict[str, list[str]]  # {"openness": ["diverse subreddits", "GitHub bio: creative"]}
       active_hours: dict[str, Any]  # {"timezone": "UTC+7", "peak": "22:00-02:00", "confidence": 0.7}
       interests: list[str]          # ["music production", "Python", "travel"]
       behavioral_notes: list[str]   # AI-generated behavioral observations
       confidence: float
       disclaimer: str               # Always: "AI-generated hypothesis — requires human verification"
   ```

3. Big-5 inference prompt:
   - Chỉ dùng evidence từ `ProfileEntity` — không invent data
   - Mỗi trait có `evidence` list để analyst biết suy luận từ đâu
   - Trả về `"Unknown"` thay vì guess nếu không đủ data

4. Behavioral Timeline:
   - `build_timeline(profile: ProfileEntity, graph_data: dict) -> list[TimelineEvent]`
   - `TimelineEvent`: `{"timestamp": "2024-03", "event": "Registered on Spotify", "source": "Holehe"}`
   - Extract từ:
     - Breach dates (HIBP/LeakLookup `breach_dates` field)
     - Account creation dates nếu có từ plugin results
     - Post timestamps từ Reddit/Instagram
   - Sort chronologically

5. Integration với `LLMSynthesizer.synthesize_profile()` (Story 9.11):
   - `synthesize_profile()` gọi `PersonalityAnalyzer.analyze()` trước khi build prompt
   - `PersonalityReport` inject vào prompt thay vì yêu cầu LLM self-analyze

6. Tất cả `PersonalityReport` content luôn có disclaimer: `"[AI-generated hypothesis]"` — không được omit

7. Unit tests tại `tests/engine/test_personality_analyzer.py` ≥ 80% coverage:
   - Test `analyze()` với rich ProfileEntity → returns all 5 traits
   - Test `analyze()` với sparse ProfileEntity → "Unknown" traits với low confidence
   - Test `build_timeline()` → sorted events
   - Test disclaimer always present
   - Mock LLM client — không thực sự call API

## Tasks / Subtasks

- [ ] Task 1: Tạo `PersonalityReport` dataclass (AC: 2)
- [ ] Task 2: Tạo `PersonalityAnalyzer` class (AC: 1)
- [ ] Task 3: Implement `analyze()` — build Big-5 prompt + parse LLM response (AC: 3)
  - [ ] Đọc `LLMSynthesizer` pattern để reuse LLM client
  - [ ] Parse structured JSON response từ LLM cho Big-5
- [ ] Task 4: Implement `build_timeline()` (AC: 4)
  - [ ] Extract từ `breach_dates` trong plugin_results
  - [ ] Sort + format
- [ ] Task 5: Update `LLMSynthesizer.synthesize_profile()` để dùng `PersonalityReport` (AC: 5)
- [ ] Task 6: Viết unit tests (AC: 7)

## Dev Notes

### Big-5 Prompt Design

```
Given these verified OSINT data points about a person:
- Bios: {bios_list}
- Subreddits: {subreddits}
- Active platforms: {platforms}
- Writing samples: {samples}

Analyze their personality using the Big-5 model. For each trait, cite specific evidence.
Respond in JSON:
{
  "openness": {"level": "High|Medium|Low|Unknown", "evidence": ["..."]},
  "conscientiousness": {"level": "...", "evidence": [...]},
  ...
}

If insufficient data for a trait, use "Unknown". Do NOT invent data.
```

### Timeline Builder

```python
def build_timeline(self, profile: ProfileEntity, graph_data: dict) -> list[dict]:
    events = []
    for pr in graph_data.get("plugin_results", []):
        data = pr.get("data", {})
        plugin = pr.get("plugin", "")
        for date, name in zip(data.get("breach_dates", []), data.get("breach_names", [])):
            if date:
                events.append({
                    "timestamp": date,
                    "event": f"Data breach: {name}",
                    "source": plugin,
                })
    events.sort(key=lambda e: e.get("timestamp", ""))
    return events
```

### LLM Response Parsing

LLM response cho Big-5 sẽ là JSON string — parse với `json.loads()`, fallback về `{"level": "Unknown", "evidence": []}` nếu parse fails.

### File Locations

| File | Action |
|------|--------|
| `Core/engine/personality_analyzer.py` | CREATE |
| `Core/engine/llm_synthesizer.py` | MODIFY — integrate PersonalityReport |
| `tests/engine/test_personality_analyzer.py` | CREATE |

### Dependencies

- Story 9.11 (`LLMSynthesizer.synthesize_profile()`) — modified để accept `PersonalityReport`
- Story 9.1 (`ProfileEntity`) — input data model

### References

- `Core/engine/llm_synthesizer.py` (Stories 8.2, 9.11)
- `Core/models/profile_entity.py` (Story 9.1)
- PRD FR30: personality traits từ behavioral patterns

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
- `Core/engine/personality_analyzer.py` (created)
- `Core/engine/llm_synthesizer.py` (modified)
- `tests/engine/test_personality_analyzer.py` (created)
