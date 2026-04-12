"""
tests/cli/test_config_wizard.py

Story 7.4 — Unit tests for API Key Management UI (Config Wizard)
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from Core.cli.config_wizard import (
    get_env_key_name,
    validate_plugin_key,
    _get_key_status,
)
from Core.plugins.base import IntelligencePlugin, PluginResult


# ---------------------------------------------------------------------------
# Dummy plugin for testing
# ---------------------------------------------------------------------------
class DummyPlugin(IntelligencePlugin):
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        
    @property
    def name(self) -> str:
        return "DummyService"
        
    @property
    def requires_api_key(self) -> bool:
        return True
        
    async def check(self, target: str, target_type: str) -> PluginResult:
        if self.api_key == "VALID":
            return PluginResult("DummyService", True, {})
        if self.api_key == "QUOTA":
            return PluginResult("DummyService", False, {}, "429 Rate Limit")
        if self.api_key == "UNSUPPORTED":
            return PluginResult("DummyService", False, {}, "only supports something else")
        return PluginResult("DummyService", False, {}, "401 Unauthorized")


# ---------------------------------------------------------------------------
# Test Core Logic
# ---------------------------------------------------------------------------

def test_get_env_key_name():
    """Environment key normalization should match settings.py exactly."""
    assert get_env_key_name("HaveIBeenPwned") == "MH_HAVEIBEENPWNED_API_KEY"
    assert get_env_key_name("shodan") == "MH_SHODAN_API_KEY"
    assert get_env_key_name("API-SERVICE 2") == "MH_API_SERVICE_2_API_KEY"


@pytest.mark.asyncio
async def test_validate_plugin_key_success():
    """Valid keys return True."""
    is_valid, msg = await validate_plugin_key(DummyPlugin, "VALID")
    assert is_valid is True
    assert "valid" in msg.lower()


@pytest.mark.asyncio
async def test_validate_plugin_key_unauthorized():
    """401 responses return False."""
    is_valid, msg = await validate_plugin_key(DummyPlugin, "INVALID")
    assert is_valid is False
    assert "401" in msg


@pytest.mark.asyncio
async def test_validate_plugin_key_quota_hit():
    """429 responses return True (key is correctly formed but user is rate limited)."""
    is_valid, msg = await validate_plugin_key(DummyPlugin, "QUOTA")
    assert is_valid is True
    assert "429" in msg


@pytest.mark.asyncio
async def test_validate_plugin_key_unsupported_target():
    """If dummy target mapping breaks, fails safely instead of approving broken key."""
    is_valid, msg = await validate_plugin_key(DummyPlugin, "UNSUPPORTED")
    assert is_valid is False
    assert "unsupported target type" in msg.lower()


@patch.dict(os.environ, {"MH_DUMMY_API_KEY": "secret"}, clear=True)
@patch("dotenv.load_dotenv")
def test_get_key_status_configured(mock_load):
    """If key is in environment after dotenv.load, status is Configured."""
    status = _get_key_status("MH_DUMMY_API_KEY")
    assert "Configured" in status
    assert "green" in status


@patch.dict(os.environ, {}, clear=True)
@patch("dotenv.load_dotenv")
def test_get_key_status_missing(mock_load):
    """If key is empty/missing, status is Missing."""
    status = _get_key_status("MH_DUMMY_API_KEY")
    assert "Missing" in status
    assert "red" in status
