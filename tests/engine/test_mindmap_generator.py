"""
tests/engine/test_mindmap_generator.py

Story 8.3 — Unit tests for MindmapGenerator

Covers:
  - AC1: MindmapGenerator class exists at correct path
  - AC2: generate() returns a non-empty HTML string
  - AC3: HTML is self-contained (no src= pointing to local files)
  - AC4: Node colors/shapes differ by target_type and depth
  - AC5: Edge labels contain plugin name
  - AC6: Empty graph handled gracefully
"""
from __future__ import annotations

import json
import re

import pytest

from Core.engine.mindmap_generator import MindmapGenerator


# ─────────────────────────────────────────────────────────────────────────────
# Sample fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def empty_graph() -> dict:
    return {"nodes": [], "edges": [], "plugin_results": []}


@pytest.fixture
def simple_graph() -> dict:
    return {
        "nodes": [
            {"target": "admin@example.com", "target_type": "EMAIL", "depth": 0},
            {"target": "192.168.1.1",        "target_type": "IP",    "depth": 1},
            {"target": "example.com",         "target_type": "DOMAIN","depth": 1},
        ],
        "edges": [
            {
                "source": "admin@example.com",
                "discovered": "192.168.1.1",
                "type": "IP",
                "via_plugin": "Shodan",
            },
            {
                "source": "admin@example.com",
                "discovered": "example.com",
                "type": "DOMAIN",
                "via_plugin": "SearxngOSINT",
            },
        ],
        "plugin_results": [],
    }


