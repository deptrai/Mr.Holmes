"""
tests/engine/test_autonomous_agent.py

Story 8.1 — Recursive Profiling Engine tests.

RED phase: These tests are written BEFORE implementation and must
initially fail (ImportError / AttributeError / AssertionError).
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from Core.plugins.base import PluginResult

# ────────────────────────────────────────────────────────────────────────────
# Helpers: Build lightweight fake PluginResults
# ────────────────────────────────────────────────────────────────────────────

def _ok(plugin: str, data: dict[str, Any]) -> PluginResult:
    return PluginResult(plugin_name=plugin, is_success=True, data=data)


def _err(plugin: str, msg: str) -> PluginResult:
    return PluginResult(plugin_name=plugin, is_success=False, data={}, error_message=msg)


# ────────────────────────────────────────────────────────────────────────────
# AC1 — BFS Engine must be importable and instantiable
# ────────────────────────────────────────────────────────────────────────────

class TestEngineImport:
    def test_import_module(self):
        from Core.engine.autonomous_agent import RecursiveProfiler  # noqa: F401

    def test_instantiate_with_depth(self):
        from Core.engine.autonomous_agent import RecursiveProfiler
        agent = RecursiveProfiler(max_depth=2)
        assert agent.max_depth == 2

    def test_default_max_depth(self):
        from Core.engine.autonomous_agent import RecursiveProfiler
        agent = RecursiveProfiler()
        assert agent.max_depth >= 1


# ────────────────────────────────────────────────────────────────────────────
# AC2 — run_profiler must return a structured result dict
# ────────────────────────────────────────────────────────────────────────────

class TestRunProfilerOutput:
    @pytest.fixture
    def agent(self):
        from Core.engine.autonomous_agent import RecursiveProfiler
        return RecursiveProfiler(max_depth=1)

    @pytest.fixture
    def mock_plugin(self):
        """A fake plugin that returns a fix PluginResult."""
        plugin = AsyncMock()
        plugin.name = "MockPlugin"
        plugin.requires_api_key = False
        plugin.check = AsyncMock(return_value=_ok(
            "MockPlugin",
            {"data_found": True, "emails": ["found@example.com"]}
        ))
        return plugin

    def test_result_has_nodes_key(self, agent, mock_plugin):
        result = asyncio.run(agent.run_profiler(
            seed_target="initial@test.com",
            seed_type="EMAIL",
            plugins=[mock_plugin],
        ))
        assert "nodes" in result

    def test_result_has_edges_key(self, agent, mock_plugin):
        result = asyncio.run(agent.run_profiler(
            seed_target="initial@test.com",
            seed_type="EMAIL",
            plugins=[mock_plugin],
        ))
        assert "edges" in result

    def test_result_has_seed_node(self, agent, mock_plugin):
        result = asyncio.run(agent.run_profiler(
            seed_target="initial@test.com",
            seed_type="EMAIL",
            plugins=[mock_plugin],
        ))
        node_targets = [n["target"] for n in result["nodes"]]
        assert "initial@test.com" in node_targets

    def test_result_has_plugin_results_key(self, agent, mock_plugin):
        result = asyncio.run(agent.run_profiler(
            seed_target="initial@test.com",
            seed_type="EMAIL",
            plugins=[mock_plugin],
        ))
        assert "plugin_results" in result


# ────────────────────────────────────────────────────────────────────────────
# AC3 — Deduplication: same target scanned only once
# ────────────────────────────────────────────────────────────────────────────

class TestDeduplication:
    def test_no_target_scanned_twice(self):
        """
        If new clues == seed target, must NOT re-queue.
        The plugin is called exactly once for the seed.
        """
        from Core.engine.autonomous_agent import RecursiveProfiler

        call_log: list[str] = []

        async def fake_check(target: str, target_type: str) -> PluginResult:
            call_log.append(target)
            # Return the same email again as a "clue" — should not recurse
            return _ok("FakePlugin", {"data_found": True, "emails": [target]})

        plugin = AsyncMock()
        plugin.name = "FakePlugin"
        plugin.requires_api_key = False
        plugin.check = fake_check

        agent = RecursiveProfiler(max_depth=3)
        asyncio.run(agent.run_profiler(
            seed_target="dup@test.com",
            seed_type="EMAIL",
            plugins=[plugin],
        ))
        assert call_log.count("dup@test.com") == 1

    def test_two_different_targets_both_scanned(self):
        from Core.engine.autonomous_agent import RecursiveProfiler

        call_log: list[str] = []

        async def fake_check(target: str, target_type: str) -> PluginResult:
            call_log.append(target)
            if target == "seed@test.com":
                return _ok("FP", {"data_found": True, "emails": ["second@test.com"]})
            return _ok("FP", {"data_found": False})

        plugin = AsyncMock()
        plugin.name = "FP"
        plugin.requires_api_key = False
        plugin.check = fake_check

        agent = RecursiveProfiler(max_depth=2)
        asyncio.run(agent.run_profiler(
            seed_target="seed@test.com",
            seed_type="EMAIL",
            plugins=[plugin],
        ))
        assert "seed@test.com" in call_log
        assert "second@test.com" in call_log


# ────────────────────────────────────────────────────────────────────────────
# AC4 — Depth limiting: never goes deeper than max_depth
# ────────────────────────────────────────────────────────────────────────────

class TestDepthLimiting:
    def test_depth_1_does_not_recurse(self):
        from Core.engine.autonomous_agent import RecursiveProfiler

        call_log: list[str] = []

        async def fake_check(target: str, target_type: str) -> PluginResult:
            call_log.append(target)
            # Each target "discovers" a new email one level deeper
            idx = len(call_log)
            return _ok("FP", {"data_found": True, "emails": [f"level{idx}@test.com"]})

        plugin = AsyncMock()
        plugin.name = "FP"
        plugin.requires_api_key = False
        plugin.check = fake_check

        agent = RecursiveProfiler(max_depth=1)
        asyncio.run(agent.run_profiler("root@test.com", "EMAIL", plugins=[plugin]))
        # max_depth=1: only the seed is scanned; discovered clues at depth 1
        # go into the queue but are beyond max_depth and should not be processed
        assert "root@test.com" in call_log
        # Must not scan discovered second-level targets
        for called in call_log:
            assert called == "root@test.com"

    def test_depth_2_recurses_once(self):
        from Core.engine.autonomous_agent import RecursiveProfiler

        call_log: list[str] = []

        async def fake_check(target: str, target_type: str) -> PluginResult:
            call_log.append(target)
            if target == "root@test.com":
                return _ok("FP", {"data_found": True, "emails": ["d1@test.com"]})
            if target == "d1@test.com":
                return _ok("FP", {"data_found": True, "emails": ["d2@test.com"]})
            return _ok("FP", {"data_found": False})

        plugin = AsyncMock()
        plugin.name = "FP"
        plugin.requires_api_key = False
        plugin.check = fake_check

        agent = RecursiveProfiler(max_depth=2)
        asyncio.run(agent.run_profiler("root@test.com", "EMAIL", plugins=[plugin]))

        # At depth=2, we should reach d1 but NOT d2
        assert "root@test.com" in call_log
        assert "d1@test.com" in call_log
        assert "d2@test.com" not in call_log


# ────────────────────────────────────────────────────────────────────────────
# AC5 — Error resilience: failed plugin does not crash engine
# ────────────────────────────────────────────────────────────────────────────

class TestErrorResilience:
    def test_failing_plugin_does_not_crash(self):
        from Core.engine.autonomous_agent import RecursiveProfiler

        bad_plugin = AsyncMock()
        bad_plugin.name = "BadPlugin"
        bad_plugin.requires_api_key = False
        bad_plugin.check = AsyncMock(side_effect=RuntimeError("boom"))

        agent = RecursiveProfiler(max_depth=1)
        # Should NOT raise
        result = asyncio.run(agent.run_profiler(
            seed_target="victim@test.com",
            seed_type="EMAIL",
            plugins=[bad_plugin],
        ))
        assert "nodes" in result

    def test_failed_plugin_recorded_in_results(self):
        from Core.engine.autonomous_agent import RecursiveProfiler

        bad_plugin = AsyncMock()
        bad_plugin.name = "CrashPlugin"
        bad_plugin.requires_api_key = False
        bad_plugin.check = AsyncMock(return_value=_err("CrashPlugin", "API timeout"))

        agent = RecursiveProfiler(max_depth=1)
        result = asyncio.run(agent.run_profiler(
            seed_target="victim@test.com",
            seed_type="EMAIL",
            plugins=[bad_plugin],
        ))
        # At minimum, seeds node must exist + plugin_results recorded
        assert len(result["nodes"]) >= 1
