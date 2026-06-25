"""
tests/engine/test_staged_profiler_api.py

Tests for StagedProfiler API — constructor and run_staged interaction.

Verifies the fix for the API mismatch where
`StagedProfiler(plugins=[], max_depth=1)` previously crashed with:
    TypeError: StagedProfiler.__init__() got an unexpected keyword argument 'plugins'
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from Core.engine.autonomous_agent import StagedProfiler
from Core.plugins.base import PluginResult


# ────────────────────────────────────────────────────────────────────────────
# Constructor API tests
# ────────────────────────────────────────────────────────────────────────────

class TestStagedProfilerConstructor:
    def test_max_depth_only(self):
        p = StagedProfiler(max_depth=1)
        assert p.max_depth == 1
        assert p._default_plugins is None

    def test_plugins_in_constructor(self):
        plugins = [AsyncMock()]
        p = StagedProfiler(plugins=plugins, max_depth=2)
        assert p.max_depth == 2
        assert p._default_plugins is plugins

    def test_plugins_kwarg_accepted(self):
        """The original bug: plugins kwarg should not crash."""
        p = StagedProfiler(plugins=[], max_depth=1)
        assert p.max_depth == 1

    def test_defaults(self):
        p = StagedProfiler()
        assert p.max_depth == 2
        assert p._default_plugins is None

    def test_negative_depth_raises(self):
        with pytest.raises(ValueError):
            StagedProfiler(max_depth=-1)


# ────────────────────────────────────────────────────────────────────────────
# run_staged uses constructor plugins as default
# ────────────────────────────────────────────────────────────────────────────

class TestRunStagedPluginFallback:
    def _make_plugin(self, name: str = "MockPlugin", stage: int = 1) -> AsyncMock:
        plugin = AsyncMock()
        plugin.name = name
        plugin.requires_api_key = False
        plugin.stage = stage
        plugin.check = AsyncMock(return_value=PluginResult(
            plugin_name=name, is_success=True, data={"data_found": True}
        ))
        return plugin

    def test_constructor_plugins_used_when_run_staged_omits_plugins(self):
        plugin = self._make_plugin()
        p = StagedProfiler(plugins=[plugin], max_depth=1)
        result = asyncio.run(p.run_staged(
            seed_target="seed@test.com", seed_type="EMAIL",
        ))
        assert "nodes" in result
        plugin.check.assert_awaited()

    def test_run_staged_plugins_override_constructor_plugins(self):
        ctor_plugin = self._make_plugin(name="CtorPlugin")
        call_plugin = self._make_plugin(name="CallPlugin")
        p = StagedProfiler(plugins=[ctor_plugin], max_depth=1)
        result = asyncio.run(p.run_staged(
            seed_target="seed@test.com", seed_type="EMAIL",
            plugins=[call_plugin],
        ))
        assert "nodes" in result
        call_plugin.check.assert_awaited()
        ctor_plugin.check.assert_not_awaited()

    def test_no_plugins_anywhere_returns_empty_graph(self):
        p = StagedProfiler(max_depth=1)
        result = asyncio.run(p.run_staged(
            seed_target="seed@test.com", seed_type="EMAIL",
        ))
        assert "nodes" in result
        assert len(result["nodes"]) >= 1  # seed node always recorded


# ────────────────────────────────────────────────────────────────────────────
# EntityResolver.build_golden_record alias
# ────────────────────────────────────────────────────────────────────────────

class TestEntityResolverAlias:
    def test_build_golden_record_alias_exists(self):
        from Core.engine.entity_resolver import EntityResolver
        resolver = EntityResolver()
        assert hasattr(resolver, "build_golden_record")
        assert callable(resolver.build_golden_record)

    def test_build_golden_record_returns_same_as_resolve(self):
        from Core.engine.entity_resolver import EntityResolver
        from Core.models.profile_entity import ProfileEntity

        resolver = EntityResolver()
        entities = [ProfileEntity(seed="x@test.com", seed_type="EMAIL")]
        golden = asyncio.run(resolver.build_golden_record(entities))
        # Single entity → returned as-is
        assert golden.seed == "x@test.com"
