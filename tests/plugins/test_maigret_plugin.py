"""
tests/plugins/test_maigret_plugin.py

Story 9.4 — Unit tests for MaigretPlugin.
All subprocess calls are mocked to avoid real maigret invocations.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from Core.plugins.maigret import MaigretPlugin
from Core.plugins.base import PluginResult


# ---------------------------------------------------------------------------
# Sample maigret JSON output
# ---------------------------------------------------------------------------

SAMPLE_MAIGRET_OUTPUT = {
    "username": "testuser",
    "sites": {
        "GitHub": {
            "status": {"status": "Claimed"},
            "url_user": "https://github.com/testuser",
            "extra": {
                "fullname": "Test User",
                "bio": "Python developer",
                "img": "https://avatars.github.com/u/12345",
                "email": "testuser@example.com",
            },
        },
        "Twitter": {
            "status": {"status": "Claimed"},
            "url_user": "https://twitter.com/testuser",
            "extra": {
                "fullname": "Test User Twitter",
                "bio": "Tweeting things",
                "img": "",
                "email": "",
            },
        },
        "Reddit": {
            "status": {"status": "Not Found"},
            "url_user": "",
            "extra": {},
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    """Create a mock asyncio subprocess."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


def _mock_named_tempfile(tmp_file: str):
    """Return a mock for tempfile.NamedTemporaryFile that yields the given path."""
    mock_ntf = MagicMock()
    mock_ntf.name = tmp_file
    return mock_ntf


# ---------------------------------------------------------------------------
# AC1: MaigretPlugin class attributes
# ---------------------------------------------------------------------------

def test_maigret_plugin_name():
    plugin = MaigretPlugin()
    assert plugin.name == "Maigret"


def test_maigret_plugin_requires_no_api_key():
    plugin = MaigretPlugin()
    assert plugin.requires_api_key is False


def test_maigret_plugin_stage():
    plugin = MaigretPlugin()
    assert plugin.stage == 2


def test_maigret_plugin_tos_risk():
    plugin = MaigretPlugin()
    assert plugin.tos_risk == "safe"


# ---------------------------------------------------------------------------
# AC2: Non-USERNAME target type → failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_wrong_target_type():
    """Non-USERNAME target returns is_success=False without running subprocess."""
    plugin = MaigretPlugin()
    result = await plugin.check("test@example.com", "EMAIL")

    assert isinstance(result, PluginResult)
    assert result.is_success is False
    assert result.plugin_name == "Maigret"
    assert "username" in result.error_message.lower()


@pytest.mark.asyncio
async def test_check_wrong_target_type_ip():
    """IP target type returns is_success=False."""
    plugin = MaigretPlugin()
    result = await plugin.check("192.168.1.1", "IP")

    assert result.is_success is False
    assert "username" in result.error_message.lower()


# ---------------------------------------------------------------------------
# AC3: maigret not installed → graceful failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_maigret_not_installed():
    """When shutil.which('maigret') returns None, return descriptive failure."""
    plugin = MaigretPlugin()

    with patch("shutil.which", return_value=None):
        result = await plugin.check("testuser", "USERNAME")

    assert result.is_success is False
    assert result.plugin_name == "Maigret"
    assert "pip install maigret" in result.error_message


# ---------------------------------------------------------------------------
# AC4: Successful check with valid JSON output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_success_parses_claimed_profiles(tmp_path):
    """Valid maigret JSON output → PluginResult with profiles list."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    proc = make_mock_process(returncode=0)

    def write_json_side_effect(*args, **kwargs):
        Path(tmp_file).write_text(json.dumps(SAMPLE_MAIGRET_OUTPUT))
        return proc

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=write_json_side_effect)):
                result = await plugin.check("testuser", "USERNAME")

    assert result.is_success is True
    assert result.plugin_name == "Maigret"
    assert "profiles" in result.data
    assert "total_found" in result.data

    profiles = result.data["profiles"]
    # Only "Claimed" sites should be included (GitHub, Twitter — not Reddit)
    assert result.data["total_found"] == 2
    assert len(profiles) == 2

    # Check GitHub profile fields
    github_profile = next(p for p in profiles if p["site"] == "GitHub")
    assert github_profile["url"] == "https://github.com/testuser"
    assert github_profile["name"] == "Test User"
    assert github_profile["bio"] == "Python developer"
    assert github_profile["avatar_url"] == "https://avatars.github.com/u/12345"
    assert github_profile["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_check_success_case_insensitive_username_type(tmp_path):
    """target_type 'username' (lowercase) is also accepted."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    proc = make_mock_process(returncode=0)

    def write_json_side_effect(*args, **kwargs):
        Path(tmp_file).write_text(json.dumps(SAMPLE_MAIGRET_OUTPUT))
        return proc

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=write_json_side_effect)):
                result = await plugin.check("testuser", "username")

    assert result.is_success is True


