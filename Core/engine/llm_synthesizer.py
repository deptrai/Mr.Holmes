"""
Core/engine/llm_synthesizer.py

Story 8.2 — LLM Synthesis Integration

Calls any OpenAI-compatible API endpoint to synthesize a ProfileGraph dict
(output from RecursiveProfiler) into a professional Markdown analyst report.

Configuration via environment variables:
    MH_LLM_BASE_URL : e.g. "https://api.openai.com/v1" or "http://localhost:11434/v1"
    MH_LLM_API_KEY  : API key (use "ollama" for local Ollama)
    MH_LLM_MODEL    : Model name e.g. "gpt-4o", "gemma3:latest"
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Output dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SynthesisResult:
    """
    AC2 — Structured output from LLMSynthesizer.synthesize().
    """
    is_success: bool
    report_markdown: str
    model_used: str
    error_message: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# System prompt template
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an elite Open Source Intelligence (OSINT) analyst with 20 years of experience.
You receive structured reconnaissance data in JSON format collected by an automated OSINT engine.
Your task is to synthesize this data into a professional intelligence report in Markdown format.

The report MUST contain these exact sections in order:
1. ## Executive Summary
2. ## Entities Discovered
3. ## Key Relationships
4. ## Risk Assessment
5. ## Recommended Next Steps

Be precise, evidence-based, and professional. If data is limited, say so clearly.
Do not fabricate information — only use what is present in the provided data."""


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class LLMSynthesizer:
    """
    Story 8.2 — Synthesizes a ProfileGraph dict into an AI-generated Markdown report
    using any OpenAI-compatible LLM API.

    Usage::

        synth = LLMSynthesizer()  # reads config from env vars
        result = await synth.synthesize(graph_dict)
        print(result.report_markdown)
    """

    _DEFAULT_TIMEOUT: int = 120  # seconds — LLMs can be slow

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else os.environ.get("MH_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("MH_LLM_API_KEY", "")
        self.model = model if model is not None else os.environ.get("MH_LLM_MODEL", "gpt-4o")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def synthesize(self, graph: dict[str, Any]) -> SynthesisResult:
        """
        Synthesize a ProfileGraph dict into a Markdown analyst report.

        Args:
            graph: dict as returned by RecursiveProfiler.run_profiler()
                   Keys: "nodes", "edges", "plugin_results"

        Returns:
            SynthesisResult — never raises; returns fallback on any error.
        """
        # AC4 — Graceful fallback when credentials are missing
        if not self.base_url or not self.api_key:
            fallback = self._build_fallback_report(graph, reason="LLM credentials not configured.")
            return SynthesisResult(
                is_success=False,
                report_markdown=fallback,
                model_used="",
                error_message="LLM credentials not configured (MH_LLM_BASE_URL / MH_LLM_API_KEY missing).",
            )

        user_prompt = self._build_user_prompt(graph)
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self._DEFAULT_TIMEOUT),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning("LLM API returned HTTP %d: %s", response.status, error_text[:200])
                        fallback = self._build_fallback_report(graph, reason=f"API HTTP {response.status}")
                        return SynthesisResult(
                            is_success=False,
                            report_markdown=fallback,
                            model_used=self.model,
                            error_message=f"LLM API HTTP {response.status}: {error_text[:200]}",
                        )

                    data = await response.json()
                    try:
                        content = data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError) as parse_err:
                        logger.warning("LLM API returned malformed JSON: %s", parse_err)
                        fallback = self._build_fallback_report(graph, reason=f"Malformed API response: {parse_err}")
                        return SynthesisResult(
                            is_success=False,
                            report_markdown=fallback,
                            model_used=self.model,
                            error_message=f"Malformed API response: {parse_err}",
                        )
                    model_used = data.get("model", self.model)

                    return SynthesisResult(
                        is_success=True,
                        report_markdown=content,
                        model_used=model_used,
                    )

        except aiohttp.ClientError as exc:
            logger.warning("LLM API network error: %s", exc)
            fallback = self._build_fallback_report(graph, reason=str(exc))
            return SynthesisResult(
                is_success=False,
                report_markdown=fallback,
                model_used=self.model,
                error_message=f"Network error: {exc}",
            )
        except Exception as exc:
            logger.warning("LLM synthesizer unexpected error: %s", exc)
            fallback = self._build_fallback_report(graph, reason=str(exc))
            return SynthesisResult(
                is_success=False,
                report_markdown=fallback,
                model_used=self.model,
                error_message=f"Unexpected error: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt construction (AC5 — testable independently)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_user_prompt(self, graph: dict[str, Any]) -> str:
        """
        Build a compact, information-dense prompt from the graph dict.
        Keeps token usage reasonable by summarizing rather than dumping raw JSON.
        """
        nodes: list[dict] = graph.get("nodes", [])
        edges: list[dict] = graph.get("edges", [])
        plugin_results: list[dict] = graph.get("plugin_results", [])

        # Node summary
        node_count = len(nodes)
        type_counts: dict[str, int] = {}
        for n in nodes:
            t = n.get("target_type", "UNKNOWN")
            type_counts[t] = type_counts.get(t, 0) + 1

        type_summary = ", ".join(f"{count} {t}" for t, count in sorted(type_counts.items()))

        # Plugin summary
        plugin_stats: dict[str, dict[str, int]] = {}
        for pr in plugin_results:
            name = pr.get("plugin", "Unknown")
            if name not in plugin_stats:
                plugin_stats[name] = {"success": 0, "failed": 0}
            if pr.get("is_success"):
                plugin_stats[name]["success"] += 1
            else:
                plugin_stats[name]["failed"] += 1

        plugin_lines = "\n".join(
            f"  - {name}: {s['success']} success, {s['failed']} failed"
            for name, s in sorted(plugin_stats.items())
        )

        # Discovered entities sample (first 20)
        entities_sample = "\n".join(
            f"  [{n['depth']}] {n.get('target_type','?')}: {n['target']}"
            for n in nodes[:20]
        )
        if node_count > 20:
            entities_sample += f"\n  ... and {node_count - 20} more entities"

        # Edge sample (first 15)
        edge_summary = ""
        if edges:
            edge_lines = "\n".join(
                f"  {e['source']} --[{e.get('via_plugin','?')}]--> {e['discovered']} ({e.get('type','?')})"
                for e in edges[:15]
            )
            if len(edges) > 15:
                edge_lines += f"\n  ... and {len(edges) - 15} more relationships"
            edge_summary = f"\n\nRelationships Found ({len(edges)} total):\n{edge_lines}"

        # Detailed plugin findings (data fields from successful results)
        findings_lines: list[str] = []
        for pr in plugin_results:
            if pr.get("is_success") and pr.get("data"):
                data = pr["data"]
                if data.get("data_found"):
                    findings_lines.append(
                        f"  - {pr['plugin']} found data for {pr['target']}: "
                        + json.dumps({k: v for k, v in data.items() if k != "data_found"}, ensure_ascii=False)[:300]
                    )
        findings_text = (
            "\n\nKey Findings from Plugins:\n" + "\n".join(findings_lines)
            if findings_lines else ""
        )

        prompt = f"""OSINT Reconnaissance Data:

Target Analysis Summary:
  Total Entities: {node_count} ({type_summary})
  Total Relationships: {len(edges)}
  Scan Depth: {max((n.get('depth') or 0 for n in nodes), default=0)} layers

Plugin Execution Results:
{plugin_lines or "  No plugins executed."}

Entities Discovered:
{entities_sample or "  None."}{edge_summary}{findings_text}

Please produce the professional OSINT intelligence report as instructed."""

        return prompt

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback report builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_fallback_report(self, graph: dict[str, Any], reason: str = "") -> str:
        """
        AC4 — Generate a minimal plaintext summary when LLM is unavailable.
        Ensures report_markdown is never empty even on failure.
        """
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        plugin_results = graph.get("plugin_results", [])
        success_count = sum(1 for pr in plugin_results if pr.get("is_success"))

        lines = [
            "# OSINT Profile Report (Fallback — LLM Unavailable)",
            "",
            f"> **Note:** LLM synthesis was unavailable. Reason: {reason or 'Unknown'}",
            f"> This is a raw data summary generated without AI analysis.",
            "",
            "## Executive Summary",
            f"Automated OSINT scan completed. {len(nodes)} entities discovered across "
            f"{max((n.get('depth', 0) for n in nodes), default=0)} depth layers. "
            f"{success_count}/{len(plugin_results)} plugin queries succeeded.",
            "",
            "## Entities Discovered",
        ]
        for n in nodes[:30]:
            lines.append(f"- [{n.get('depth', '?')}] **{n.get('target_type', '?')}**: `{n.get('target', '?')}`")
        if len(nodes) > 30:
            lines.append(f"- ... and {len(nodes) - 30} more entities")

        lines += [
            "",
            "## Key Relationships",
        ]
        if edges:
            for e in edges[:20]:
                lines.append(
                    f"- `{e.get('source')}` → `{e.get('discovered')}` (via **{e.get('via_plugin', '?')}**)"
                )
        else:
            lines.append("- No cross-entity relationships discovered.")

        lines += [
            "",
            "## Risk Assessment",
            "_LLM analysis unavailable. Manual review of entities and plugin data recommended._",
            "",
            "## Recommended Next Steps",
            "1. Configure LLM credentials (`MH_LLM_BASE_URL`, `MH_LLM_API_KEY`, `MH_LLM_MODEL`) for AI-powered analysis.",
            "2. Review raw plugin results in the JSON output.",
            "3. Re-run the profiler with increased depth if needed.",
        ]

        return "\n".join(lines)
