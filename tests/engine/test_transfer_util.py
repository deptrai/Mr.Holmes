"""
tests/engine/test_transfer_util.py

Unit tests cho Core/engine/transfer_util.py — TransferUtil class.

Test coverage:
    - FOLDER_MAP constant
    - get_folder_name() for known and unknown options
    - build_report_path() for various categories
    - copy_report() success, missing source, error handling
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def transfer_util_mod():
    """Import TransferUtil (no I/O side effects at module level)."""
    mod = importlib.import_module("Core.engine.transfer_util")
    importlib.reload(mod)
    yield mod


class TestTransferUtilClass:
    """Verify TransferUtil class structure."""

    def test_class_exists(self, transfer_util_mod):
        assert hasattr(transfer_util_mod, "TransferUtil")

    def test_has_static_methods(self, transfer_util_mod):
        cls = transfer_util_mod.TransferUtil
        for name in ("get_folder_name", "build_report_path", "copy_report"):
            assert hasattr(cls, name), f"Missing method: {name}"

    def test_folder_map_constant(self, transfer_util_mod):
        fm = transfer_util_mod.TransferUtil.FOLDER_MAP
        assert isinstance(fm, dict)
        assert len(fm) == 9

    def test_folder_map_values(self, transfer_util_mod):
        fm = transfer_util_mod.TransferUtil.FOLDER_MAP
        assert fm[1] == "Usernames"
        assert fm[5] == "E-Mail"
        assert fm[7] == "PDF"
        assert fm[9] == "Graphs"


class TestGetFolderName:
    """Test get_folder_name static method."""

    def test_usernames(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(1) == "Usernames"

    def test_phone(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(2) == "Phone"

    def test_websites(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(3) == "Websites"

    def test_people(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(4) == "People"

    def test_email(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(5) == "E-Mail"

    def test_ports(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(6) == "Ports"

    def test_pdf(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(7) == "PDF"

    def test_maps(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(8) == "Maps"

    def test_graphs(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(9) == "Graphs"

    def test_unknown_option(self, transfer_util_mod):
        assert transfer_util_mod.TransferUtil.get_folder_name(99) == "Unknown"


class TestBuildReportPath:
    """Test build_report_path static method."""

    def test_username_path(self, transfer_util_mod):
        path = transfer_util_mod.TransferUtil.build_report_path(1, "alice", "txt")
        assert path == "GUI/Reports/Usernames/alice/alice.txt"

    def test_email_path(self, transfer_util_mod):
        path = transfer_util_mod.TransferUtil.build_report_path(5, "a@b.com", "txt")
        assert path == "GUI/Reports/E-Mail/a@b.com.txt"

    def test_pdf_path(self, transfer_util_mod):
        path = transfer_util_mod.TransferUtil.build_report_path(7, "alice", "pdf")
        assert path == "GUI/PDF/alice.pdf"

    def test_graphs_path(self, transfer_util_mod):
        path = transfer_util_mod.TransferUtil.build_report_path(9, "alice", "mh")
        assert path == "GUI/Graphs/alice/alice.mh"

    def test_maps_path(self, transfer_util_mod):
        path = transfer_util_mod.TransferUtil.build_report_path(8, "alice", "txt")
        assert path == "GUI/Maps/alice/alice.txt"


class TestCopyReport:
    """Test copy_report static method."""

    def test_copy_success(self, transfer_util_mod, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("report content")
        dst = tmp_path / "dst.txt"
        result = transfer_util_mod.TransferUtil.copy_report(
            str(src), str(dst))
        assert result is True
        assert dst.read_text() == "report content"

    def test_copy_missing_source(self, transfer_util_mod, tmp_path):
        dst = tmp_path / "dst.txt"
        result = transfer_util_mod.TransferUtil.copy_report(
            str(tmp_path / "nope.txt"), str(dst))
        assert result is False

    def test_copy_handles_error(self, transfer_util_mod, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        with mock.patch.object(transfer_util_mod.shutil, "copyfile",
                               side_effect=transfer_util_mod.shutil.Error("fail")):
            result = transfer_util_mod.TransferUtil.copy_report(
                str(src), str(tmp_path / "dst.txt"))
        assert result is False

    def test_copy_default_fmt(self, transfer_util_mod, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        result = transfer_util_mod.TransferUtil.copy_report(
            str(src), str(dst), fmt="txt")
        assert result is True
