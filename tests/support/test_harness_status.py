"""
tests/support/test_harness_status.py

Unit tests cho Core.Support.Harness_Status.
Story US-001 — Harness Status Python wrapper.
"""
import os
import subprocess
from unittest import mock

import pytest

from Core.Support.Harness_Status import Harness_Status


class TestCliPath:
    """Test path resolution."""

    def test_cli_path_returns_string(self):
        path = Harness_Status._cli_path()
        assert isinstance(path, str)
        assert path.endswith(os.path.join("scripts", "bin", "harness-cli"))

    def test_cli_path_absolute(self):
        path = Harness_Status._cli_path()
        assert os.path.isabs(path)


class TestStats:
    """Test stats() parsing."""

    def test_stats_returns_dict_with_expected_keys(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = (
                "intakes  stories  decisions  backlog_items  traces\n"
                "1        0        7          0              1\n"
            )
            result = Harness_Status.stats()
        assert result["intakes"] == 1
        assert result["stories"] == 0
        assert result["decisions"] == 7
        assert result["backlog_items"] == 0
        assert result["traces"] == 1

    def test_stats_empty_output_returns_empty_dict(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = ""
            result = Harness_Status.stats()
        assert result == {}

    def test_stats_calls_correct_args(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = "a  b\n0  0\n"
            Harness_Status.stats()
        mock_run.assert_called_once_with(["query", "stats"])


class TestAudit:
    """Test audit() parsing."""

    def test_audit_parses_entropy_score(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = (
                "=== Harness Drift Audit ===\n\n"
                "Orphaned stories (planned/in-progress, no traces): 0\n\n"
                "Unverified stories: 0\n\n"
                "Entropy score: 0/100 (lower is better)\n"
            )
            result = Harness_Status.audit()
        assert result["entropy_score"] == 0
        assert result["drift_categories"]["Orphaned stories"] == 0
        assert result["drift_categories"]["Unverified stories"] == 0

    def test_audit_nonzero_entropy(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = "Entropy score: 42/100 (lower is better)\n"
            result = Harness_Status.audit()
        assert result["entropy_score"] == 42

    def test_audit_calls_correct_args(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = "Entropy score: 0/100\n"
            Harness_Status.audit()
        mock_run.assert_called_once_with(["audit"])


class TestMatrix:
    """Test matrix() parsing."""

    def test_matrix_returns_list_of_dicts(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = (
                "id  title  status  unit  integ  e2e  plat  evidence\n"
                "US-001  Test  implemented  1  0  0  0  pytest\n"
            )
            result = Harness_Status.matrix()
        assert len(result) == 1
        assert result[0]["id"] == "US-001"
        assert result[0]["unit"] == 1

    def test_matrix_empty_returns_empty_list(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = "id  title\n"
            result = Harness_Status.matrix()
        assert result == []

    def test_matrix_calls_numeric_mode(self):
        with mock.patch.object(Harness_Status, "_run") as mock_run:
            mock_run.return_value = "id  title\n"
            Harness_Status.matrix()
        mock_run.assert_called_once_with(["query", "matrix", "--numeric"])


class TestRunErrorHandling:
    """Test _run error paths."""

    def test_missing_binary_raises_filenotfound(self):
        with mock.patch("os.path.isfile", return_value=False):
            with pytest.raises(FileNotFoundError, match="harness-cli not found"):
                Harness_Status._run(["query", "stats"])

    def test_cli_failure_raises_runtimeerror(self):
        with mock.patch("os.path.isfile", return_value=True):
            with mock.patch("subprocess.run") as mock_run:
                mock_proc = mock.Mock()
                mock_proc.returncode = 1
                mock_proc.stdout = ""
                mock_proc.stderr = "database locked"
                mock_run.return_value = mock_proc
                with pytest.raises(RuntimeError, match="database locked"):
                    Harness_Status._run(["query", "stats"])


class TestIntegration:
    """Integration test — requires real harness-cli + harness.db."""

    def test_stats_integration_returns_real_data(self):
        """Chỉ chạy nếu harness-cli thực tồn tại."""
        cli = Harness_Status._cli_path()
        if not os.path.isfile(cli):
            pytest.skip("harness-cli not installed")
        result = Harness_Status.stats()
        assert "intakes" in result
        assert "decisions" in result
        assert result["decisions"] >= 7  # 7 ADR imported

    def test_audit_integration_returns_entropy(self):
        cli = Harness_Status._cli_path()
        if not os.path.isfile(cli):
            pytest.skip("harness-cli not installed")
        result = Harness_Status.audit()
        assert result["entropy_score"] is not None
        assert 0 <= result["entropy_score"] <= 100
