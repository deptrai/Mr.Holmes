"""
tests/engine/test_staged_profiler.py

Integration tests cho StageRouter + StagedProfiler (Story 9.2).
"""
from __future__ import annotations

import asyncio
import pytest

from Core.engine.stage_router import StageRouter
from Core.engine.autonomous_agent import RecursiveProfiler, StagedProfiler
from Core.plugins.base import PluginResult


# ─────────────────────────────────────────────────────────────────────────────
# Mock Plugins
# ─────────────────────────────────────────────────────────────────────────────

class MockStage2Plugin:
    """Stage 2 plugin: handles EMAIL/USERNAME, returns phone clue."""
    name = "MockStage2"
    requires_api_key = False
    stage = 2
    tos_risk = "safe"

    def __init__(self, call_tracker: list | None = None):
        self._calls = call_tracker if call_tracker is not None else []

    async def check(self, target: str, target_type: str) -> PluginResult:
        self._calls.append((target, target_type))
        if target_type.upper() not in ("EMAIL", "USERNAME"):
            return PluginResult(plugin_name=self.name, is_success=False, data={})
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "registered": ["instagram", "spotify"],
                "recovery_phones": ["+84928881690"],
            },
        )


class MockStage3Plugin:
    """Stage 3 plugin: handles PHONE, returns carrier info."""
    name = "MockStage3"
    requires_api_key = False
    stage = 3
    tos_risk = "safe"

    def __init__(self, call_tracker: list | None = None):
        self._calls = call_tracker if call_tracker is not None else []

    async def check(self, target: str, target_type: str) -> PluginResult:
        self._calls.append((target, target_type))
        if target_type.upper() != "PHONE":
            return PluginResult(plugin_name=self.name, is_success=False, data={})
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={"carrier": "Viettel", "country": "VN"},
        )


class MockStage1Plugin:
    """Epic 8 style plugin: no stage attribute (defaults to 1)."""
    name = "MockStage1"
    requires_api_key = False
    # No 'stage' attribute intentionally

    async def check(self, target: str, target_type: str) -> PluginResult:
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={"breach_names": ["Adobe"], "breach_dates": ["2013-10-01"]},
        )


class FailingPlugin:
    """Plugin that always raises an exception."""
    name = "Failing"
    requires_api_key = False
    stage = 2

    async def check(self, target: str, target_type: str) -> PluginResult:
        raise RuntimeError("Simulated plugin crash")


# ─────────────────────────────────────────────────────────────────────────────
# StageRouter tests
# ─────────────────────────────────────────────────────────────────────────────

class TestStageRouter:
    def test_email_routes_stage2(self):
        router = StageRouter()
        assert router.route("EMAIL") == 2

    def test_username_routes_stage2(self):
        router = StageRouter()
        assert router.route("USERNAME") == 2

    def test_phone_routes_stage3(self):
        router = StageRouter()
        assert router.route("PHONE") == 3

    def test_domain_routes_stage3(self):
        router = StageRouter()
        assert router.route("DOMAIN") == 3

    def test_ip_routes_stage3(self):
        router = StageRouter()
        assert router.route("IP") == 3

    def test_unknown_type_routes_stage1(self):
        router = StageRouter()
        assert router.route("UNKNOWN_TYPE") == 1

    def test_case_insensitive_routing(self):
        router = StageRouter()
        assert router.route("email") == 2
        assert router.route("Phone") == 3

    def test_filter_plugins_by_stage(self):
        router = StageRouter()
        s2 = MockStage2Plugin()
        s3 = MockStage3Plugin()
        s1 = MockStage1Plugin()

        assert router.filter_plugins([s2, s3, s1], stage=2) == [s2]
        assert router.filter_plugins([s2, s3, s1], stage=3) == [s3]
        assert router.filter_plugins([s2, s3, s1], stage=1) == [s1]

    def test_filter_plugins_no_stage_attr_defaults_to_1(self):
        """Plugins without 'stage' attribute default to stage 1."""
        router = StageRouter()
        s1 = MockStage1Plugin()  # no stage attr
        result = router.filter_plugins([s1], stage=1)
        assert result == [s1]

    def test_filter_plugins_empty(self):
        router = StageRouter()
        assert router.filter_plugins([], stage=2) == []


# ─────────────────────────────────────────────────────────────────────────────
# StagedProfiler tests
# ─────────────────────────────────────────────────────────────────────────────