# ---------------------------------------------------------------------------
# AC5: Subprocess timeout → failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_subprocess_timeout(tmp_path):
    """asyncio.TimeoutError during communicate() → failure PluginResult."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    proc = make_mock_process(returncode=0)
    proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
                result = await plugin.check("testuser", "USERNAME")

    assert result.is_success is False
    assert "timed out" in result.error_message.lower() or "300" in result.error_message
    proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# AC6: Non-zero exit code → failure with stderr excerpt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_nonzero_returncode(tmp_path):
    """Non-zero exit code returns is_success=False with stderr in error_message."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    proc = make_mock_process(returncode=1, stderr=b"Fatal error: something went wrong")

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
                result = await plugin.check("testuser", "USERNAME")

    assert result.is_success is False
    assert "1" in result.error_message or "error" in result.error_message.lower()


# ---------------------------------------------------------------------------
# AC7: JSON parse error → failure, no exception propagated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_malformed_json(tmp_path):
    """Malformed JSON in output file → failure PluginResult, no exception raised."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    proc = make_mock_process(returncode=0)

    def write_bad_json(*args, **kwargs):
        Path(tmp_file).write_text("{ this is not valid json !!!")
        return proc

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=write_bad_json)):
                result = await plugin.check("testuser", "USERNAME")

    assert result.is_success is False
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_check_missing_json_file(tmp_path):
    """Missing JSON output file → failure PluginResult, no exception raised."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "nonexistent.json")
    # Do NOT create the file
    proc = make_mock_process(returncode=0)

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
                result = await plugin.check("testuser", "USERNAME")

    assert result.is_success is False


# ---------------------------------------------------------------------------
# AC8: Temp file cleanup in finally block
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_temp_file_cleaned_up_on_success(tmp_path):
    """Temp file is deleted after successful run."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    proc = make_mock_process(returncode=0)

    def write_json_side_effect(*args, **kwargs):
        Path(tmp_file).write_text(json.dumps(SAMPLE_MAIGRET_OUTPUT))
        return proc

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=write_json_side_effect)):
                await plugin.check("testuser", "USERNAME")

    assert not os.path.exists(tmp_file), "Temp file should be cleaned up after success"


@pytest.mark.asyncio
async def test_check_temp_file_cleaned_up_on_failure(tmp_path):
    """Temp file is deleted even when subprocess fails."""
    plugin = MaigretPlugin()

    tmp_file = str(tmp_path / "output.json")
    # Create the file to simulate it being created before failure
    Path(tmp_file).write_text("partial content")
    proc = make_mock_process(returncode=1, stderr=b"error")

    with patch("shutil.which", return_value="/usr/local/bin/maigret"):
        with patch("tempfile.NamedTemporaryFile", return_value=_mock_named_tempfile(tmp_file)):
            with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
                await plugin.check("testuser", "USERNAME")

    assert not os.path.exists(tmp_file), "Temp file should be cleaned up even on failure"


# ---------------------------------------------------------------------------
# AC9: extract_clues() — only valid emails extracted
# ---------------------------------------------------------------------------

def test_extract_clues_returns_emails():
    """extract_clues() returns (email, 'EMAIL') tuples for non-empty emails."""
    plugin = MaigretPlugin()

    result = PluginResult(
        plugin_name="Maigret",
        is_success=True,
        data={
            "profiles": [
                {"site": "GitHub", "url": "...", "name": "User A", "bio": "", "avatar_url": "", "email": "usera@example.com"},
                {"site": "Twitter", "url": "...", "name": "User A", "bio": "", "avatar_url": "", "email": ""},
                {"site": "LinkedIn", "url": "...", "name": "User A", "bio": "", "avatar_url": "", "email": "usera@work.com"},
            ],
            "total_found": 3,
        },
    )

    clues = plugin.extract_clues(result)

    assert ("usera@example.com", "EMAIL") in clues
    assert ("usera@work.com", "EMAIL") in clues
    assert len(clues) == 2  # empty email should be skipped


def test_extract_clues_skips_none_email():
    """extract_clues() skips profiles with None email."""
    plugin = MaigretPlugin()

    result = PluginResult(
        plugin_name="Maigret",
        is_success=True,
        data={
            "profiles": [
                {"site": "GitHub", "url": "...", "name": "", "bio": "", "avatar_url": "", "email": None},
                {"site": "Reddit", "url": "...", "name": "", "bio": "", "avatar_url": "", "email": "valid@email.com"},
            ],
            "total_found": 2,
        },
    )

    clues = plugin.extract_clues(result)

    assert len(clues) == 1
    assert ("valid@email.com", "EMAIL") in clues


def test_extract_clues_empty_profiles():
    """extract_clues() returns empty list when no profiles."""
    plugin = MaigretPlugin()

    result = PluginResult(
        plugin_name="Maigret",
        is_success=True,
        data={"profiles": [], "total_found": 0},
    )

    clues = plugin.extract_clues(result)
    assert clues == []


def test_extract_clues_failed_result():
    """extract_clues() on failed PluginResult returns empty list gracefully."""
    plugin = MaigretPlugin()

    result = PluginResult(
        plugin_name="Maigret",
        is_success=False,
        data={},
        error_message="maigret not found",
    )

    clues = plugin.extract_clues(result)
    assert clues == []
