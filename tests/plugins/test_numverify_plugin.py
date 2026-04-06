"""
tests/plugins/test_numverify_plugin.py

Story 9.8 — Unit tests for NumverifyPlugin.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from Core.plugins.numverify import NumverifyPlugin
from Core.plugins.base import PluginResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_RESPONSE = {
    "valid": True,
    "number": "84928881690",
    "local_format": "0928881690",
    "international_format": "+84928881690",
    "country_prefix": "+84",
    "country_code": "VN",
    "country_name": "Vietnam",
    "location": "Ho Chi Minh City",
    "carrier": "Mobifone",
    "line_type": "mobile",
}

INVALID_PHONE_RESPONSE = {
    "valid": False,
    "number": "0000",
    "local_format": "",
    "international_format": "",
    "country_prefix": "",
    "country_code": "",
    "country_name": "",
    "location": "",
    "carrier": "",
    "line_type": "",
}


def make_mock_response(status: int, json_data: dict):
    """Build a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    return mock_resp


def make_mock_session(mock_response):
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


# ---------------------------------------------------------------------------
# AC1: Plugin attributes
# ---------------------------------------------------------------------------


def test_plugin_name():
    plugin = NumverifyPlugin()
    assert plugin.name == "Numverify"


def test_plugin_requires_api_key():
    plugin = NumverifyPlugin()
    assert plugin.requires_api_key is True


def test_plugin_stage():
    plugin = NumverifyPlugin()
    assert plugin.stage == 3


def test_plugin_tos_risk():
    plugin = NumverifyPlugin()
    assert plugin.tos_risk == "safe"


# ---------------------------------------------------------------------------
# AC2: check() — non-PHONE target rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_phone_target_returns_failure():
    plugin = NumverifyPlugin(api_key="testkey")
    result = await plugin.check("test@example.com", "EMAIL")
    assert result.is_success is False
    assert "PHONE" in result.error_message


@pytest.mark.asyncio
async def test_non_phone_username_returns_failure():
    plugin = NumverifyPlugin(api_key="testkey")
    result = await plugin.check("johndoe", "USERNAME")
    assert result.is_success is False


# ---------------------------------------------------------------------------
# AC2: Missing API key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_api_key_returns_failure(monkeypatch):
    monkeypatch.delenv("MH_NUMVERIFY_API_KEY", raising=False)
    plugin = NumverifyPlugin()
    result = await plugin.check("+84928881690", "PHONE")
    assert result.is_success is False
    assert "MH_NUMVERIFY_API_KEY" in result.error_message


@pytest.mark.asyncio
async def test_api_key_from_env(monkeypatch):
    """NumverifyPlugin reads API key from MH_NUMVERIFY_API_KEY env var."""
    monkeypatch.setenv("MH_NUMVERIFY_API_KEY", "env_key_123")
    plugin = NumverifyPlugin()
    assert plugin.api_key == "env_key_123"


# ---------------------------------------------------------------------------
# AC2: Phone normalization
# ---------------------------------------------------------------------------


def test_normalize_phone_strips_spaces():
    plugin = NumverifyPlugin(api_key="key")
    assert plugin._normalize_phone("+84 928 881 690") == "+84928881690"


def test_normalize_phone_strips_dashes():
    plugin = NumverifyPlugin(api_key="key")
    assert plugin._normalize_phone("+1-800-555-0199") == "+18005550199"


def test_normalize_phone_strips_parens():
    plugin = NumverifyPlugin(api_key="key")
    assert plugin._normalize_phone("(+84)928881690") == "+84928881690"


def test_normalize_phone_preserves_leading_plus():
    plugin = NumverifyPlugin(api_key="key")
    assert plugin._normalize_phone("+84928881690") == "+84928881690"


def test_normalize_phone_too_short_returns_empty():
    plugin = NumverifyPlugin(api_key="key")
    assert plugin._normalize_phone("123") == ""


