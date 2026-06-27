# 0010 Claude Code as Orchestrator

Date: 2026-06-26

## Status

Accepted

## Context

Mr.Holmes currently has a `StagedProfiler` (`Core/engine/autonomous_agent.py`)
that implements a fixed 4-phase BFS pipeline for recursive profiling:

- Phase A: Stage 2 plugins (identity expansion: Holehe, Maigret, GitHub)
- Phase B: Clue extraction from Stage 2 results
- Phase C: Stage 3 plugins (deep enrichment: Numverify, Hunter)
- Phase D: Stage 1 fallback (legacy plugins via RecursiveProfiler)

This hardcoded pipeline cannot adapt to unexpected findings. For example,
if Phase A discovers a phone number, the pipeline routes it to Stage 3
(Numverify) — but it cannot decide to also try Shodan on the phone's
carrier IP, or generate Google dorks for the discovered real name. The
phase ordering is static.

To achieve truly iterative, adaptive investigation, we need an AI
orchestrator that can:
1. Inspect intermediate results from any tool.
2. Form hypotheses ("this username likely belongs to the same person as
   this email").
3. Decide which tool to call next based on findings so far.
4. Pivot strategies when a lead goes cold.
5. Synthesize a final report with confidence assessment.

The question is: should we build this AI orchestration layer internally
(inside Mr.Holmes), or delegate it to an external AI orchestrator (Claude
Code)?

## Decision

Use **Claude Code as the AI orchestrator**. Do NOT build an internal AI
orchestration engine.

Mr.Holmes will expose fine-grained OSINT tools via MCP (see ADR-0009).
Claude Code calls these tools, reasons about results, and drives the
investigation flow. Mr.Holmes remains a **tool collection** — it collects
data, Claude Code thinks.

The existing `StagedProfiler` is preserved as one available tool
(`run_profiler`) for batch-mode operation, but it is no longer the primary
investigation driver. The `EntityResolver` is also exposed as a tool
(`resolve_entities`) for Claude Code to call when it wants to merge
findings.

## Alternatives Considered

1. **Build internal AI orchestrator using an LLM API (OpenAI/Anthropic)**
   — Would require: prompt engineering for tool routing, context window
   management, retry/fallback logic, hypothesis tracking, and a
   conversation state machine. This is essentially rebuilding what Claude
   Code already does, but worse, because we'd be building an AI agent
   framework inside an OSINT tool. High maintenance burden, duplicates
   Claude Code's capabilities.

2. **Use LangChain/LangGraph for orchestration** — Adds a heavy framework
   dependency. LangGraph's agent loop is less capable than Claude Code's
   native reasoning for this use case. Still requires us to maintain the
   orchestration logic.

3. **Keep StagedProfiler as the only engine, add more phases** —
   Fundamentally limited by hardcoded phase ordering. Adding phases for
   every possible pivot path is combinatorially explosive and still can't
   handle truly adaptive reasoning.

4. **Hybrid: StagedProfiler for common patterns, Claude Code for complex
   cases** — Considered, but adds complexity without clear benefit. The
   `run_profiler` tool remains available for batch mode; Claude Code can
   choose to use it or call individual tools. No need for a separate
   hybrid mode.

## Consequences

Positive:

- Dramatically simpler codebase — no AI agent framework, no prompt
  engineering, no conversation state machine inside Mr.Holmes.
- Leverages Claude Code's superior reasoning, context management, and
  tool-calling capabilities (built and maintained by Anthropic).
- Investigation flow becomes fully adaptive — Claude Code can pivot, form
  hypotheses, and call tools in any order.
- Mr.Holmes team focuses on OSINT tool quality (data coverage, accuracy,
  bot-detection bypass) rather than AI orchestration.
- The `StagedProfiler` code is preserved and still useful for batch/CLI
  mode — no wasted work.

Tradeoffs:

- Hard dependency on Claude Code for the primary interactive flow. If
  Claude Code is unavailable, users fall back to CLI/REST (batch mode,
  no AI reasoning).
- Investigation quality depends on Claude Code's reasoning ability and
  context window size. Very large investigations (hundreds of tool calls)
  may hit context limits — mitigated by Evidence Store (query past
  results instead of keeping in context).
- Less control over the orchestration logic — we cannot force Claude Code
  to follow a specific investigation protocol. Mitigated by tool design
  (e.g., `safe_mode` flag excludes high-risk sources).
- Debugging investigation flows requires inspecting Claude Code's
  conversation, not just Mr.Holmes logs. The audit_log table (ADR-0012)
  provides server-side traceability.

## Follow-Up

- Ensure all tools return structured, Claude-friendly output (JSON with
  clear field names, not raw HTML).
- Design tools with appropriate granularity — not too fine (100 tiny tools
  overwhelms context) nor too coarse (1 mega-tool prevents reasoning).
- Implement Evidence Store (ADR-0012) so Claude Code can offload findings
  to SQLite instead of keeping everything in context.
- Document recommended investigation patterns in a Claude Code prompt
  guide.
