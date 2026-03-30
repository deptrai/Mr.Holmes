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

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns used to extract new clues from plugin result payloads
# ─────────────────────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
_IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
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

def _extract_clues_from_result(result: PluginResult) -> list[tuple[str, str]]:
    """
    Parse a PluginResult.data dict and extract new (target, type) clues.

    Looks for:
    - data["emails"]: list[str]       → ("value", "EMAIL")
    - data["hostnames"]: list[str]    → ("value", "DOMAIN")
    - data["osint_urls"]: list[str]   → scan for embedded emails/IPs
    - Any string value in data        → regex scan for emails and IPs
    Returns: deduplicated list of (value, type) tuples.
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

    for key, value in data.items():
        if isinstance(value, str):
            _scan_string(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    _scan_string(item)

    # Deduplicate while preserving first-seen order
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for clue in clues:
        if clue not in seen:
            seen.add(clue)
            deduped.append(clue)

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
        if max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {max_depth}")
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
