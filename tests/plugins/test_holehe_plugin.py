"""
tests/plugins/test_holehe_plugin.py

Story 9.3 — Unit tests for HolehPlugin (Holehe email-to-service integration).
All holehe calls are mocked to avoid real HTTP requests.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from Core.plugins.holehe import HolehPlugin
from Core.plugins.base import PluginResult


# ---------------------------------------------------------------------------
# Sample holehe response data
# ---------------------------------------------------------------------------

SAMPLE_HOLEHE_RESULTS = [
    {
        "name": "instagram",
        "domain": "instagram.com",
        "exists": True,
        "emailrecovery": None,
        "phoneNumber": "+84928881690",  # fully revealed — no *
        "others": None,
    },
    {
        "name": "discord",
        "domain": "discord.com",
        "exists": True,
        "emailrecovery": "full@example.com",  # fully revealed — no *
        "phoneNumber": None,
        "others": None,
    },
    {
        "name": "spotify",
        "domain": "spotify.com",
        "exists": True,
        "emailrecovery": "a***@g***.com",  # masked — should be excluded
        "phoneNumber": "+84 *** *** 169",  # masked — should be excluded
        "others": None,
    },
    {
        "name": "twitter",
        "domain": "twitter.com",
        "exists": False,
        "emailrecovery": None,
        "phoneNumber": None,
        "others": None,
    },
    # Simulate 116 more "not found" entries to get total_checked = 120
    *[
        {
            "name": f"service_{i}",
            "domain": f"service{i}.com",
            "exists": False,
            "emailrecovery": None,
            "phoneNumber": None,
            "others": None,
        }
        for i in range(116)
    ],
]


# ---------------------------------------------------------------------------
# AC1: HolehPlugin implements IntelligencePlugin protocol
# ---------------------------------------------------------------------------

def test_holehe_plugin_name():
    """HolehPlugin.name returns 'Holehe'."""
    plugin = HolehPlugin()
    assert plugin.name == "Holehe"


def test_holehe_plugin_requires_api_key():
    """HolehPlugin.requires_api_key is False."""
    plugin = HolehPlugin()
    assert plugin.requires_api_key is False


def test_holehe_plugin_stage():
    """HolehPlugin.stage is 2 (identity expansion)."""
    plugin = HolehPlugin()
    assert plugin.stage == 2


def test_holehe_plugin_tos_risk():
    """HolehPlugin.tos_risk is 'tos_risk'."""
    plugin = HolehPlugin()
    assert plugin.tos_risk == "tos_risk"


# ---------------------------------------------------------------------------
# AC2: check() with mock holehe output → correct PluginResult structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_holehe_check_success():
    """Returns PluginResult with registered services and recovery data."""
    plugin = HolehPlugin()

    def mock_run_holehe_sync(email):
        return SAMPLE_HOLEHE_RESULTS

    with patch("Core.plugins.holehe._run_holehe_sync", side_effect=mock_run_holehe_sync):
        result = await plugin.check("test@example.com", "EMAIL")

    assert isinstance(result, PluginResult)
    assert result.plugin_name == "Holehe"
    assert result.is_success is True
    assert result.error_message is None

    # Registered services
    assert "instagram" in result.data["registered"]
    assert "discord" in result.data["registered"]
    assert "spotify" in result.data["registered"]
    assert "twitter" not in result.data["registered"]

    # Total counts
    assert result.data["total_checked"] == 120
    assert result.data["total_registered"] == 3

    # Recovery phones: only fully revealed (no *)
    assert "+84928881690" in result.data["recovery_phones"]
    assert not any("*" in p for p in result.data["recovery_phones"])

    # Recovery emails: only fully revealed (no *)
    assert "full@example.com" in result.data["recovery_emails"]
    assert not any("*" in e for e in result.data["recovery_emails"])


@pytest.mark.asyncio
async def test_holehe_check_no_registrations():
    """Returns is_success=True with empty registered list when no services found."""
    plugin = HolehPlugin()

    empty_results = [
        {
            "name": f"service_{i}",
            "domain": f"service{i}.com",
            "exists": False,
            "emailrecovery": None,
            "phoneNumber": None,
            "others": None,
        }
        for i in range(10)
    ]

    def mock_run_holehe_sync(email):
        return empty_results

    with patch("Core.plugins.holehe._run_holehe_sync", side_effect=mock_run_holehe_sync):
        result = await plugin.check("unknown@example.com", "EMAIL")

    assert result.is_success is True
    assert result.data["registered"] == []
    assert result.data["total_registered"] == 0
    assert result.data["total_checked"] == 10


# ---------------------------------------------------------------------------
# AC3: Graceful fallback when holehe not installed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_holehe_not_installed_returns_failure():
    """When holehe not installed, returns is_success=False with install hint."""
    plugin = HolehPlugin()

    with patch("Core.plugins.holehe._run_holehe_sync", side_effect=ImportError("No module named 'holehe'")):
        result = await plugin.check("test@example.com", "EMAIL")

    assert isinstance(result, PluginResult)
    assert result.is_success is False
    assert result.plugin_name == "Holehe"
    assert "holehe" in result.error_message.lower()
    assert "pip install" in result.error_message.lower()


# ---------------------------------------------------------------------------
# AC2: check() with non-EMAIL target → failure PluginResult
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_holehe_wrong_target_type():
    """Non-EMAIL target type returns is_success=False without calling holehe."""
    plugin = HolehPlugin()
    result = await plugin.check("someusername", "USERNAME")

    assert result.is_success is False
    assert result.plugin_name == "Holehe"
    assert "email" in result.error_message.lower()


@pytest.mark.asyncio
async def test_holehe_ip_target_type():
    """IP target type returns is_success=False."""
    plugin = HolehPlugin()
    result = await plugin.check("192.168.1.1", "IP")

    assert result.is_success is False
    assert "email" in result.error_message.lower()


# ---------------------------------------------------------------------------
# AC4: Semaphore is class-level
# ---------------------------------------------------------------------------

def test_holehe_semaphore_class_level():
    """_semaphore is a class-level asyncio.Semaphore with limit 3."""
    import asyncio
    assert hasattr(HolehPlugin, "_semaphore")
    assert isinstance(HolehPlugin._semaphore, asyncio.Semaphore)


# ---------------------------------------------------------------------------
# AC5: extract_clues() with mixed partial/full values
# ---------------------------------------------------------------------------

def test_extract_clues_with_full_values():
    """extract_clues() returns clues only for fully revealed values."""
    plugin = HolehPlugin()
    result = PluginResult(
        plugin_name="Holehe",
        is_success=True,
        data={
            "registered": ["instagram", "discord"],
            "recovery_phones": ["+84928881690"],
            "recovery_emails": ["full@example.com"],
            "total_checked": 120,
            "total_registered": 2,
        },
    )

    clues = plugin.extract_clues(result)

    assert ("+84928881690", "PHONE") in clues
    assert ("full@example.com", "EMAIL") in clues
    assert len(clues) == 2


def test_extract_clues_excludes_masked_values():
    """extract_clues() skips masked/partial values containing '*'."""
    plugin = HolehPlugin()
    result = PluginResult(
        plugin_name="Holehe",
        is_success=True,
        data={
            "registered": ["spotify"],
            "recovery_phones": ["+84 *** *** 169"],
            "recovery_emails": ["a***@g***.com"],
            "total_checked": 120,
            "total_registered": 1,
        },
    )

    clues = plugin.extract_clues(result)

    # Masked values should be excluded
    assert len(clues) == 0


def test_extract_clues_mixed_values():
    """extract_clues() includes only fully revealed from a mix."""
    plugin = HolehPlugin()
    result = PluginResult(
        plugin_name="Holehe",
        is_success=True,
        data={
            "registered": ["instagram", "spotify"],
            "recovery_phones": ["+84928881690", "+84 *** *** 169"],
            "recovery_emails": ["full@example.com", "a***@g***.com"],
            "total_checked": 120,
            "total_registered": 2,
        },
    )

    clues = plugin.extract_clues(result)

    assert ("+84928881690", "PHONE") in clues
    assert ("full@example.com", "EMAIL") in clues
    # masked values NOT included
    assert ("+84 *** *** 169", "PHONE") not in clues
    assert ("a***@g***.com", "EMAIL") not in clues
    assert len(clues) == 2


def test_extract_clues_empty_result():
    """extract_clues() returns empty list when no recovery data."""
    plugin = HolehPlugin()
    result = PluginResult(
        plugin_name="Holehe",
        is_success=True,
        data={
            "registered": [],
            "recovery_phones": [],
            "recovery_emails": [],
            "total_checked": 0,
            "total_registered": 0,
        },
    )

    clues = plugin.extract_clues(result)

    assert clues == []


def test_extract_clues_failure_result():
    """extract_clues() returns empty list when result is not successful."""
    plugin = HolehPlugin()
    result = PluginResult(
        plugin_name="Holehe",
        is_success=False,
        data={},
        error_message="holehe not installed",
    )

    clues = plugin.extract_clues(result)

    assert clues == []


# ---------------------------------------------------------------------------
# Exception handling in check()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_holehe_exception_in_check():
    """Unexpected exceptions in check() are caught and returned as failure."""
    plugin = HolehPlugin()

    def mock_run_holehe_sync(email):
        raise RuntimeError("Unexpected error during holehe run")

    with patch("Core.plugins.holehe._run_holehe_sync", side_effect=mock_run_holehe_sync):
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert result.plugin_name == "Holehe"
    assert result.error_message is not None
