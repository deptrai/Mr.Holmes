"""tests/support/test_consent_tracker.py — Consent tracking tests."""
import pytest
import os
import json
import tempfile
from unittest import mock
from Core.Support.consent_tracker import ConsentTracker

class TestConsentTracker:
    def test_log_acceptance_creates_entry(self, tmp_path):
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", str(tmp_path / "consent.jsonl")):
            cid = ConsentTracker.log_acceptance("analyst1", "research", "CLI")
            assert len(cid) == 16
            assert os.path.exists(str(tmp_path / "consent.jsonl"))
    
    def test_log_acceptance_has_correct_fields(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            cid = ConsentTracker.log_acceptance("analyst1", "research", "CLI")
            with open(log_path) as f:
                entry = json.loads(f.readline())
            assert entry["consent_id"] == cid
            assert entry["username"] == "analyst1"
            assert entry["purpose"] == "research"
            assert entry["mode"] == "CLI"
            assert "timestamp" in entry
            assert "unix_time" in entry
    
    def test_log_investigation(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            cid = ConsentTracker.log_acceptance("analyst1", "research")
            ConsentTracker.log_investigation(cid, "torvalds", "username", ["GitHub", "DNS"], 5)
            with open(log_path) as f:
                lines = f.readlines()
            assert len(lines) == 2
            inv = json.loads(lines[1])
            assert inv["consent_id"] == cid
            assert inv["target_type"] == "username"
            assert inv["plugins_used"] == ["GitHub", "DNS"]
            assert inv["result_count"] == 5
    
    def test_get_history_empty(self, tmp_path):
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", str(tmp_path / "nonexist.jsonl")):
            assert ConsentTracker.get_history() == []
    
    def test_get_history_returns_entries(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            ConsentTracker.log_acceptance("user1", "research")
            ConsentTracker.log_acceptance("user2", "redteam")
            history = ConsentTracker.get_history()
            assert len(history) == 2
            # Newest first
            assert history[0]["username"] == "user2"
    
    def test_get_history_limit(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            for i in range(5):
                ConsentTracker.log_acceptance(f"user{i}", "research")
            assert len(ConsentTracker.get_history(limit=3)) == 3
    
    def test_has_recent_consent_true(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            ConsentTracker.log_acceptance("analyst1", "research")
            assert ConsentTracker.has_recent_consent("analyst1") is True
    
    def test_has_recent_consent_false_different_user(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            ConsentTracker.log_acceptance("analyst1", "research")
            assert ConsentTracker.has_recent_consent("analyst2") is False
    
    def test_has_recent_consent_false_expired(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            ConsentTracker.log_acceptance("analyst1", "research")
            # Write an old entry
            import time as _time
            old_entry = {"username": "analyst1", "unix_time": int(_time.time()) - 48 * 3600}
            with open(log_path, "a") as f:
                f.write(json.dumps(old_entry) + "\n")
            # The recent one should still be found
            assert ConsentTracker.has_recent_consent("analyst1", hours=24) is True
    
    def test_target_hash_is_sha256_prefix(self, tmp_path):
        log_path = str(tmp_path / "consent.jsonl")
        with mock.patch("Core.Support.consent_tracker.CONSENT_LOG", log_path):
            cid = ConsentTracker.log_acceptance("a", "r")
            ConsentTracker.log_investigation(cid, "secret_target", "username", [], 0)
            with open(log_path) as f:
                lines = f.readlines()
            inv = json.loads(lines[1])
            assert len(inv["target_hash"]) == 16
            assert inv["target_hash"] != "secret_target"  # hashed, not plaintext
