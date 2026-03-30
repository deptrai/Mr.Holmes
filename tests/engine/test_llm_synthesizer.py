"""
tests/engine/test_llm_synthesizer.py

Story 8.2 — LLM Synthesis Integration tests.

RED phase: Written BEFORE implementation. Must initially fail with ImportError.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from Core.plugins.base import PluginResult


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: Build fake ProfileGraph dicts (output of RecursiveProfiler)
# ─────────────────────────────────────────────────────────────────────────────

def _make_graph(
    nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
    plugin_results: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "nodes": nodes or [
            {"target": "victim@test.com", "target_type": "EMAIL", "depth": 0}
        ],
        "edges": edges or [],
        "plugin_results": plugin_results or [
            {
                "target": "victim@test.com",
                "target_type": "EMAIL",
                "plugin": "LeakLookup",
                "is_success": True,
                "data": {"data_found": True, "vulnerabilities": ["breach_db_1"]},
                "error": None,
            }
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# AC1 — LLMSynthesizer must be importable and instantiable
# ─────────────────────────────────────────────────────────────────────────────

class TestSynthesizerImport:
    def test_import_module(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer  # noqa: F401

    def test_import_result_dataclass(self):
        from Core.engine.llm_synthesizer import SynthesisResult  # noqa: F401

    def test_instantiate_default(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer()
        assert synth is not None

    def test_instantiate_with_env_overrides(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            model="gemma3:latest",
        )
        assert synth.model == "gemma3:latest"


# ─────────────────────────────────────────────────────────────────────────────
# AC2 — SynthesisResult dataclass has required fields
# ─────────────────────────────────────────────────────────────────────────────

class TestSynthesisResultFields:
    def test_success_result_fields(self):
        from Core.engine.llm_synthesizer import SynthesisResult
        r = SynthesisResult(
            is_success=True,
            report_markdown="# Report",
            model_used="gpt-4o",
        )
        assert r.is_success is True
        assert r.report_markdown == "# Report"
        assert r.model_used == "gpt-4o"
        assert r.error_message is None

    def test_failure_result_fields(self):
        from Core.engine.llm_synthesizer import SynthesisResult
        r = SynthesisResult(
            is_success=False,
            report_markdown="",
            model_used="",
            error_message="API timeout",
        )
        assert r.is_success is False
        assert r.error_message == "API timeout"


# ─────────────────────────────────────────────────────────────────────────────
# AC3 — synthesize() returns SynthesisResult with markdown report on success
# ─────────────────────────────────────────────────────────────────────────────

class TestSynthesizeSuccess:
    def _mock_successful_response(self, content: str = "## OSINT Report\nFindings here."):
        """Build a fake aiohttp response returning an OpenAI-format JSON."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [
                {"message": {"content": content}}
            ],
            "model": "gpt-4o-test",
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        return mock_response

    def test_returns_synthesis_result_type(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer, SynthesisResult

        mock_resp = self._mock_successful_response()
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            synth = LLMSynthesizer(
                base_url="http://fake-llm/v1",
                api_key="test-key",
                model="gpt-4o",
            )
            result = asyncio.run(synth.synthesize(_make_graph()))

        assert isinstance(result, SynthesisResult)

    def test_success_result_is_success_true(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer

        mock_resp = self._mock_successful_response("# Great Report")
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(
                LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m").synthesize(_make_graph())
            )

        assert result.is_success is True

    def test_success_result_contains_report_markdown(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer

        expected = "## OSINT Executive Summary\nThis is leaked."
        mock_resp = self._mock_successful_response(expected)
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(
                LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m").synthesize(_make_graph())
            )

        assert expected in result.report_markdown


# ─────────────────────────────────────────────────────────────────────────────
# AC4 — Graceful fallback when LLM credentials missing or API fails
# ─────────────────────────────────────────────────────────────────────────────

class TestSynthesizeFallback:
    def test_missing_credentials_returns_fallback_not_crash(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer

        synth = LLMSynthesizer(base_url="", api_key="", model="")
        result = asyncio.run(synth.synthesize(_make_graph()))

        # Must NOT raise; must return a SynthesisResult
        from Core.engine.llm_synthesizer import SynthesisResult
        assert isinstance(result, SynthesisResult)

    def test_missing_credentials_is_success_false(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer(base_url="", api_key="", model="")
        result = asyncio.run(synth.synthesize(_make_graph()))
        assert result.is_success is False

    def test_missing_credentials_fallback_has_report(self):
        """Even on failure, a basic plaintext summary should be in report_markdown."""
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer(base_url="", api_key="", model="")
        result = asyncio.run(synth.synthesize(_make_graph()))
        # Should contain at least node count or similar summary
        assert len(result.report_markdown) > 0

    def test_api_http_error_returns_fallback(self):
        """If the API returns a non-200, result.is_success must be False."""
        from Core.engine.llm_synthesizer import LLMSynthesizer

        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.text = AsyncMock(return_value="Internal Server Error")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(
                LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m").synthesize(_make_graph())
            )

        assert result.is_success is False

    def test_network_exception_returns_fallback(self):
        """Exception during HTTP call → graceful fallback."""
        from Core.engine.llm_synthesizer import LLMSynthesizer
        import aiohttp

        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Network down"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(
                LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m").synthesize(_make_graph())
            )

        assert result.is_success is False
        assert result.error_message is not None


# ─────────────────────────────────────────────────────────────────────────────
# AC5 — Prompt builder uses graph data properly
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptBuilding:
    def test_prompt_includes_node_count(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m")
        graph = _make_graph(nodes=[
            {"target": "a@test.com", "target_type": "EMAIL", "depth": 0},
            {"target": "b@test.com", "target_type": "EMAIL", "depth": 1},
        ])
        prompt = synth._build_user_prompt(graph)
        assert "2" in prompt  # node count

    def test_prompt_includes_target_type(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m")
        graph = _make_graph()
        prompt = synth._build_user_prompt(graph)
        assert "EMAIL" in prompt

    def test_prompt_includes_plugin_name(self):
        from Core.engine.llm_synthesizer import LLMSynthesizer
        synth = LLMSynthesizer(base_url="http://f/v1", api_key="k", model="m")
        graph = _make_graph()
        prompt = synth._build_user_prompt(graph)
        assert "LeakLookup" in prompt