@pytest.fixture
def multi_depth_graph() -> dict:
    return {
        "nodes": [
            {"target": "seed@test.com", "target_type": "EMAIL",    "depth": 0},
            {"target": "user123",       "target_type": "USERNAME",  "depth": 1},
            {"target": "1.2.3.4",       "target_type": "IP",        "depth": 2},
            {"target": "+84900000000",  "target_type": "PHONE",     "depth": 3},
        ],
        "edges": [
            {"source": "seed@test.com", "discovered": "user123",     "type": "USERNAME", "via_plugin": "LeakLookup"},
            {"source": "user123",       "discovered": "1.2.3.4",     "type": "IP",       "via_plugin": "Shodan"},
            {"source": "1.2.3.4",       "discovered": "+84900000000","type": "PHONE",    "via_plugin": "SearxngOSINT"},
        ],
        "plugin_results": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# AC1 — Class instantiation
# ─────────────────────────────────────────────────────────────────────────────

class TestMindmapGeneratorInit:
    def test_instantiation(self):
        gen = MindmapGenerator()
        assert gen is not None

    def test_has_generate_method(self):
        gen = MindmapGenerator()
        assert callable(gen.generate)


# ─────────────────────────────────────────────────────────────────────────────
# AC2 — generate() returns a valid HTML string
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateOutput:
    def test_returns_str(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert isinstance(html, str)

    def test_html_not_empty(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert len(html) > 500

    def test_html_doctype(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_html_contains_vis_network_cdn(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert "vis-network" in html

    def test_html_contains_network_container(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert "network-container" in html

    def test_title_shows_seed_target(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert "admin@example.com" in html


# ─────────────────────────────────────────────────────────────────────────────
# AC3 — HTML is self-contained (data embedded inline)
# ─────────────────────────────────────────────────────────────────────────────

class TestSelfContained:
    def test_no_external_local_json_src(self, simple_graph):
        """Must NOT load JSON from local filesystem."""
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        # Should not have src="*.json" or fetch("*.json")
        assert not re.search(r'src=["\'][^"\']*\.json["\']', html)
        assert not re.search(r'fetch\(["\'][^"\']*\.json["\']', html)

    def test_vis_dataset_initialized_inline(self, simple_graph):
        """vis.DataSet(...) should appear in html, meaning data is embedded."""
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert "vis.DataSet" in html

    def test_node_data_embedded(self, simple_graph):
        """Node target appears inside inline JSON block."""
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert "admin@example.com" in html
        assert "192.168.1.1" in html

    def test_edge_data_embedded(self, simple_graph):
        gen = MindmapGenerator()
        html = gen.generate(simple_graph)
        assert "Shodan" in html
        assert "SearxngOSINT" in html


# ─────────────────────────────────────────────────────────────────────────────
# AC4 — Node visuals vary by type and depth
# ─────────────────────────────────────────────────────────────────────────────

class TestNodeVisuals:
    def test_seed_node_is_star_shape(self, simple_graph):
        gen = MindmapGenerator()
        vis_nodes = gen._build_vis_nodes(simple_graph["nodes"])
        seed = next(n for n in vis_nodes if n["id"] == "admin@example.com")
        assert seed["shape"] == "star"

    def test_ip_node_is_diamond(self, simple_graph):
        gen = MindmapGenerator()
        vis_nodes = gen._build_vis_nodes(simple_graph["nodes"])
        ip_node = next(n for n in vis_nodes if n["id"] == "192.168.1.1")
        assert ip_node["shape"] == "diamond"

    def test_domain_node_is_box(self, simple_graph):
        gen = MindmapGenerator()
        vis_nodes = gen._build_vis_nodes(simple_graph["nodes"])
        domain_node = next(n for n in vis_nodes if n["id"] == "example.com")
        assert domain_node["shape"] == "box"

    def test_seed_color_is_crimson(self, simple_graph):
        gen = MindmapGenerator()
        vis_nodes = gen._build_vis_nodes(simple_graph["nodes"])
        seed = next(n for n in vis_nodes if n["id"] == "admin@example.com")
        # depth 0 always crimson regardless of type
        assert seed["color"]["background"] == "#c0392b"

    def test_deeper_nodes_have_different_color_than_seed(self, multi_depth_graph):
        gen = MindmapGenerator()
        vis_nodes = gen._build_vis_nodes(multi_depth_graph["nodes"])
        seed = next(n for n in vis_nodes if n["id"] == "seed@test.com")
        depth1 = next(n for n in vis_nodes if n["id"] == "user123")
        assert seed["color"]["background"] != depth1["color"]["background"]

    def test_seed_node_larger_than_leaf(self, multi_depth_graph):
        gen = MindmapGenerator()
        vis_nodes = gen._build_vis_nodes(multi_depth_graph["nodes"])
        seed = next(n for n in vis_nodes if n["id"] == "seed@test.com")
        deep = next(n for n in vis_nodes if n["id"] == "+84900000000")
        assert seed["size"] > deep["size"]

    def test_duplicate_nodes_deduplicated(self):
        gen = MindmapGenerator()
        nodes = [
            {"target": "dup@test.com", "target_type": "EMAIL", "depth": 0},
            {"target": "dup@test.com", "target_type": "EMAIL", "depth": 0},
        ]
        vis_nodes = gen._build_vis_nodes(nodes)
        assert len(vis_nodes) == 1


# ─────────────────────────────────────────────────────────────────────────────
# AC5 — Edge labels contain plugin name
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeLabels:
    def test_edge_label_contains_plugin_name(self, simple_graph):
        gen = MindmapGenerator()
        vis_edges = gen._build_vis_edges(simple_graph["edges"])
        labels = {e["label"] for e in vis_edges}
        assert "Shodan" in labels
        assert "SearxngOSINT" in labels

    def test_edge_title_shows_plugin(self, simple_graph):
        gen = MindmapGenerator()
        vis_edges = gen._build_vis_edges(simple_graph["edges"])
        shodan_edge = next(e for e in vis_edges if e["label"] == "Shodan")
        assert "Shodan" in shodan_edge["title"]

    def test_edge_from_to_set(self, simple_graph):
        gen = MindmapGenerator()
        vis_edges = gen._build_vis_edges(simple_graph["edges"])
        shodan_edge = next(e for e in vis_edges if e["label"] == "Shodan")
        assert shodan_edge["from"] == "admin@example.com"
        assert shodan_edge["to"] == "192.168.1.1"

    def test_malformed_edge_skipped(self):
        gen = MindmapGenerator()
        bad_edges = [
            {"source": "", "discovered": "1.2.3.4", "type": "IP", "via_plugin": "X"},
            {"source": "ok@test.com", "discovered": "", "type": "IP", "via_plugin": "Y"},
        ]
        vis_edges = gen._build_vis_edges(bad_edges)
        assert len(vis_edges) == 0


# ─────────────────────────────────────────────────────────────────────────────
# AC6 — Empty graph handled gracefully
# ─────────────────────────────────────────────────────────────────────────────

class TestEmptyGraph:
    def test_empty_graph_does_not_raise(self, empty_graph):
        gen = MindmapGenerator()
        html = gen.generate(empty_graph)
        assert isinstance(html, str)
        assert len(html) > 100

    def test_empty_graph_nodes_json_is_empty_array(self, empty_graph):
        gen = MindmapGenerator()
        html = gen.generate(empty_graph)
        assert "RAW_NODES = []" in html

    def test_empty_graph_edges_json_is_empty_array(self, empty_graph):
        gen = MindmapGenerator()
        html = gen.generate(empty_graph)
        assert "RAW_EDGES = []" in html

    def test_missing_keys_handled(self):
        gen = MindmapGenerator()
        html = gen.generate({})   # Completely empty dict
        assert isinstance(html, str)
        assert len(html) > 100

    def test_title_fallback_when_no_seed(self, empty_graph):
        gen = MindmapGenerator()
        html = gen.generate(empty_graph)
        assert "OSINT Report" in html
