"""
Core/engine/mindmap_generator.py

Story 8.3 — Interactive Mindmap Generation

Converts a ProfileGraph dictionary (output of RecursiveProfiler.run_profiler())
into a standalone, self-contained interactive HTML file using vis-network (Vis.js).

The generated HTML:
  - Embeds ALL graph data inline as JavaScript (fully portable — no external JSON needed)
  - Renders nodes with distinct colors/shapes per target_type and depth
  - Labels edges with the plugin name that discovered the relationship
  - Loads vis-network via CDN (internet connection required to VIEW the map)

Usage::

    from Core.engine.mindmap_generator import MindmapGenerator

    gen = MindmapGenerator()
    html_content = gen.generate(graph_dict)
    with open("mindmap.html", "w", encoding="utf-8") as f:
        f.write(html_content)
"""
from __future__ import annotations

import html as _html_module
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Visual config: node appearance per target_type and depth
# ─────────────────────────────────────────────────────────────────────────────

_TYPE_COLORS: dict[str, str] = {
    "EMAIL":    "#e74c3c",   # Red
    "USERNAME": "#9b59b6",   # Purple
    "IP":       "#2980b9",   # Blue
    "DOMAIN":   "#27ae60",   # Green
    "PHONE":    "#f39c12",   # Orange
    "URL":      "#1abc9c",   # Teal
}
_DEPTH_COLORS: list[str] = [
    "#c0392b",  # depth 0 — Seed (crimson)
    "#e67e22",  # depth 1 — orange
    "#f1c40f",  # depth 2 — yellow
    "#2ecc71",  # depth 3 — green
    "#3498db",  # depth 4+ — blue
]
_TYPE_SHAPES: dict[str, str] = {
    "EMAIL":    "star",
    "USERNAME": "ellipse",
    "IP":       "diamond",
    "DOMAIN":   "box",
    "PHONE":    "triangle",
    "URL":      "dot",
}

# ─────────────────────────────────────────────────────────────────────────────
# HTML template — uses NODES_JSON__PLACEHOLDER, EDGES_JSON__PLACEHOLDER,
# TITLE__PLACEHOLDER, GENERATED_AT__PLACEHOLDER
# Using string replacement (not .format()) to avoid crashes when node data
# contains curly braces (F6 fix).
# ─────────────────────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mr.Holmes OSINT Mindmap — TITLE__PLACEHOLDER</title>
  <script type="text/javascript"
    src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js">
  </script>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body {
      margin: 0; padding: 0;
      background: #0d1117;
      color: #c9d1d9;
      font-family: 'Segoe UI', Arial, sans-serif;
    }
    #header {
      padding: 14px 20px;
      background: linear-gradient(135deg, #161b22 0%, #21262d 100%);
      border-bottom: 1px solid #30363d;
      display: flex; align-items: center; gap: 10px;
    }
    #header h1 {
      margin: 0; font-size: 1.1rem; font-weight: 600;
      color: #f0883e;
      flex: 1;
    }
    #header span {
      font-size: 0.75rem; color: #8b949e;
    }
    #controls {
      padding: 8px 20px;
      background: #161b22;
      border-bottom: 1px solid #30363d;
      display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
    }
    #controls button {
      background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
      padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
      transition: background 0.2s;
    }
    #controls button:hover { background: #30363d; }
    #legend {
      display: flex; gap: 12px; flex-wrap: wrap; margin-left: auto;
    }
    #legend .litem {
      display: flex; align-items: center; gap: 5px;
      font-size: 0.72rem; color: #8b949e;
    }
    #legend .dot {
      width: 10px; height: 10px; border-radius: 50%;
      display: inline-block; flex-shrink: 0;
    }
    #network-container {
      width: 100%; height: calc(100vh - 100px);
    }
    #stats {
      position: fixed; bottom: 10px; right: 14px;
      background: rgba(22,27,34,0.9);
      border: 1px solid #30363d; border-radius: 8px;
      padding: 8px 14px; font-size: 0.75rem; color: #8b949e;
      backdrop-filter: blur(4px);
    }
  </style>
