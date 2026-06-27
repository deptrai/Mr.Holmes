"""tests/mcp/test_mcp_server.py — MCP server tool tests."""
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

class TestMCPServer:
    def test_server_exists(self):
        from Core.mcp.server import mcp
        assert mcp is not None

    def test_list_plugins_tool(self):
        from Core.mcp.server import list_plugins
        result = asyncio.run(list_plugins())
        data = json.loads(result)
        assert "plugins" in data
        assert data["count"] > 0

    def test_validate_email_valid(self):
        from Core.mcp.server import validate_email
        result = asyncio.run(validate_email("test@gmail.com"))
        data = json.loads(result)
        assert data["is_valid"] is True

    def test_validate_email_invalid(self):
        from Core.mcp.server import validate_email
        result = asyncio.run(validate_email("notanemail"))
        data = json.loads(result)
        assert data["is_valid"] is False

    def test_validate_phone(self):
        from Core.mcp.server import validate_phone
        result = asyncio.run(validate_phone("+1 234 567 890"))
        data = json.loads(result)
        assert data["normalized"] == "+1234567890"

    def test_decode_base64(self):
        from Core.mcp.server import decode_text
        result = asyncio.run(decode_text("SGVsbG8=", "base64"))
        data = json.loads(result)
        assert data["output"] == "Hello"

    def test_decode_md5(self):
        from Core.mcp.server import decode_text
        result = asyncio.run(decode_text("test", "md5"))
        data = json.loads(result)
        assert len(data["output"]) == 32

    def test_decode_sha256(self):
        from Core.mcp.server import decode_text
        result = asyncio.run(decode_text("test", "sha256"))
        data = json.loads(result)
        assert len(data["output"]) == 64

    def test_decode_unknown_format(self):
        from Core.mcp.server import decode_text
        result = asyncio.run(decode_text("test", "unknown"))
        data = json.loads(result)
        assert "error" in data

class TestEvidenceStore:
    def test_create_investigation(self, tmp_path):
        from Core.evidence.store import EvidenceStore
        store = EvidenceStore(str(tmp_path / "test.db"))
        inv_id = store.create_investigation("torvalds", "username")
        assert inv_id > 0

    def test_save_and_query_evidence(self, tmp_path):
        from Core.evidence.store import EvidenceStore
        store = EvidenceStore(str(tmp_path / "test.db"))
        inv_id = store.create_investigation("torvalds", "username")
        ev_id = store.save_evidence(inv_id, "GitHub", "torvalds", "username", {"name": "Linus"})
        assert ev_id > 0
        evidence = store.query_evidence(inv_id)
        assert len(evidence) == 1
        assert evidence[0]["tool_name"] == "GitHub"

    def test_query_evidence_by_tool(self, tmp_path):
        from Core.evidence.store import EvidenceStore
        store = EvidenceStore(str(tmp_path / "test.db"))
        inv_id = store.create_investigation("test", "username")
        store.save_evidence(inv_id, "GitHub", "test", "username", {"a": 1})
        store.save_evidence(inv_id, "DNS", "test.com", "domain", {"b": 2})
        github_only = store.query_evidence(inv_id, "GitHub")
        assert len(github_only) == 1

    def test_get_investigation(self, tmp_path):
        from Core.evidence.store import EvidenceStore
        store = EvidenceStore(str(tmp_path / "test.db"))
        inv_id = store.create_investigation("test", "username")
        store.save_evidence(inv_id, "GitHub", "test", "username", {"a": 1})
        inv = store.get_investigation(inv_id)
        assert inv["investigation"]["seed"] == "test"
        assert len(inv["evidence"]) == 1
        assert len(inv["audit_log"]) >= 2

    def test_list_investigations(self, tmp_path):
        from Core.evidence.store import EvidenceStore
        store = EvidenceStore(str(tmp_path / "test.db"))
        store.create_investigation("user1", "username")
        store.create_investigation("user2", "email")
        invs = store.list_investigations()
        assert len(invs) == 2

    def test_get_nonexistent_investigation(self, tmp_path):
        from Core.evidence.store import EvidenceStore
        store = EvidenceStore(str(tmp_path / "test.db"))
        inv = store.get_investigation(999)
        assert "error" in inv

class TestMCPPluginTools:
    def test_run_plugin_not_found(self):
        from Core.mcp.server import run_plugin
        result = asyncio.run(run_plugin("NonExistent", "test", "username"))
        data = json.loads(result)
        assert "error" in data

    def test_search_username_returns_json(self):
        from Core.mcp.server import search_username
        result = asyncio.run(search_username("torvalds"))
        data = json.loads(result)
        assert "plugin" in data or "error" in data
