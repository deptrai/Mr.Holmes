"""
tests/models/test_scan_context.py

Unit tests cho ScanContext và ScanConfig dataclasses.
Story 1.1 — Foundation Refactoring, Epic 1.
"""
import pytest
from Core.models.scan_context import ScanContext, ScanConfig


class TestScanContext:
    """Tests cho ScanContext dataclass."""

    def test_create_with_required_fields(self):
        """ScanContext tạo được với chỉ 2 required fields."""
        ctx = ScanContext(target="johndoe", subject_type="USERNAME")
        assert ctx.target == "johndoe"
        assert ctx.subject_type == "USERNAME"

    def test_default_values(self):
        """Tất cả optional fields có đúng default values."""
        ctx = ScanContext(target="test", subject_type="EMAIL")
        assert ctx.report_path == ""
        assert ctx.json_output_path == ""
        assert ctx.json_names_path == ""
        assert ctx.nsfw_enabled is False
        assert ctx.concurrency_limit == 20

    def test_override_defaults(self):
        """Có thể override tất cả default values."""
        ctx = ScanContext(
            target="+84912345678",
            subject_type="PHONE-NUMBER",
            report_path="GUI/Reports/Phones/test.txt",
            json_output_path="GUI/Reports/Phones/test.json",
            json_names_path="GUI/Reports/Phones/names.json",
            nsfw_enabled=True,
            concurrency_limit=50,
        )
        assert ctx.target == "+84912345678"
        assert ctx.subject_type == "PHONE-NUMBER"
        assert ctx.report_path == "GUI/Reports/Phones/test.txt"
        assert ctx.nsfw_enabled is True
        assert ctx.concurrency_limit == 50

    def test_subject_types_accepted(self):
        """Các subject_type khác nhau đều được chấp nhận."""
        for subject in ["USERNAME", "PHONE-NUMBER", "EMAIL", "WEBSITE", "PERSON"]:
            ctx = ScanContext(target="test", subject_type=subject)
            assert ctx.subject_type == subject

    def test_equality(self):
        """Hai ScanContext với cùng values là equal (dataclass behavior)."""
        ctx1 = ScanContext(target="user", subject_type="USERNAME")
        ctx2 = ScanContext(target="user", subject_type="USERNAME")
        assert ctx1 == ctx2

    def test_different_targets_not_equal(self):
        """Khác target → không equal."""
        ctx1 = ScanContext(target="user1", subject_type="USERNAME")
        ctx2 = ScanContext(target="user2", subject_type="USERNAME")
        assert ctx1 != ctx2


class TestScanConfig:
    """Tests cho ScanConfig dataclass."""

    def test_create_with_defaults(self):
        """ScanConfig tạo được với 0 arguments."""
        cfg = ScanConfig()
        assert cfg.proxy_enabled is False
        assert cfg.proxy_dict is None
        assert cfg.proxy_identity is None
        assert cfg.writable is True
        assert cfg.process_tags is True

    def test_proxy_configuration(self):
        """Proxy settings được set đúng."""
        proxy = {"http": "http://10.0.0.1:8080", "https": "http://10.0.0.1:8080"}
        cfg = ScanConfig(
            proxy_enabled=True,
            proxy_dict=proxy,
            proxy_identity="Region: Ho Chi Minh, Vietnam",
        )
        assert cfg.proxy_enabled is True
        assert cfg.proxy_dict == proxy
        assert "Vietnam" in cfg.proxy_identity

    def test_non_writable_mode(self):
        """Non-writable mode — dùng khi scan phone number."""
        cfg = ScanConfig(writable=False)
        assert cfg.writable is False

    def test_no_tag_processing(self):
        """process_tags=False khi subject là PHONE-NUMBER."""
        cfg = ScanConfig(process_tags=False)
        assert cfg.process_tags is False

    def test_config_with_no_proxy(self):
        """Không có proxy — proxy_dict là None."""
        cfg = ScanConfig(proxy_enabled=False)
        assert cfg.proxy_dict is None
        assert cfg.proxy_enabled is False
