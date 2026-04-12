"""
tests/test_autonomous_cli.py

Story 8.4 — Unit tests for AutonomousCLI

Covers:
  - AC1: AutonomousCLI class exists and is callable
  - AC2: _InputFlow validates target, type, depth correctly
  - AC3: Orchestration calls Profiler → Mindmap → LLM in sequence
  - AC4: Artifacts saved to correct directory structure
  - AC5/AC6: Menu.py import and integration smoke test
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_GRAPH = {
    "nodes": [
        {"target": "test@test.com", "target_type": "EMAIL", "depth": 0},
        {"target": "1.2.3.4",       "target_type": "IP",    "depth": 1},
    ],
    "edges": [
        {"source": "test@test.com", "discovered": "1.2.3.4", "type": "IP", "via_plugin": "Shodan"},
    ],
    "plugin_results": [],
}

SAMPLE_LLM_RESULT = MagicMock(
    is_success=True,
    model_used="deepseek-v3.2",
    report_markdown="# OSINT Report\n\nTest result.",
    error_message=None,
)


# ─────────────────────────────────────────────────────────────────────────────
# AC1 — Class exists and is importable
# ─────────────────────────────────────────────────────────────────────────────

class TestAutonomousCLIExists:
    def test_import_autonomous_cli(self):
        from Core import autonomous_cli
        assert autonomous_cli is not None

    def test_class_exists(self):
        from Core.autonomous_cli import AutonomousCLI
        assert AutonomousCLI is not None

    def test_run_method_callable(self):
        from Core.autonomous_cli import AutonomousCLI
        assert callable(AutonomousCLI.run)

    def test_report_base_constant(self):
        from Core.autonomous_cli import _REPORT_BASE
        assert "Autonomous" in _REPORT_BASE
        assert "GUI" in _REPORT_BASE


# ─────────────────────────────────────────────────────────────────────────────
# AC2 — Input validation helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestSafeFolderName:
    def test_safe_folder_name_normal(self):
        from Core.autonomous_cli import _safe_folder_name
        assert _safe_folder_name("admin@test.com") == "admin@test.com"

    def test_safe_folder_name_spaces(self):
        from Core.autonomous_cli import _safe_folder_name
        result = _safe_folder_name("hello world")
        assert " " not in result

    def test_safe_folder_name_special_chars(self):
        from Core.autonomous_cli import _safe_folder_name
        result = _safe_folder_name("test<>:/\\|?*")
        for bad in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            assert bad not in result

    def test_safe_folder_name_max_length(self):
        from Core.autonomous_cli import _safe_folder_name
        long_name = "a" * 200
        result = _safe_folder_name(long_name)
        assert len(result) <= 80

    def test_safe_folder_name_ip(self):
        from Core.autonomous_cli import _safe_folder_name
        result = _safe_folder_name("192.168.1.1")
        assert result == "192.168.1.1"


# ─────────────────────────────────────────────────────────────────────────────
# AC3 — Orchestration pipeline (mocked)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAsyncOrchestration:

    @pytest.mark.asyncio
    async def test_run_async_calls_profiler(self):
        """RecursiveProfiler.run_profiler must be awaited."""
        from Core.autonomous_cli import _run_async

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

        mock_profiler.run_profiler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_async_calls_mindmap_generator(self):
        """MindmapGenerator.generate must be called with graph_dict."""
        from Core.autonomous_cli import _run_async

        captured_graph = {}

        def mock_generate(graph):
            captured_graph.update({"graph": graph})
            return "<html>mock</html>"

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = mock_generate
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

        assert "graph" in captured_graph
        assert captured_graph["graph"]["nodes"] == SAMPLE_GRAPH["nodes"]

    @pytest.mark.asyncio
    async def test_run_async_calls_llm_synthesizer(self):
        """LLMSynthesizer.synthesize must be awaited."""
        from Core.autonomous_cli import _run_async

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

        mock_synth.synthesize.assert_awaited_once_with(SAMPLE_GRAPH)


# ─────────────────────────────────────────────────────────────────────────────
# AC4 — File persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestFilePersistence:

    @pytest.mark.asyncio
    async def test_creates_report_directory(self):
        from Core.autonomous_cli import _run_async

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html>mindmap</html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async("target@example.com", "EMAIL", 1)

            # Directory must exist
            target_dir = Path(tmpdir) / "target@example.com"
            assert target_dir.exists()

            # All 3 artifact files must exist
            assert (target_dir / "raw_data.json").exists()
            assert (target_dir / "mindmap.html").exists()
            assert (target_dir / "ai_report.md").exists()

    @pytest.mark.asyncio
    async def test_raw_data_json_is_valid(self):
        from Core.autonomous_cli import _run_async

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async("test@example.com", "EMAIL", 1)

            json_path = Path(tmpdir) / "test@example.com" / "raw_data.json"
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            assert "nodes" in data
            assert "edges" in data

    @pytest.mark.asyncio
    async def test_llm_failure_still_saves_fallback_report(self):
        """When LLM fails, ai_report.md should contain error message, not empty."""
        from Core.autonomous_cli import _run_async

        failed_result = MagicMock(
            is_success=False,
            model_used="deepseek-v3.2",
            report_markdown="",
            error_message="Connection timeout",
        )

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=failed_result)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async("fail@example.com", "EMAIL", 1)

            md_path = Path(tmpdir) / "fail@example.com" / "ai_report.md"
            content = md_path.read_text(encoding="utf-8")
            assert "Connection timeout" in content

    @pytest.mark.asyncio
    async def test_special_char_target_uses_safe_folder(self):
        """Target with special chars must map to a safe directory name."""
        from Core.autonomous_cli import _run_async, _safe_folder_name

        target = "user<hack>@test.com"
        expected_folder = _safe_folder_name(target)
        assert "<" not in expected_folder

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
            ):
                await _run_async(target, "EMAIL", 1)

            target_dir = Path(tmpdir) / expected_folder
            assert target_dir.exists()


# ─────────────────────────────────────────────────────────────────────────────
# AC5 — Menu.py integration smoke test
# ─────────────────────────────────────────────────────────────────────────────

class TestMenuIntegration:
    def test_menu_imports_autonomous_cli(self):
        """Menu.py must import autonomous_cli without error."""
        from Core.Support import Menu
        import Core.autonomous_cli as acli
        assert hasattr(acli, "AutonomousCLI")

    def test_autonomous_cli_run_handles_keyboard_interrupt(self):
        """AutonomousCLI.run must catch KeyboardInterrupt gracefully."""
        from Core.autonomous_cli import AutonomousCLI

        with (
            patch("Core.autonomous_cli._InputFlow.collect", side_effect=KeyboardInterrupt),
            patch("builtins.input", return_value=""),
        ):
            # Should NOT raise
            AutonomousCLI.run("Desktop")

    def test_autonomous_cli_run_handles_unexpected_exception(self):
        """AutonomousCLI.run must catch generic exceptions gracefully."""
        from Core.autonomous_cli import AutonomousCLI

        with (
            patch("Core.autonomous_cli._InputFlow.collect", side_effect=RuntimeError("boom")),
            patch("builtins.input", return_value=""),
        ):
            # Should NOT raise
            AutonomousCLI.run("Desktop")

# ─────────────────────────────────────────────────────────────────────────────
# Story 9.6 — New tests: detect_seed_type, _build_profile_entity, golden_record
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectSeedType:
    """Tests for detect_seed_type() — AC1."""

    def test_email_detection(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("user@example.com") == "EMAIL"

    def test_email_with_subdomains(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("admin@mail.example.co.uk") == "EMAIL"

    def test_phone_with_plus(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("+84912345678") == "PHONE"

    def test_phone_digits_only_9_chars(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("123456789") == "PHONE"

    def test_phone_digits_only_15_chars(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("123456789012345") == "PHONE"

    def test_phone_too_short_is_username(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("12345678") == "USERNAME"

    def test_phone_too_long_is_username(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("1234567890123456") == "USERNAME"

    def test_username_alpha(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("johndoe") == "USERNAME"

    def test_username_with_numbers(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("user123") == "USERNAME"

    def test_strips_whitespace(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("  user@test.com  ") == "EMAIL"


class TestBuildProfileEntity:
    """Tests for _build_profile_entity() — AC4, AC5."""

    def test_returns_profile_entity(self):
        from Core.autonomous_cli import _build_profile_entity
        from Core.models.profile_entity import ProfileEntity
        entity = _build_profile_entity({}, "test@example.com", "EMAIL")
        assert isinstance(entity, ProfileEntity)

    def test_seed_and_type_set(self):
        from Core.autonomous_cli import _build_profile_entity
        entity = _build_profile_entity({}, "test@example.com", "EMAIL")
        assert entity.seed == "test@example.com"
        assert entity.seed_type == "EMAIL"

    def test_extracts_real_names_from_maigret_profiles(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [{
                "plugin": "Maigret", "is_success": True,
                "data": {"profiles": [
                    {"name": "Alice Smith", "site": "GitHub", "url": "https://github.com/alice", "bio": "", "avatar_url": "", "email": ""},
                    {"name": "", "site": "Twitter", "url": "", "bio": "", "avatar_url": "", "email": ""},  # empty name skipped
                ]},
            }]
        }
        entity = _build_profile_entity(graph, "alice", "USERNAME")
        assert len(entity.real_names) == 1
        assert entity.real_names[0].value == "Alice Smith"

    def test_extracts_breach_sources_from_hibp(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [{
                "plugin": "HaveIBeenPwned", "is_success": True,
                "data": {"breach_names": ["Adobe", "LinkedIn"]},
            }]
        }
        entity = _build_profile_entity(graph, "test@example.com", "EMAIL")
        assert "Adobe" in entity.breach_sources
        assert "LinkedIn" in entity.breach_sources

    def test_extracts_breach_sources_from_leaklookup(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [{
                "plugin": "LeakLookup", "is_success": True,
                "data": {"hostnames": ["example.com", "leaked.io"]},
            }]
        }
        entity = _build_profile_entity(graph, "test@example.com", "EMAIL")
        assert "example.com" in entity.breach_sources

    def test_extracts_platforms_from_maigret(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [{
                "plugin": "Maigret", "is_success": True,
                "data": {"profiles": [
                    {"name": "Alice", "site": "GitHub", "url": "https://github.com/alice", "bio": "", "avatar_url": "", "email": ""},
                ]},
            }]
        }
        entity = _build_profile_entity(graph, "alice", "USERNAME")
        assert "github" in entity.platforms
        assert entity.platforms["github"] == "https://github.com/alice"

    def test_skips_failed_plugin_results(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [{
                "plugin": "HaveIBeenPwned", "is_success": False,
                "data": {"breach_names": ["Adobe"]},
            }]
        }
        entity = _build_profile_entity(graph, "test@example.com", "EMAIL")
        assert "Adobe" not in entity.breach_sources

    def test_deduplicates_breach_sources(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [
                {"plugin": "HIBP", "is_success": True, "data": {"breach_names": ["Adobe"]}},
                {"plugin": "LeakLookup", "is_success": True, "data": {"hostnames": ["Adobe"]}},
            ]
        }
        entity = _build_profile_entity(graph, "test@example.com", "EMAIL")
        assert entity.breach_sources.count("Adobe") == 1

    def test_confidence_set_when_fields_exist(self):
        from Core.autonomous_cli import _build_profile_entity
        graph = {
            "plugin_results": [{
                "plugin": "Maigret", "is_success": True,
                "data": {"profiles": [{"name": "Alice", "site": "GitHub", "url": "url", "bio": "", "avatar_url": "", "email": ""}]},
            }]
        }
        entity = _build_profile_entity(graph, "alice", "USERNAME")
        assert entity.confidence > 0

    def test_empty_graph_returns_empty_entity(self):
        from Core.autonomous_cli import _build_profile_entity
        entity = _build_profile_entity({"plugin_results": []}, "test@example.com", "EMAIL")
        assert entity.real_names == []
        assert entity.breach_sources == []
        assert entity.confidence == 0.0


class TestGoldenRecordPersistence:
    """Tests for golden_record.json saved by _run_async() — AC4, AC5."""

    @pytest.mark.asyncio
    async def test_golden_record_json_created(self):
        from Core.autonomous_cli import _run_async

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

            golden_path = Path(tmpdir) / "test@test.com" / "golden_record.json"
            assert golden_path.exists(), "golden_record.json must be created"

    @pytest.mark.asyncio
    async def test_golden_record_json_valid_schema(self):
        from Core.autonomous_cli import _run_async

        graph_with_data = {
            "nodes": [{"target": "test@test.com", "target_type": "EMAIL", "depth": 0}],
            "edges": [],
            "plugin_results": [{
                "plugin": "Maigret", "is_success": True, "target": "test@test.com", "target_type": "EMAIL",
                "data": {"profiles": [
                    {"name": "Test User", "site": "GitHub", "url": "https://github.com/test", "bio": "", "avatar_url": "", "email": ""},
                ]},
                "error": None,
            }],
        }

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=graph_with_data)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

            golden_path = Path(tmpdir) / "test@test.com" / "golden_record.json"
            data = json.loads(golden_path.read_text(encoding="utf-8"))
            assert "seed" in data
            assert "seed_type" in data
            assert "real_names" in data
            assert "breach_sources" in data
            assert "confidence" in data
            assert data["seed"] == "test@test.com"
            assert data["seed_type"] == "EMAIL"


class TestTosRiskDisplay:
    """Tests for _display_tos_summary() — AC2."""

    def test_display_returns_true_on_confirmation(self):
        from Core.autonomous_cli import _display_tos_summary

        class SafePlugin:
            name = "SafePlugin"
            stage = 1
            tos_risk = "safe"

        with patch("builtins.input", return_value="y"):
            result = _display_tos_summary([SafePlugin()])
        assert result is True

    def test_display_returns_false_on_cancel(self):
        from Core.autonomous_cli import _display_tos_summary

        class SafePlugin:
            name = "SafePlugin"
            stage = 1
            tos_risk = "safe"

        with patch("builtins.input", return_value="n"):
            result = _display_tos_summary([SafePlugin()])
        assert result is False

    def test_empty_plugin_list_returns_true(self):
        from Core.autonomous_cli import _display_tos_summary
        with patch("builtins.input", return_value="y"):
            result = _display_tos_summary([])
        assert result is True

    def test_ban_risk_plugin_requires_separate_confirmation(self):
        """AC2: ban_risk plugins need explicit 'y' confirmation."""
        from Core.autonomous_cli import _display_tos_summary

        class BanRiskPlugin:
            name = "DangerPlugin"
            stage = 2
            tos_risk = "ban_risk"

        # First input: general proceed, second input: ban_risk confirm
        with patch("builtins.input", side_effect=["y", "y"]):
            result = _display_tos_summary([BanRiskPlugin()])
        assert result is True

    def test_ban_risk_plugin_rejected_cancels(self):
        """AC2: rejecting ban_risk confirmation cancels the whole flow."""
        from Core.autonomous_cli import _display_tos_summary

        class BanRiskPlugin:
            name = "DangerPlugin"
            stage = 2
            tos_risk = "ban_risk"

        with patch("builtins.input", side_effect=["y", "n"]):
            result = _display_tos_summary([BanRiskPlugin()])
        assert result is False

    def test_ban_risk_mixed_plugins_second_rejected(self):
        """AC2: multiple ban_risk plugins — rejecting any one cancels."""
        from Core.autonomous_cli import _display_tos_summary

        class SafePlugin:
            name = "Safe"
            stage = 1
            tos_risk = "safe"

        class Ban1:
            name = "Ban1"
            stage = 2
            tos_risk = "ban_risk"

        class Ban2:
            name = "Ban2"
            stage = 2
            tos_risk = "ban_risk"

        # Proceed=y, Ban1=y, Ban2=n
        with patch("builtins.input", side_effect=["y", "y", "n"]):
            result = _display_tos_summary([SafePlugin(), Ban1(), Ban2()])
        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.17 — AC3: detect_seed_type supports IP/DOMAIN
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectSeedTypeIPDomain:
    def test_ipv4_address_returns_IP(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("192.168.1.1") == "IP"

    def test_ipv4_all_zeros_returns_IP(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("0.0.0.0") == "IP"

    def test_ipv4_with_spaces_returns_IP(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("  10.0.0.1  ") == "IP"

    def test_invalid_octet_999_returns_DOMAIN(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("999.999.999.999") == "DOMAIN"

    def test_invalid_octet_256_returns_DOMAIN(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("256.1.1.1") == "DOMAIN"

    def test_domain_with_dot_returns_DOMAIN(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("example.com") == "DOMAIN"

    def test_domain_with_subdomain_returns_DOMAIN(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("sub.example.com") == "DOMAIN"

    def test_email_not_domain(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("user@example.com") == "EMAIL"

    def test_username_no_dot_returns_USERNAME(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("luisphan") == "USERNAME"

    def test_existing_email_unchanged(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("test@gmail.com") == "EMAIL"

    def test_existing_phone_unchanged(self):
        from Core.autonomous_cli import detect_seed_type
        assert detect_seed_type("+84901234567") == "PHONE"


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.17 — AC5: StagedProfiler routing test
# ─────────────────────────────────────────────────────────────────────────────

class TestStagedProfilerRouting:
    @pytest.mark.asyncio
    async def test_run_async_uses_staged_profiler_when_stage2_plugin(self):
        """_run_async routes to StagedProfiler when at least one plugin has stage >= 2."""
        from Core.autonomous_cli import _run_async

        class Stage2Plugin:
            name = "GitHub"
            stage = 2
            tos_risk = "safe"

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = [Stage2Plugin()]
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        mock_staged_cls = MagicMock()
        mock_staged = MagicMock()
        mock_staged.run_staged = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_staged_cls.return_value = mock_staged

        mock_recursive_cls = MagicMock()
        mock_recursive = MagicMock()
        mock_recursive.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_recursive_cls.return_value = mock_recursive

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
                patch("Core.engine.autonomous_agent.StagedProfiler", mock_staged_cls),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_recursive_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

        mock_staged.run_staged.assert_called_once()
        mock_recursive.run_profiler.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_async_uses_recursive_profiler_when_all_stage1(self):
        """_run_async routes to RecursiveProfiler when all plugins are stage == 1."""
        from Core.autonomous_cli import _run_async

        class Stage1Plugin:
            name = "HIBP"
            stage = 1
            tos_risk = "safe"

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = [Stage1Plugin()]
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        mock_staged_cls = MagicMock()
        mock_staged = MagicMock()
        mock_staged.run_staged = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_staged_cls.return_value = mock_staged

        mock_recursive_cls = MagicMock()
        mock_recursive = MagicMock()
        mock_recursive.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_recursive_cls.return_value = mock_recursive

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
                patch("Core.engine.autonomous_agent.StagedProfiler", mock_staged_cls),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_recursive_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
            ):
                await _run_async("test@test.com", "EMAIL", 1)

        mock_recursive.run_profiler.assert_called_once()
        mock_staged.run_staged.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.17 — AC6: _build_profile_entity extracts emails from GitHub data
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildProfileEntityEmails:
    def test_github_emails_extracted_to_entity_emails(self):
        """_build_profile_entity must populate entity.emails from GitHub data['emails']."""
        from Core.autonomous_cli import _build_profile_entity

        graph_data = {
            "plugin_results": [
                {
                    "plugin": "GitHub",
                    "is_success": True,
                    "data": {
                        "emails": ["found@example.com", "other@example.com"],
                        "real_names": [],
                    },
                }
            ]
        }
        entity = _build_profile_entity(graph_data, "testuser", "USERNAME")
        email_values = [f.value for f in entity.emails]
        assert "found@example.com" in email_values
        assert "other@example.com" in email_values

    def test_github_emails_have_source_and_confidence(self):
        """Extracted emails must be SourcedField with source='GitHub' and confidence>0."""
        from Core.autonomous_cli import _build_profile_entity

        graph_data = {
            "plugin_results": [
                {
                    "plugin": "GitHub",
                    "is_success": True,
                    "data": {"emails": ["alice@example.com"], "real_names": []},
                }
            ]
        }
        entity = _build_profile_entity(graph_data, "alice", "USERNAME")
        assert entity.emails
        sf = entity.emails[0]
        assert sf.value == "alice@example.com"
        assert "GitHub" in sf.source
        assert sf.confidence > 0

    def test_github_emails_deduplicated(self):
        """Duplicate emails from GitHub data must not be added twice."""
        from Core.autonomous_cli import _build_profile_entity

        graph_data = {
            "plugin_results": [
                {
                    "plugin": "GitHub",
                    "is_success": True,
                    "data": {"emails": ["dup@example.com", "dup@example.com"], "real_names": []},
                }
            ]
        }
        entity = _build_profile_entity(graph_data, "someone", "USERNAME")
        email_values = [f.value for f in entity.emails]
        assert email_values.count("dup@example.com") == 1

    def test_failed_plugin_result_not_processed(self):
        """is_success=False plugin results must not contribute emails."""
        from Core.autonomous_cli import _build_profile_entity

        graph_data = {
            "plugin_results": [
                {
                    "plugin": "GitHub",
                    "is_success": False,
                    "data": {"emails": ["leaked@example.com"]},
                }
            ]
        }
        entity = _build_profile_entity(graph_data, "testuser", "EMAIL")
        assert entity.emails == []


class TestGracefulDegradation:
    """Tests for graceful degradation when holehe/maigret not installed — AC8."""

    @pytest.mark.asyncio
    async def test_run_async_without_epic9_plugins_still_works(self):
        """Without Holehe/Maigret, _run_async still produces output files."""
        from Core.autonomous_cli import _run_async

        mock_pm_cls = MagicMock()
        mock_pm = MagicMock()
        mock_pm.plugins = []  # no plugins at all
        mock_pm.discover_plugins = MagicMock()
        mock_pm_cls.return_value = mock_pm

        mock_profiler_cls = MagicMock()
        mock_profiler = MagicMock()
        mock_profiler.run_profiler = AsyncMock(return_value=SAMPLE_GRAPH)
        mock_profiler_cls.return_value = mock_profiler

        mock_gen_cls = MagicMock()
        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value="<html></html>")
        mock_gen_cls.return_value = mock_gen

        mock_synth_cls = MagicMock()
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=SAMPLE_LLM_RESULT)
        mock_synth_cls.return_value = mock_synth

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("Core.autonomous_cli._REPORT_BASE", tmpdir),
                patch("Core.plugins.manager.PluginManager", mock_pm_cls),
                patch("Core.engine.autonomous_agent.RecursiveProfiler", mock_profiler_cls),
                patch("Core.engine.mindmap_generator.MindmapGenerator", mock_gen_cls),
                patch("Core.engine.llm_synthesizer.LLMSynthesizer", mock_synth_cls),
            ):
                # Should NOT raise even without Epic 9 plugins
                await _run_async("test@test.com", "EMAIL", 1)

            target_dir = Path(tmpdir) / "test@test.com"
            assert (target_dir / "raw_data.json").exists()
            assert (target_dir / "golden_record.json").exists()
