"""
Core/plugins/maigret.py

Story 9.4 — MaigretPlugin: scan a username across 3000+ sites via Maigret subprocess.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from Core.plugins.base import IntelligencePlugin, PluginResult


class MaigretPlugin:
    """
    Maigret Intelligence Plugin.
    Scans a username across 3000+ sites via maigret CLI subprocess.
    No API key required — uses maigret open-source tool.
    Stage 2: Identity expansion from a USERNAME seed.
    """

    name: str = "Maigret"
    requires_api_key: bool = False
    stage: int = 2
    tos_risk: str = "safe"

    async def check(self, target: str, target_type: str) -> PluginResult:
        """
        Scan a username across 3000+ sites via maigret subprocess.

        Args:
            target: Username string to scan.
            target_type: Must be "USERNAME" (case-insensitive).

        Returns:
            PluginResult with profiles list on success, or failure with error_message.
        """
        if target_type.upper() != "USERNAME":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Maigret only supports USERNAME targets, got {target_type}",
            )

        if not shutil.which("maigret"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="maigret not found. Run: pip install maigret",
            )

<<<<<<< HEAD
        tmp_dir = tempfile.mkdtemp()
        try:
            # maigret 0.4.4 uses: maigret <username> -J simple --folderoutput <dir>
            proc = await asyncio.create_subprocess_exec(
                "maigret", target,
                "-J", "simple",
                "--folderoutput", tmp_dir,
                "--timeout", "30",
                "--no-color",
                "--no-progressbar",
=======
        tmp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp = tmp_file.name
        tmp_file.close()
        try:
            proc = await asyncio.create_subprocess_exec(
                "maigret", target, "--json", tmp, "--timeout", "30", "--no-color",
>>>>>>> cdba61f9b0cf9314efd08901bf21b1b9eac189c1
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except asyncio.TimeoutError:
                proc.kill()
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message="Maigret timed out after 300s",
                )

            if proc.returncode != 0:
                stderr_excerpt = stderr.decode(errors="replace")[:200] if stderr else ""
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message=f"maigret exit {proc.returncode}: {stderr_excerpt}",
                )

<<<<<<< HEAD
            # Find the generated JSON file in the temp folder
            json_files = list(Path(tmp_dir).glob("*.json"))
            if not json_files:
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message="maigret produced no JSON output file",
                )
            try:
                output_data = json.loads(json_files[0].read_text())
=======
            try:
                output_data = json.loads(Path(tmp).read_text())
>>>>>>> cdba61f9b0cf9314efd08901bf21b1b9eac189c1
            except (json.JSONDecodeError, FileNotFoundError, OSError, ValueError) as e:
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message=f"Failed to parse maigret JSON output: {e}",
                )

            profiles = _parse_maigret_output(output_data)
            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={
                    "profiles": profiles,
                    "total_found": len(profiles),
                },
            )

        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Maigret unexpected error: {e}",
            )
        finally:
<<<<<<< HEAD
            import shutil as _shutil
            if os.path.exists(tmp_dir):
                _shutil.rmtree(tmp_dir, ignore_errors=True)
=======
            if os.path.exists(tmp):
                os.unlink(tmp)
>>>>>>> cdba61f9b0cf9314efd08901bf21b1b9eac189c1

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """
        Extract email clues from a MaigretPlugin result.

        Args:
            result: PluginResult from check().

        Returns:
            List of (email, "EMAIL") tuples for non-empty emails found in profiles.
        """
        clues: list[tuple[str, str]] = []
        profiles = result.data.get("profiles", [])
        for profile in profiles:
            email = profile.get("email")
            if email:
                clues.append((email, "EMAIL"))
        return clues


def _parse_maigret_output(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse maigret JSON output into a normalized list of discovered profiles.

<<<<<<< HEAD
    Supports both:
    - Old format: {"sites": {"Facebook": {...}, ...}}
    - New simple format (v0.4.4): {"Facebook": {...}, "Twitch": {...}, ...}

    Only includes entries with status "Claimed".
    """
    # Try old nested format first, then flat format
    sites: dict[str, Any] = data.get("sites", {})
    if not sites:
        # v0.4.4 simple format: top-level keys are site names
        sites = {
            k: v for k, v in data.items()
            if isinstance(v, dict) and "status" in v
        }

    profiles = []
    for site_name, site_data in sites.items():
        if not isinstance(site_data, dict):
            continue
        status_block = site_data.get("status", {}) or {}
        status = status_block.get("status", "")
        if status != "Claimed":
            continue

        # Extract extra info (ids dict contains extracted fields)
        ids = status_block.get("ids", {}) or {}
        extra_info = site_data.get("extra", {}) or {}

        profiles.append(
            {
                "site": site_name,
                "url": site_data.get("url_user", ""),
                "name": ids.get("fullname", extra_info.get("fullname", "")),
                "bio": ids.get("bio", extra_info.get("bio", "")),
                "avatar_url": ids.get("image", extra_info.get("img", "")),
                "email": ids.get("email", extra_info.get("email", "")),
            }
        )
=======
    Only includes sites with status "Claimed".
    """
    sites = data.get("sites", {})
    profiles = []
    for site_name, site_data in sites.items():
        status = site_data.get("status", {}).get("status", "")
        if status == "Claimed":
            extra = site_data.get("extra", {}) or {}
            profiles.append(
                {
                    "site": site_name,
                    "url": site_data.get("url_user", ""),
                    "name": extra.get("fullname", ""),
                    "bio": extra.get("bio", ""),
                    "avatar_url": extra.get("img", ""),
                    "email": extra.get("email", ""),
                }
            )
>>>>>>> cdba61f9b0cf9314efd08901bf21b1b9eac189c1
    return profiles
