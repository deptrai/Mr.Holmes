"""
tests/plugins/test_plugins.py

Story 7.1 — Unit tests for IntelligencePlugin, PluginManager, and core integration.
"""
from __future__ import annotations

import pytest

from Core.plugins.base import IntelligencePlugin, PluginResult
from Core.plugins.manager import PluginManager
from Core.engine.result_collector import ScanResultCollector
from Core.config.settings import Settings


# ---------------------------------------------------------------------------
# Mock Plugins
# ---------------------------------------------------------------------------

class MockPlugin(IntelligencePlugin):
    """A valid mock plugin obeying the IntelligencePlugin protocol."""

    @property
    def name(self) -> str:
        return "MockPlugin"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def check(self, target: str, target_type: str) -> PluginResult:
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={"breaches": ["Adobe"]},
            error_message=None,
        )


class ExplodingPlugin:
    """Plugin whose check() always raises."""

    @property
    def name(self) -> str:
        return "ExplodingPlugin"

    @property
    def requires_api_key(self) -> bool:
        return False

    async def check(self, target: str, target_type: str) -> PluginResult:
        raise RuntimeError("boom")


class BrokenNamePlugin:
    """Plugin whose name property itself throws."""

    @property
    def name(self) -> str:
        raise AttributeError("name is broken")

    @property
    def requires_api_key(self) -> bool:
        return False

    async def check(self, target: str, target_type: str) -> PluginResult:
        raise RuntimeError("also boom")


# ---------------------------------------------------------------------------
# PluginResult dataclass tests
# ---------------------------------------------------------------------------

def test_plugin_result_attributes():
    """PluginResult is a dataclass with expected attributes."""
    res = PluginResult(
        plugin_name="Test",
        is_success=False,
        data={},
        error_message="API Key missing",
    )
    assert res.plugin_name == "Test"
    assert res.is_success is False
    assert res.data == {}
    assert res.error_message == "API Key missing"


def test_plugin_result_defaults():
    """error_message defaults to None."""
    res = PluginResult(plugin_name="X", is_success=True, data={"k": 1})
    assert res.error_message is None


# ---------------------------------------------------------------------------
# PluginManager tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_plugin_manager_registration_and_execution():
    """Manager registers and executes plugins concurrently."""
    manager = PluginManager()
    plugin1 = MockPlugin()

    manager.register(plugin1)

    assert len(manager.plugins) == 1
    assert manager.plugins[0].name == "MockPlugin"

    results = await manager.run_all("jane_doe", "USERNAME")
    assert len(results) == 1
    assert isinstance(results[0], PluginResult)
    assert results[0].plugin_name == "MockPlugin"
    assert results[0].data == {"breaches": ["Adobe"]}


@pytest.mark.asyncio
async def test_plugin_manager_empty_plugins():
    """run_all with zero plugins returns empty list."""
    manager = PluginManager()
    results = await manager.run_all("target", "EMAIL")
    assert results == []


def test_plugin_manager_duplicate_registration():
    """Registering the same plugin name twice is silently ignored."""
    manager = PluginManager()
    p1 = MockPlugin()
    p2 = MockPlugin()

    manager.register(p1)
    manager.register(p2)

    assert len(manager.plugins) == 1


@pytest.mark.asyncio
async def test_safe_execute_catches_plugin_exception():
    """_safe_execute wraps exceptions into a failed PluginResult."""
    manager = PluginManager()
    manager.register(ExplodingPlugin())

    results = await manager.run_all("target", "IP")
    assert len(results) == 1
    assert results[0].is_success is False
    assert results[0].plugin_name == "ExplodingPlugin"
    assert "Plugin Exception" in results[0].error_message


@pytest.mark.asyncio
async def test_safe_execute_broken_name_plugin():
    """Even if plugin.name throws, _safe_execute still returns a PluginResult."""
    manager = PluginManager()
    # Can't use register() because name throws, so inject directly
    manager._plugins.append(BrokenNamePlugin())

    results = await manager.run_all("target", "IP")
    assert len(results) == 1
    assert results[0].is_success is False
    assert results[0].plugin_name == "unknown"


def test_plugins_property_returns_copy():
    """The plugins property returns a copy, not the internal list."""
    manager = PluginManager()
    manager.register(MockPlugin())
    plugins_view = manager.plugins
    plugins_view.clear()
    assert len(manager.plugins) == 1  # internal list untouched


# ---------------------------------------------------------------------------
# ScanResultCollector integration tests
# ---------------------------------------------------------------------------

def test_scan_result_collector_add_plugin_result():
    """ScanResultCollector seamlessly assimilates PluginResult."""
    collector = ScanResultCollector(subject="USERNAME")

    p_result = PluginResult(
        plugin_name="HaveIBeenPwned",
        is_success=True,
        data={"leaks": 5},
    )

    collector.add_plugin_result(p_result)

    assert collector.total_count == 1
    assert collector.found_count == 1
    assert "Plugin: HaveIBeenPwned" in collector.found_names

    as_dict = collector.to_dict()
    finding = as_dict["results"][0]
    assert finding["name"] == "Plugin: HaveIBeenPwned"
    assert finding["plugin_data"] == {"leaks": 5}
    assert finding["site"] == ""


def test_add_plugin_result_success_empty_data():
    """is_success=True with data={} should map to FOUND (not NOT_FOUND)."""
    collector = ScanResultCollector(subject="USERNAME")

    p_result = PluginResult(
        plugin_name="CleanCheck",
        is_success=True,
        data={},
    )

    collector.add_plugin_result(p_result)

    assert collector.found_count == 1  # FOUND, not NOT_FOUND


def test_add_plugin_result_failure():
    """is_success=False should map to NOT_FOUND."""
    collector = ScanResultCollector(subject="USERNAME")

    p_result = PluginResult(
        plugin_name="FailedCheck",
        is_success=False,
        data={},
        error_message="API error",
    )

    collector.add_plugin_result(p_result)

    assert collector.found_count == 0
    assert collector.total_count == 1


# ---------------------------------------------------------------------------
# Settings.get_plugin_key tests
# ---------------------------------------------------------------------------

def test_settings_get_plugin_key(monkeypatch):
    """Settings can dynamically retrieve keys for plugins."""
    monkeypatch.setenv("MH_HAVEIBEENPWNED_API_KEY", "super_secret_123")
    monkeypatch.setenv("MH_SHODAN_API_KEY", "shodan_456")

    s = Settings()
    assert s.get_plugin_key("HaveIBeenPwned") == "super_secret_123"
    assert s.get_plugin_key("Shodan") == "shodan_456"
    assert s.get_plugin_key("UnknownPlugin") == ""


def test_settings_get_plugin_key_sanitizes_hyphens(monkeypatch):
    """Hyphens and dots in plugin names are sanitized to underscores."""
    monkeypatch.setenv("MH_HAVE_I_BEEN_PWNED_API_KEY", "key_hyphen")
    monkeypatch.setenv("MH_IP_API_COM_API_KEY", "key_dot")

    s = Settings()
    assert s.get_plugin_key("have-i-been-pwned") == "key_hyphen"
    assert s.get_plugin_key("ip-api.com") == "key_dot"
