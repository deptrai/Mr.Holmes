"""
Core/engine/autonomous_agent.py

Story 8.1 — Recursive Profiling Engine (Autonomous OSINT Agent)

Implements a Breadth-First-Search (BFS) driven engine that:
- Accepts a seed target + type and a max_depth limit
- Iteratively calls all registered IntelligencePlugins per layer
- Extracts new clues (emails, IPs, usernames) from plugin results
- Adds discovered clues to the next scan layer while deduplicating
- Returns a structured graph (nodes + edges + raw plugin_results)
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from Core.plugins.base import IntelligencePlugin, PluginResult
from Core.engine.stage_router import StageRouter

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns used to extract new clues from plugin result payloads
# ─────────────────────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
_IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)



@dataclass
class ProfileNode:
    """One entity (target+type) discovered during profiling."""
    target: str
    target_type: str
    depth: int


@dataclass
class ProfileEdge:
    """A directed link: source node discovered target_node via plugin."""
    source_target: str
    discovered_target: str
    discovered_type: str
    via_plugin: str


@dataclass
class ProfileGraph:
    """
    Final output of RecursiveProfiler.run_profiler().
    Contains:
      - nodes: all entities discovered/scanned
      - edges: provenance links between entities
      - plugin_results: raw PluginResult objects keyed by (target, plugin_name)
    """
    nodes: list[ProfileNode] = field(default_factory=list)
    edges: list[ProfileEdge] = field(default_factory=list)
    plugin_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"target": n.target, "target_type": n.target_type, "depth": n.depth}
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": e.source_target,
                    "discovered": e.discovered_target,
                    "type": e.discovered_type,
                    "via_plugin": e.via_plugin,
                }
                for e in self.edges
            ],
            "plugin_results": self.plugin_results,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Clue extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

_MAX_CLUES_PER_RESULT = 15  # Prevent BFS explosion from noisy breach databases


def _extract_clues_from_result(result: PluginResult) -> list[tuple[str, str]]:
    """
    Parse a PluginResult.data dict and extract new (target, type) clues.

    Looks for:
    - data["emails"]: list[str]       → ("value", "EMAIL")
    - data["hostnames"]: list[str]    → ("value", "DOMAIN")
    - data["osint_urls"]: list[str]   → scan for embedded emails/IPs
    - Any string value in data        → regex scan for emails and IPs
    Returns: deduplicated list of (value, type) tuples, capped at _MAX_CLUES_PER_RESULT.
    """
    clues: list[tuple[str, str]] = []

    if not result.is_success or not result.data:
        return clues

    data = result.data

    # Explicit email list from plugins (e.g. LeakLookup)
    for email in data.get("emails", []):
        if isinstance(email, str) and email.strip():
            clues.append((email.strip().lower(), "EMAIL"))

    # Explicit hostname list from Shodan
    for hostname in data.get("hostnames", []):
        if isinstance(hostname, str) and hostname.strip():
            clues.append((hostname.strip().lower(), "DOMAIN"))

    # Scan raw string values for emails and IPs via regex
    def _scan_string(s: str) -> None:
        for email in _EMAIL_RE.findall(s):
            clues.append((email.lower(), "EMAIL"))
        for ip in _IP_RE.findall(s):
            clues.append((ip, "IP"))

    def _scan_value(v: Any) -> None:
        if isinstance(v, str):
            _scan_string(v)
        elif isinstance(v, list):
            for item in v:
                _scan_value(item)
        elif isinstance(v, dict):
            for sub_v in v.values():
                _scan_value(sub_v)

    for key, value in data.items():
        _scan_value(value)

    # Deduplicate while preserving first-seen order, cap at limit
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for clue in clues:
        if clue not in seen:
            seen.add(clue)
            deduped.append(clue)
            if len(deduped) >= _MAX_CLUES_PER_RESULT:
                break

    return deduped


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class RecursiveProfiler:
    """
    Story 8.1 — BFS Recursive Profiler Engine.

    Usage::

        agent = RecursiveProfiler(max_depth=2)
        result = await agent.run_profiler(
            seed_target="admin@facebook.com",
            seed_type="EMAIL",
            plugins=[hibp_plugin, leak_lookup_plugin, shodan_plugin, searxng_plugin],
        )
        # result is a dict with "nodes", "edges", "plugin_results"

    Depth semantics:
      - depth=0  : the seed target itself
      - depth=1  : clues discovered FROM scanning the seed
      - depth=N  : clues discovered at Nth recursive layer

    max_depth controls the LAST layer that is actively scanned.
    Clues found at depth max_depth are recorded but NOT scanned again.
    """

    # Max concurrent plugin calls per node to throttle pressure on APIs
    _SEMAPHORE_LIMIT: int = 5

    def __init__(self, max_depth: int = 2) -> None:
        if max_depth < 0:
            raise ValueError(f"max_depth must be >= 0, got {max_depth}")
        self.max_depth = max_depth

    async def run_profiler(
        self,
        seed_target: str,
        seed_type: str,
        plugins: list[IntelligencePlugin] | None = None,
    ) -> dict[str, Any]:
        """
        Entry point for the profiling engine.

        Args:
            seed_target: Starting piece of intelligence (email, IP, domain…).
            seed_type:   Category of the seed — "EMAIL", "IP", "DOMAIN", "USERNAME".
            plugins:     List of IntelligencePlugin instances to use.
                         If None or empty, an empty graph is returned.

        Returns:
            dict with keys: "nodes", "edges", "plugin_results"
        """
        plugins = plugins or []
        graph = ProfileGraph()
        # Visited set: (target, type) to prevent re-scanning
        visited: set[tuple[str, str]] = set()

        # BFS layers — each layer is a list of (target, type, depth) tuples
        current_layer: list[tuple[str, str, int]] = [
            (seed_target, seed_type, 0)
        ]

        semaphore = asyncio.Semaphore(self._SEMAPHORE_LIMIT)

        while current_layer:
            next_layer: list[tuple[str, str, int]] = []

            for target, t_type, depth in current_layer:
                key = (target.lower(), t_type.upper())
                if key in visited:
                    continue
                visited.add(key)

                # Record this node in the graph
                node = ProfileNode(target=target, target_type=t_type, depth=depth)
                graph.nodes.append(node)

                # Stop scanning if we are beyond max_depth
                if depth >= self.max_depth:
                    continue

                # Auto-derive USERNAME from EMAIL prefix (e.g. "user@gmail.com" → "user")
                if t_type.upper() == "EMAIL" and "@" in target:
                    prefix = target.split("@")[0].lower()
                    domain_part = target.split("@")[1].lower()
                    if len(prefix) >= 3:
                        prefix_key = (prefix, "USERNAME")
                        if prefix_key not in visited:
                            next_layer.append((prefix, "USERNAME", depth + 1))
                            graph.edges.append(ProfileEdge(
                                source_target=target,
                                discovered_target=prefix,
                                discovered_type="USERNAME",
                                via_plugin="auto:email-prefix",
                            ))
                    # Also derive DOMAIN for non-freemail providers
                    _FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                                 "protonmail.com", "icloud.com", "aol.com", "mail.com",
                                 "yandex.com", "zoho.com", "gmx.com", "live.com"}
                    if domain_part not in _FREEMAIL:
                        domain_key = (domain_part, "DOMAIN")
                        if domain_key not in visited:
                            next_layer.append((domain_part, "DOMAIN", depth + 1))
                            graph.edges.append(ProfileEdge(
                                source_target=target,
                                discovered_target=domain_part,
                                discovered_type="DOMAIN",
                                via_plugin="auto:email-domain",
                            ))

                # Run all plugins concurrently for this target
                tasks = [
                    self._safe_plugin_run(plugin, target, t_type, semaphore)
                    for plugin in plugins
                ]
                results: list[PluginResult] = list(await asyncio.gather(*tasks))

                for result in results:
                    # Store raw result
                    graph.plugin_results.append({
                        "target": target,
                        "target_type": t_type,
                        "plugin": result.plugin_name,
                        "is_success": result.is_success,
                        "data": result.data,
                        "error": result.error_message,
                        "stage": 1,
                    })

                    # Extract new clues and add to next layer
                    clues = _extract_clues_from_result(result)
                    for clue_target, clue_type in clues:
                        clue_key = (clue_target.lower(), clue_type.upper())
                        if clue_key not in visited:
                            next_layer.append((clue_target, clue_type, depth + 1))
                            graph.edges.append(ProfileEdge(
                                source_target=target,
                                discovered_target=clue_target,
                                discovered_type=clue_type,
                                via_plugin=result.plugin_name,
                            ))

            current_layer = next_layer

        return graph.to_dict()

    async def _safe_plugin_run(
        self,
        plugin: IntelligencePlugin,
        target: str,
        target_type: str,
        semaphore: asyncio.Semaphore,
    ) -> PluginResult:
        return await _safe_plugin_run(plugin, target, target_type, semaphore)


async def _safe_plugin_run(
    plugin: IntelligencePlugin,
    target: str,
    target_type: str,
    semaphore: asyncio.Semaphore,
) -> PluginResult:
    """
    Execute a single plugin with semaphore throttling and exception safety.
    Never raises — returns a failure PluginResult on any exception.
    """
    async with semaphore:
        try:
            return await plugin.check(target, target_type)
        except Exception as exc:
            try:
                name = plugin.name
            except Exception:
                name = "unknown"
            logger.warning("Plugin %s raised exception for %s: %s", name, target, exc)
            return PluginResult(
                plugin_name=name,
                is_success=False,
                data={},
                error_message=f"Plugin Exception: {exc}",
            )


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.2 — StagedProfiler (multi-stage BFS for Epic 9)
# ─────────────────────────────────────────────────────────────────────────────

class StagedProfiler:
    """
    Story 9.2 — Multi-Stage BFS Orchestration Engine.

    4-phase pipeline:
      Phase A — Stage 2 (identity expansion: Holehe, Maigret, GitHub)
      Phase B — Clue extraction from Stage 2 results
      Phase C — Stage 3 (deep enrichment: Numverify, Hunter on discovered PHONE/DOMAIN)
      Phase D — Stage 1 fallback (Epic 8 plugins via RecursiveProfiler)

    Backward compatible: if all plugins are stage-1, delegates entirely to
    RecursiveProfiler.run_profiler() preserving Epic 8 behavior.
    """

    _SEMAPHORE_LIMIT: int = 5

    def __init__(self, max_depth: int = 2) -> None:
        if max_depth < 0:
            raise ValueError(f"max_depth must be >= 0, got {max_depth}")
        self.max_depth = max_depth
        self._router = StageRouter()

    async def run_staged(
        self,
        seed_target: str,
        seed_type: str,
        plugins: list[IntelligencePlugin] | None = None,
    ) -> dict[str, Any]:
        """
        Run the multi-stage enrichment pipeline.

        Args:
            seed_target: Starting piece of intelligence.
            seed_type:   "EMAIL" | "USERNAME" | "PHONE" | "DOMAIN" | "IP"
            plugins:     List of IntelligencePlugin instances.

        Returns:
            dict with keys: "nodes", "edges", "plugin_results"  (same schema as Epic 8)
        """
        plugins = plugins or []

        # Detect staged plugins
        has_staged = any(getattr(p, "stage", 1) >= 2 for p in plugins)
        if not has_staged:
            # Pure Epic 8 path — delegate entirely to RecursiveProfiler
            flat = RecursiveProfiler(max_depth=self.max_depth)
            return await flat.run_profiler(seed_target, seed_type, plugins)

        graph = ProfileGraph()
        visited: set[tuple[str, str]] = set()
        semaphore = asyncio.Semaphore(self._SEMAPHORE_LIMIT)

        # Record seed node
        seed_key = (seed_target.lower(), seed_type.upper())
        visited.add(seed_key)
        graph.nodes.append(ProfileNode(
            target=seed_target, target_type=seed_type, depth=0
        ))

        # ── Phase A: Stage 2 plugins on seed (if seed_type routes to stage 2) ───
        stage2_plugins = self._router.filter_plugins(plugins, stage=2)
        stage2_results: list[PluginResult] = []

        if stage2_plugins and self._router.route(seed_type) == 2:
            tasks = [
                self._safe_plugin_run(p, seed_target, seed_type, semaphore)
                for p in stage2_plugins
            ]
            stage2_results = list(await asyncio.gather(*tasks))
            for result in stage2_results:
                graph.plugin_results.append({
                    "target": seed_target,
                    "target_type": seed_type,
                    "plugin": result.plugin_name,
                    "is_success": result.is_success,
                    "data": result.data,
                    "error": result.error_message,
                    "stage": 2,
                })

        # ── Phase B: Extract stage-3 targets from stage-2 results ───────────────
        stage3_targets: list[tuple[str, str]] = []  # (target, type) for stage 3

        def _add_clue(clue_target: str, clue_type: str, via_plugin: str) -> None:
            clue_key = (clue_target.lower(), clue_type.upper())
            if self._router.route(clue_type) == 3 and clue_key not in visited:
                visited.add(clue_key)
                stage3_targets.append((clue_target, clue_type))
                graph.nodes.append(ProfileNode(
                    target=clue_target, target_type=clue_type, depth=1
                ))
                graph.edges.append(ProfileEdge(
                    source_target=seed_target,
                    discovered_target=clue_target,
                    discovered_type=clue_type,
                    via_plugin=via_plugin,
                ))

        for i, result in enumerate(stage2_results):
            # Generic clue extraction (Epic 8 — EMAIL/DOMAIN/IP via regex)
            for clue_target, clue_type in _extract_clues_from_result(result):
                _add_clue(clue_target, clue_type, result.plugin_name)

            # Plugin-specific clue extraction (Epic 9 — PHONE, profile emails)
            plugin = stage2_plugins[i] if i < len(stage2_plugins) else None
            if plugin is not None and hasattr(plugin, "extract_clues"):
                try:
                    for clue_target, clue_type in plugin.extract_clues(result):
                        _add_clue(clue_target, clue_type, result.plugin_name)
                except Exception as exc:
                    logger.warning("extract_clues failed for %s: %s",
                                   result.plugin_name, exc)

        # ── Phase C: Stage 3 plugins on discovered PHONE/DOMAIN clues ────────────
        stage3_plugins = self._router.filter_plugins(plugins, stage=3)
        if stage3_plugins and stage3_targets:
            for clue_target, clue_type in stage3_targets:
                tasks = [
                    self._safe_plugin_run(p, clue_target, clue_type, semaphore)
                    for p in stage3_plugins
                ]
                results = list(await asyncio.gather(*tasks))
                for result in results:
                    graph.plugin_results.append({
                        "target": clue_target,
                        "target_type": clue_type,
                        "plugin": result.plugin_name,
                        "is_success": result.is_success,
                        "data": result.data,
                        "error": result.error_message,
                        "stage": 3,
                    })

        # ── Phase D: Stage 1 (Epic 8) plugins via RecursiveProfiler ─────────────
        stage1_plugins = self._router.filter_plugins(plugins, stage=1)
        if stage1_plugins:
            flat = RecursiveProfiler(max_depth=self.max_depth)
            flat_result = await flat.run_profiler(seed_target, seed_type, stage1_plugins)
            # Merge flat result — add nodes/edges/results not already in graph
            existing_node_keys = {
                (n.target.lower(), n.target_type.upper()) for n in graph.nodes
            }
            for node_dict in flat_result.get("nodes", []):
                key = (node_dict["target"].lower(), node_dict["target_type"].upper())
                if key not in existing_node_keys:
                    existing_node_keys.add(key)
                    graph.nodes.append(ProfileNode(
                        target=node_dict["target"],
                        target_type=node_dict["target_type"],
                        depth=node_dict["depth"],
                    ))
            for edge_dict in flat_result.get("edges", []):
                graph.edges.append(ProfileEdge(
                    source_target=edge_dict["source"],
                    discovered_target=edge_dict["discovered"],
                    discovered_type=edge_dict["type"],
                    via_plugin=edge_dict["via_plugin"],
                ))
            graph.plugin_results.extend(flat_result.get("plugin_results", []))

        return graph.to_dict()

    async def _safe_plugin_run(
        self,
        plugin: IntelligencePlugin,
        target: str,
        target_type: str,
        semaphore: asyncio.Semaphore,
    ) -> PluginResult:
        return await _safe_plugin_run(plugin, target, target_type, semaphore)