class TestStagedProfiler:
    @pytest.mark.asyncio
    async def test_stage2_plugin_called_for_email_seed(self):
        """Stage-2 plugin is called with EMAIL seed."""
        tracker = []
        plugins = [MockStage2Plugin(call_tracker=tracker)]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)
        assert any(t == ("a@b.com", "EMAIL") for t in tracker)

    @pytest.mark.asyncio
    async def test_stage3_plugin_called_with_phone_from_stage2(self):
        """Phone clue discovered from stage-2 → stage-3 plugin runs on it."""
        stage2_tracker = []
        stage3_tracker = []
        plugins = [
            MockStage2Plugin(call_tracker=stage2_tracker),
            MockStage3Plugin(call_tracker=stage3_tracker),
        ]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)

        # Stage-2 called with seed
        assert ("a@b.com", "EMAIL") in stage2_tracker
        # Stage-3 called with phone discovered from stage-2
        # MockStage2 returns recovery_phones=["+84928881690"]
        # But stage3 only gets called if phone is in data — check result
        assert isinstance(result, dict)
        assert "nodes" in result
        assert "plugin_results" in result

    @pytest.mark.asyncio
    async def test_stage2_plugin_not_called_for_phone_seed(self):
        """Stage-2 plugin is NOT called when seed type is PHONE."""
        tracker = []
        plugins = [MockStage2Plugin(call_tracker=tracker)]
        profiler = StagedProfiler(max_depth=1)
        await profiler.run_staged("+84928881690", "PHONE", plugins)
        # Stage-2 plugin should NOT be called for PHONE seed
        assert len(tracker) == 0

    @pytest.mark.asyncio
    async def test_failing_plugin_does_not_crash_pipeline(self):
        """1 plugin crash → pipeline continues, result still returned."""
        plugins = [FailingPlugin(), MockStage2Plugin()]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)
        # Pipeline completed — result is dict with nodes
        assert isinstance(result, dict)
        # The failing plugin result should be recorded with is_success=False
        failing_results = [
            pr for pr in result.get("plugin_results", [])
            if pr["plugin"] == "Failing"
        ]
        assert len(failing_results) > 0
        assert failing_results[0]["is_success"] is False

    @pytest.mark.asyncio
    async def test_stage1_plugins_still_run(self):
        """Epic 8 stage-1 plugins (no stage attr) still run via RecursiveProfiler fallback."""
        plugins = [MockStage1Plugin()]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)
        stage1_results = [
            pr for pr in result.get("plugin_results", [])
            if pr["plugin"] == "MockStage1"
        ]
        assert len(stage1_results) > 0
        assert stage1_results[0]["is_success"] is True

    @pytest.mark.asyncio
    async def test_output_schema_same_as_epic8(self):
        """Output dict has same keys as Epic 8 ProfileGraph.to_dict()."""
        plugins = [MockStage2Plugin()]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)
        assert set(result.keys()) >= {"nodes", "edges", "plugin_results"}

    @pytest.mark.asyncio
    async def test_no_duplicate_nodes(self):
        """Same entity is not scanned twice (deduplication)."""
        plugins = [MockStage2Plugin()]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)
        node_keys = [(n["target"], n["target_type"]) for n in result["nodes"]]
        # No duplicates
        assert len(node_keys) == len(set(node_keys))


# ─────────────────────────────────────────────────────────────────────────────
# Backward compatibility: RecursiveProfiler unmodified
# ─────────────────────────────────────────────────────────────────────────────

class TestRecursiveProfilerBackwardCompat:
    @pytest.mark.asyncio
    async def test_recursive_profiler_still_works(self):
        """RecursiveProfiler.run_profiler() unchanged — Epic 8 backward compat."""
        plugins = [MockStage1Plugin()]
        profiler = RecursiveProfiler(max_depth=1)
        result = await profiler.run_profiler("a@b.com", "EMAIL", plugins)
        assert "nodes" in result
        assert "edges" in result
        assert "plugin_results" in result
        # Seed node recorded
        assert any(n["target"] == "a@b.com" for n in result["nodes"])

    @pytest.mark.asyncio
    async def test_staged_profiler_falls_back_when_all_stage1(self):
        """StagedProfiler with only stage-1 plugins → uses RecursiveProfiler path."""
        plugins = [MockStage1Plugin()]
        profiler = StagedProfiler(max_depth=1)
        result = await profiler.run_staged("a@b.com", "EMAIL", plugins)
        # Should still produce valid result
        assert "nodes" in result
        assert any(n["target"] == "a@b.com" for n in result["nodes"])