</head>
<body>
  <div id="header">
    <h1>🔍 Mr.Holmes OSINT Mindmap — TITLE__PLACEHOLDER</h1>
    <span>Được tạo lúc: GENERATED_AT__PLACEHOLDER</span>
  </div>

  <div id="controls">
    <button onclick="network.fit()">⛶ Fit tất cả</button>
    <button onclick="network.setOptions({physics:{enabled:true}})">▶ Bật Physics</button>
    <button onclick="network.setOptions({physics:{enabled:false}})">⏸ Tắt Physics</button>
    <div id="legend">
      <div class="litem"><span class="dot" style="background:#c0392b"></span>Seed (Depth 0)</div>
      <div class="litem"><span class="dot" style="background:#e67e22"></span>Depth 1</div>
      <div class="litem"><span class="dot" style="background:#f1c40f"></span>Depth 2</div>
      <div class="litem"><span class="dot" style="background:#e74c3c"></span>EMAIL</div>
      <div class="litem"><span class="dot" style="background:#9b59b6"></span>USERNAME</div>
      <div class="litem"><span class="dot" style="background:#2980b9"></span>IP</div>
      <div class="litem"><span class="dot" style="background:#27ae60"></span>DOMAIN</div>
    </div>
  </div>

  <div id="network-container"></div>
  <div id="stats">
    Nodes: <b id="node-count">0</b> | Edges: <b id="edge-count">0</b>
  </div>

  <script type="text/javascript">
    // ── embedded graph data (generated by Mr.Holmes) ──────────────────────────
    var RAW_NODES = NODES_JSON__PLACEHOLDER;
    var RAW_EDGES = EDGES_JSON__PLACEHOLDER;

    // ── build vis DataSets ────────────────────────────────────────────────────
    var nodes = new vis.DataSet(RAW_NODES);
    var edges = new vis.DataSet(RAW_EDGES);

    document.getElementById("node-count").textContent = RAW_NODES.length;
    document.getElementById("edge-count").textContent = RAW_EDGES.length;

    // ── network options ───────────────────────────────────────────────────────
    var options = {
      nodes: {
        borderWidth: 2,
        shadow: true,
        font: { color: "#f0f6fc", size: 13, face: "Segoe UI, Arial" },
        chosen: {
          node: function(values, id, selected) {
            values.size = values.size * 1.2;
          }
        }
      },
      edges: {
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        color: { color: "#30363d", highlight: "#f0883e", hover: "#58a6ff" },
        font: { color: "#8b949e", size: 10, align: "middle" },
        smooth: { type: "dynamic" },
        shadow: true,
      },
      physics: {
        enabled: true,
        stabilization: { iterations: 150 },
        barnesHut: {
          gravitationalConstant: -8000,
          springLength: 140,
          springConstant: 0.04,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        navigationButtons: false,
        keyboard: true,
      },
      layout: { randomSeed: 42 },
    };

    var container = document.getElementById("network-container");
    var network = new vis.Network(container, { nodes: nodes, edges: edges }, options);

    // Tắt physics sau khi ổn định để tránh giật
    network.on("stabilizationIterationsDone", function () {
      network.setOptions({ physics: { enabled: false } });
    });

    // Tooltip khi hover node
    network.on("hoverNode", function (params) {
      var node = nodes.get(params.node);
      container.title = node.title || node.label;
    });
  </script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class MindmapGenerator:
    """
    Story 8.3 — Converts a ProfileGraph dict into a self-contained interactive
    HTML mindmap using vis-network.

    Accepts the same ``graph_dict`` format produced by
    ``RecursiveProfiler.run_profiler()``:

    .. code-block:: python

        {
            "nodes": [{"target": str, "target_type": str, "depth": int}, ...],
            "edges": [{"source": str, "discovered": str,
                       "type": str, "via_plugin": str}, ...],
            "plugin_results": [...],   # not used for rendering
        }

    Usage::

        gen = MindmapGenerator()
        html = gen.generate(graph_dict)
        Path("mindmap.html").write_text(html, encoding="utf-8")
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, graph_dict: dict[str, Any]) -> str:
        """
        Convert *graph_dict* into a self-contained HTML string.

        AC3 — All data is embedded inline; no external JSON files needed.
        AC6 — Empty graphs are handled gracefully (renders empty canvas).

        Security notes:
          - title is HTML-escaped to prevent XSS (F1).
          - JSON data uses ensure_ascii-False dumps; script block is safe because
            json.dumps escapes / as \\/ when the string starts a </script> tag.
          - Template uses string .replace() not .format() so curly braces in data
            never crash the renderer (F6).
        """
        nodes_json = self._build_vis_nodes(graph_dict.get("nodes", []))
        edges_json = self._build_vis_edges(graph_dict.get("edges", []))

        # Title = first seed node's target or generic fallback
        raw_nodes = graph_dict.get("nodes", [])
        seed_nodes = [n for n in raw_nodes if n.get("depth", 1) == 0]
        raw_title = seed_nodes[0]["target"] if seed_nodes else "OSINT Report"

        # F1 fix: escape HTML special chars in title to prevent XSS
        title = _html_module.escape(raw_title)

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # F2 + F6 fix: use string .replace() instead of .format() so that:
        # - curly braces in node data don't crash
        # - we control exactly where JSON is injected
        # json.dumps with ensure_ascii=False is safe inside <script>; the only
        # dangerous sequence is </script> which json.dumps escapes as <\/script>
        nodes_json_str = json.dumps(nodes_json, ensure_ascii=False).replace(
            "</", r"<\/"  # belt-and-suspenders: prevent </script> breakout
        )
        edges_json_str = json.dumps(edges_json, ensure_ascii=False).replace(
            "</", r"<\/"
        )

        html = (
            _HTML_TEMPLATE
            .replace("NODES_JSON__PLACEHOLDER", nodes_json_str)
            .replace("EDGES_JSON__PLACEHOLDER", edges_json_str)
            .replace("TITLE__PLACEHOLDER", title)
            .replace("GENERATED_AT__PLACEHOLDER", generated_at)
        )
        logger.info(
            "MindmapGenerator: generated HTML with %d nodes, %d edges",
            len(nodes_json),
            len(edges_json),
        )
        return html

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _node_color(self, target_type: str, depth: int) -> str:
        """
        AC4 — Return a hex color based on target_type first, then depth fallback.
        Depth-0 (seed) always gets the crimson highlight regardless of type.
        """
        if depth == 0:
            return _DEPTH_COLORS[0]
        return _TYPE_COLORS.get(target_type.upper(), _DEPTH_COLORS[min(depth, len(_DEPTH_COLORS) - 1)])

    def _node_shape(self, target_type: str, depth: int) -> str:
        """AC4 — Return a vis-network shape string based on target_type."""
        if depth == 0:
            return "star"
        return _TYPE_SHAPES.get(target_type.upper(), "ellipse")

    def _node_size(self, depth: int) -> int:
        """Seed nodes are larger; deeper nodes get progressively smaller."""
        return max(12, 30 - depth * 6)

    def _build_vis_nodes(self, raw_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        AC3, AC4 — Convert ProfileNode dicts → vis-network node objects.
        """
        vis_nodes: list[dict[str, Any]] = []
        seen: set[str] = set()

        for node in raw_nodes:
            target = node.get("target", "")

            # F7 fix: skip nodes with empty target — they would create orphan
            # empty-label nodes in the vis.js graph
            if not target:
                continue

            target_type = node.get("target_type", "UNKNOWN").upper()

            # F8 fix: guard against non-numeric depth values gracefully
            try:
                depth = int(node.get("depth", 0))
            except (TypeError, ValueError):
                logger.warning("MindmapGenerator: invalid depth %r for %r, defaulting to 0", node.get("depth"), target)
                depth = 0

            if target in seen:
                continue
            seen.add(target)

            color = self._node_color(target_type, depth)
            shape = self._node_shape(target_type, depth)
            size = self._node_size(depth)

            label = target if len(target) <= 40 else target[:37] + "…"

            vis_nodes.append({
                "id": target,
                "label": label,
                "title": f"{target_type}: {target} (depth {depth})",
                "color": {
                    "background": color,
                    "border": "#ffffff",
                    "highlight": {"background": color, "border": "#f0883e"},
                    "hover":     {"background": color, "border": "#58a6ff"},
                },
                "shape": shape,
                "size": size,
                "font": {
                    "color": "#ffffff",
                    "size": 13 if depth == 0 else 11,
                    # F5 fix: vis-network uses face="bold" not bold:True
                    "face": "bold" if depth == 0 else "Segoe UI, Arial",
                },
            })

        return vis_nodes

    def _build_vis_edges(self, raw_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        AC5 — Convert ProfileEdge dicts → vis-network edge objects.
        Edge label shows the plugin that discovered the link.
        """
        vis_edges: list[dict[str, Any]] = []

        for i, edge in enumerate(raw_edges):
            source = edge.get("source", "")
            target = edge.get("discovered", "")
            plugin = edge.get("via_plugin", "unknown")

            if not source or not target:
                continue

            vis_edges.append({
                "id": i,
                "from": source,
                "to": target,
                "label": plugin,
                "title": f"Discovered by: {plugin}",
                "dashes": False,
                "width": 1.5,
            })

        return vis_edges
