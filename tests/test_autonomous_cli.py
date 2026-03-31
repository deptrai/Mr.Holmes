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
