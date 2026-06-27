# 0009 MCP Server Architecture

Date: 2026-06-26

## Status

Accepted

## Context

Mr.Holmes currently exposes its OSINT capabilities through two interfaces:
a legacy interactive CLI (`MrHolmes.py`) and a FastAPI REST API
(`Core/api/server.py`). Both are batch-oriented — the user (or API caller)
specifies a target, and the system runs all registered plugins concurrently
via `PluginManager.run_all()` or `StagedProfiler.run_staged()`, then returns
the full result set.

This batch model has a fundamental limitation: there is no iterative
reasoning. The system cannot look at intermediate results, decide which
plugin to call next, form hypotheses, or pivot based on discovered clues.
The `StagedProfiler` (`Core/engine/autonomous_agent.py`) attempts to
approximate this with a fixed 4-phase BFS pipeline, but the phase ordering
is hardcoded — it cannot adapt to unexpected findings.

We need a way for an AI orchestrator (Claude Code) to call individual OSINT
tools, inspect results, and decide the next step dynamically. This requires
a tool-calling interface with fine-grained, individually-addressable tools.

## Decision

Build an MCP (Model Context Protocol) server using the official Python `mcp`
SDK (`pip install mcp`, `FastMCP` class). The server will live at
`Core/mcp/server.py` and expose ~30 individually-addressable tools (see
`_bmad-output/planning-artifacts/mcp-tool-catalog.md`).

Each tool is a thin wrapper around existing components:
- `PluginManager` / individual plugins (`Core/plugins/`)
- `StagedProfiler` (`Core/engine/autonomous_agent.py`)
- `EntityResolver` (`Core/engine/entity_resolver.py`)
- `Database` / Evidence Store (`Core/reporting/database.py`)
- `ProxyManager` (`Core/proxy/manager.py`)

The MCP server becomes the **primary interface** for interactive
investigation. The existing CLI and REST API remain as secondary interfaces
for backward compatibility and non-AI automation.

Transport: stdio (default, for local Claude Code integration) with optional
SSE transport for remote deployments.

## Alternatives Considered

1. **Extend the REST API with OpenAI function-calling schema** — Would work
   but requires a separate function-calling layer; MCP is the standardized
   protocol purpose-built for this, with native Claude Code support and
   zero glue code.

2. **Build a custom JSON-RPC server** — Reinvents what MCP already provides
   (tool discovery, schema generation, transport handling). No ecosystem
   benefit.

3. **gRPC tool server** — Overkill for local single-user OSINT tooling.
   Adds protobuf compilation step and heavier dependency.

## Consequences

Positive:

- Claude Code becomes the primary interface with zero integration cost
  (built-in MCP client).
- Each OSINT capability is individually addressable — Claude Code can call
  `check_breach` without running all email plugins.
- Tool schemas auto-generated from Python type hints — no manual schema
  maintenance.
- Existing plugin/engine code is reused unchanged — MCP layer is pure
  wrapper.
- MCP is an open protocol — future LLM clients beyond Claude Code can
  integrate.

Tradeoffs:

- Claude Code becomes a hard dependency for the primary interactive flow.
  CLI/REST remain as fallbacks but lack AI reasoning.
- The `mcp` Python package is a new dependency (lightweight, pure Python).
- Tool granularity shifts from "run everything" to "call one thing" —
  requires rethinking how `StagedProfiler` is exposed (exposed as a single
  `run_profiler` tool, not per-phase).
- stdio transport means the MCP server runs as a subprocess of Claude Code
  — lifecycle management is external.

## Follow-Up

- Implement `Core/mcp/server.py` with 5 core tools (Phase 1 MVP).
- Add MCP server config to Claude Code's `mcp_servers.json`.
- Create `Core/mcp/tool_registry.py` for auto-discovery of plugin-to-tool
  mapping.
- Document tool schemas in `_bmad-output/planning-artifacts/mcp-tool-catalog.md`.