def test_normalize_phone_no_leading_plus():
    plugin = NumverifyPlugin(api_key="key")
    assert plugin._normalize_phone("0928881690") == "0928881690"


# ---------------------------------------------------------------------------
# AC2: check() — valid phone
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_phone_returns_success():
    plugin = NumverifyPlugin(api_key="testkey")
    mock_resp = make_mock_response(200, VALID_RESPONSE)
    mock_session = make_mock_session(mock_resp)

    with patch("Core.plugins.numverify.aiohttp.ClientSession", return_value=mock_session):
        result = await plugin.check("+84928881690", "PHONE")

    assert result.is_success is True
    assert result.data["valid"] is True
    assert result.data["country_code"] == "VN"
    assert result.data["carrier"] == "Mobifone"
    assert result.data["line_type"] == "mobile"


@pytest.mark.asyncio
async def test_valid_phone_data_fields():
    """All expected fields present in result.data."""
    plugin = NumverifyPlugin(api_key="testkey")
    mock_resp = make_mock_response(200, VALID_RESPONSE)
    mock_session = make_mock_session(mock_resp)

    with patch("Core.plugins.numverify.aiohttp.ClientSession", return_value=mock_session):
        result = await plugin.check("+84928881690", "PHONE")

    for field in ("valid", "number", "local_format", "international_format",
                  "country_prefix", "country_code", "country_name",
                  "location", "carrier", "line_type"):
        assert field in result.data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# AC3: valid=false from API → is_success=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_phone_response_is_success_true():
    """API returning valid=false is a valid result, not an error."""
    plugin = NumverifyPlugin(api_key="testkey")
    mock_resp = make_mock_response(200, INVALID_PHONE_RESPONSE)
    mock_session = make_mock_session(mock_resp)

    with patch("Core.plugins.numverify.aiohttp.ClientSession", return_value=mock_session):
        result = await plugin.check("00000000000", "PHONE")

    assert result.is_success is True
    assert result.data["valid"] is False


# ---------------------------------------------------------------------------
# AC3: API errors → failure PluginResult
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_429_returns_failure():
    plugin = NumverifyPlugin(api_key="testkey")
    mock_resp = make_mock_response(429, {})
    mock_session = make_mock_session(mock_resp)

    with patch("Core.plugins.numverify.aiohttp.ClientSession", return_value=mock_session):
        result = await plugin.check("+84928881690", "PHONE")

    assert result.is_success is False
    assert "429" in result.error_message or "rate" in result.error_message.lower()


@pytest.mark.asyncio
async def test_api_network_exception_returns_failure():
    plugin = NumverifyPlugin(api_key="testkey")
    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=Exception("Connection refused"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("Core.plugins.numverify.aiohttp.ClientSession", return_value=mock_session):
        result = await plugin.check("+84928881690", "PHONE")

    assert result.is_success is False
    assert "Connection refused" in result.error_message or "Error" in result.error_message


@pytest.mark.asyncio
async def test_phone_normalized_before_api_call():
    """Phone with spaces/dashes is normalized before being sent to API."""
    plugin = NumverifyPlugin(api_key="testkey")
    mock_resp = make_mock_response(200, VALID_RESPONSE)
    mock_session = make_mock_session(mock_resp)

    with patch("Core.plugins.numverify.aiohttp.ClientSession", return_value=mock_session) as mock_cls:
        await plugin.check("+84 928-881-690", "PHONE")

    # Verify get() was called with the normalized number
    call_kwargs = mock_session.get.call_args
    called_url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url", "")
    assert "+84928881690" in called_url or "84928881690" in called_url


@pytest.mark.asyncio
async def test_too_short_phone_returns_failure():
    """Phone that normalizes to <7 digits → failure before API call."""
    plugin = NumverifyPlugin(api_key="testkey")
    result = await plugin.check("123", "PHONE")
    assert result.is_success is False
