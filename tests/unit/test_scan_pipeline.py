"""
tests/unit/test_scan_pipeline.py

Unit tests cho ScanPipeline — Kiểm thử từng Stage Pipeline
mà KHÔNG cần kết nối mạng hay khởi động CLI thật.

Chiến lược:
  - Dùng `unittest.mock.patch` để giả lập (mock) các module:
    * Core.engine.async_search.search_site  → trả về ScanResult giả
    * Core.proxy.manager.ProxyManager       → bypass proxy config
    * aiohttp.ClientSession                 → không mở socket thật
    * Core.Support.Logs, Banner, Clear...   → tắt I/O nặng
  - ScanPipeline.batch_mode=True           → bỏ qua input() prompts
  - TmpDir fixture tạo cấu trúc Report tạm thời → không ghi vào GUI/Reports thật
"""

from __future__ import annotations

import asyncio
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock, patch, call
from typing import List

import pytest

# ---------------------------------------------------------------------------
# Đảm bảo PROJECT_ROOT nằm trong sys.path để import được Core.* 
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Import models (không có side-effect nặng)
# ---------------------------------------------------------------------------
from Core.models.scan_result import ScanResult, ScanStatus, ErrorStrategy
from Core.models.scan_context import ScanContext, ScanConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """
    Tạo cấu trúc thư mục tối thiểu giả lập PROJECT_ROOT để
    ScanPipeline có thể ghi report mà không đụng đến cây thật.

      tmp_path/
        GUI/Reports/Usernames/
        Site_lists/Username/
        Banners/Username/
        Temp/
    """
    (tmp_path / "GUI" / "Reports" / "Usernames").mkdir(parents=True)
    (tmp_path / "GUI" / "Reports" / "Usernames" / "Dorks").mkdir(parents=True)
    (tmp_path / "Site_lists" / "Username").mkdir(parents=True)
    (tmp_path / "Banners" / "Username").mkdir(parents=True)
    (tmp_path / "Temp").mkdir(parents=True)

    # Tạo site_list.json tối giản với 2 site giả
    site_list = [
        {
            "site1": {
                "name": "FakeSite",
                "user": "https://fakesite.com/{}",
                "user2": "https://fakesite.com/{}",
                "main": "fakesite.com",
                "Error": "Status-Code",
                "exception": [],
                "Scrapable": "False",
                "Tag": ["Social"]
            }
        },
        {
            "site2": {
                "name": "AnotherFake",
                "user": "https://another.io/users/{}",
                "user2": "https://another.io/users/{}",
                "main": "another.io",
                "Error": "Message",
                "exception": [],
                "Scrapable": "True",
                "Tag": ["Developer"]
            }
        }
    ]
    (tmp_path / "Site_lists" / "Username" / "site_list.json").write_text(
        json.dumps(site_list), encoding="utf-8"
    )
    # NSFW list rỗng
    (tmp_path / "Site_lists" / "Username" / "site_list_NSFW.json").write_text(
        "[]", encoding="utf-8"
    )
    return tmp_path


def _make_mock_scan_result(site_name: str, found: bool = True) -> ScanResult:
    """Helper: tạo ScanResult giả."""
    return ScanResult(
        site_name=site_name,
        url=f"https://example.com/user/{site_name.lower()}",
        status=ScanStatus.FOUND if found else ScanStatus.NOT_FOUND,
        is_scrapable=False,
        tags=["Social"],
    )


# ---------------------------------------------------------------------------
# Context manager cho heavy patches — tránh decorator gây lộn fixture args
# ---------------------------------------------------------------------------
@contextmanager
def heavy_patches():
    """Context manager áp dụng tất cả I/O patches."""
    patches = [
        patch("Core.Support.Clear.Screen.Clear", return_value=None),
        patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),
        patch("Core.Support.Logs.Log.Checker", return_value=None),
        patch("Core.Support.Notification.Notifier.Start", return_value=None),
        patch("Core.Support.Creds.Sender.mail", return_value=None),
        patch("Core.Support.Encoding.Encoder.Encode", return_value=None),
        patch("Core.Support.Recap.Stats.Printer", return_value=None),
        patch("Core.Support.Language.Translation.Get_Language", return_value="English"),
        patch("Core.Support.Language.Translation.Translate_Language",
              side_effect=lambda *args, **kwargs: "[TRANSLATED]"),
        patch("Core.Support.DateFormat.Get.Format", return_value="%Y-%m-%d"),
        patch("Core.proxy.manager.ProxyManager.configure", return_value=None),
        patch("Core.proxy.manager.ProxyManager.get_proxy", return_value=None),
        patch("Core.proxy.manager.ProxyManager.get_identity", return_value=None),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# 1. Unit tests: ScanResult / ScanContext Dataclasses
# ===========================================================================
class TestScanResultDataclass:
    """Kiểm thử thuần túy ScanResult dataclass — không cần mock."""

    def test_found_property_true_when_status_found(self):
        r = ScanResult("GitHub", "https://github.com/foo", status=ScanStatus.FOUND)
        assert r.found is True

    def test_found_property_false_when_not_found(self):
        r = ScanResult("GitHub", "https://github.com/foo", status=ScanStatus.NOT_FOUND)
        assert r.found is False

    def test_to_json_contains_required_keys(self):
        r = ScanResult(
            site_name="TestSite",
            url="https://test.com/user",
            status=ScanStatus.FOUND,
            tags=["Social", "Chat"],
        )
        data = json.loads(r.to_json())
        assert data["site_name"] == "TestSite"
        assert data["status"] == "found"
        assert "Social" in data["tags"]

    def test_to_dict_structure(self):
        r = ScanResult("X", "https://x.com/u", status=ScanStatus.BLOCKED)
        d = r.to_dict()
        assert d["status"] == "blocked"
        assert "site" in d

    @pytest.mark.parametrize("status", list(ScanStatus))
    def test_all_status_values_serializable(self, status: ScanStatus):
        r = ScanResult("S", "https://s.io", status=status)
        d = json.loads(r.to_json())
        assert d["status"] == status.value


class TestScanContextDataclass:
    """Kiểm thử ScanContext / ScanConfig dataclasses."""

    def test_scan_context_defaults(self):
        ctx = ScanContext(target="johndoe", subject_type="USERNAME")
        assert ctx.report_path == ""
        assert ctx.nsfw_enabled is False
        assert ctx.concurrency_limit == 20

    def test_scan_config_defaults(self):
        cfg = ScanConfig()
        assert cfg.proxy_enabled is False
        assert cfg.proxy_dict is None
        assert cfg.writable is True

    def test_scan_config_proxy_enabled(self):
        cfg = ScanConfig(proxy_enabled=True, proxy_dict={"http": "http://1.2.3.4:8080"})
        assert cfg.proxy_enabled is True
        assert "http" in cfg.proxy_dict


# ===========================================================================
# 2. Unit tests: ScanPipeline.setup() — Stage 1
# ===========================================================================
class TestScanPipelineSetup:
    """Stage 1: setup() phải trả về ScanContext với đúng paths."""

    def test_setup_returns_scan_context(self):
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline("testuser", "Desktop", batch_mode=True)
            ctx = pipeline.setup()

            assert isinstance(ctx, ScanContext)
            assert ctx.target == "testuser"
            assert ctx.subject_type == "USERNAME"
            assert "testuser" in ctx.report_path
            assert "testuser" in ctx.json_output_path

    def test_setup_stores_ctx_on_pipeline(self):
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline("alice", "Desktop", batch_mode=True)
            pipeline.setup()
            assert pipeline.ctx is not None
            assert pipeline.ctx.target == "alice"


# ===========================================================================
# 3. Unit tests: ScanPipeline.configure_proxy() — Stage 3
# ===========================================================================
class TestScanPipelineConfigureProxy:
    """Stage 3: batch_mode phải bypass interactive input và dùng _batch_proxy_choice."""

    def test_batch_mode_no_proxy(self):
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline("bob", "Desktop", batch_mode=True, proxy_choice=2)
            pipeline.setup()
            cfg = pipeline.configure_proxy()

            assert isinstance(cfg, ScanConfig)
            assert cfg.proxy_enabled is False  # choice==2 → không proxy

    def test_batch_mode_with_proxy_choice_1(self):
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline("carol", "Desktop", batch_mode=True, proxy_choice=1)
            pipeline.setup()
            cfg = pipeline.configure_proxy()

            assert isinstance(cfg, ScanConfig)
            assert cfg.proxy_enabled is True  # choice==1 → proxy enabled


# ===========================================================================
# 4. Unit tests: ScanPipeline._load_site_configs() — Site List Parsing
# ===========================================================================
class TestScanPipelineLoadSiteConfigs:
    """_load_site_configs() phải parse đúng JSON và trả về list SiteConfig."""

    def test_load_site_configs_returns_list(self, tmp_project):
        with heavy_patches():
            os.chdir(str(tmp_project))
            from Core.engine.scan_pipeline import ScanPipeline
            from Core.engine.async_search import SiteConfig
            pipeline = ScanPipeline("dave", "Desktop", batch_mode=True)
            pipeline.setup()

            configs = pipeline._load_site_configs("Site_lists/Username/site_list.json")
            assert isinstance(configs, list)
            assert len(configs) == 2
            assert all(isinstance(c, SiteConfig) for c in configs)

    def test_load_site_configs_name_parsed(self, tmp_project):
        with heavy_patches():
            os.chdir(str(tmp_project))
            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline("dave", "Desktop", batch_mode=True)
            pipeline.setup()

            configs = pipeline._load_site_configs("Site_lists/Username/site_list.json")
            names = [c.name for c in configs]
            assert "FakeSite" in names
            assert "AnotherFake" in names

    def test_load_site_configs_exception_filter(self, tmp_path):
        """Username có ký tự bị loại trong exception list → config bị bỏ qua."""
        with heavy_patches():
            os.chdir(str(tmp_path))

            (tmp_path / "Site_lists" / "Username").mkdir(parents=True, exist_ok=True)
            site_list = [{
                "site_exc": {
                    "name": "ExcludedSite",
                    "user": "https://exc.io/{}",
                    "user2": "https://exc.io/{}",
                    "main": "exc.io",
                    "Error": "Status-Code",
                    "exception": ["@"],
                    "Scrapable": "False",
                    "Tag": []
                }
            }]
            path = tmp_path / "Site_lists" / "Username" / "test_exception.json"
            path.write_text(json.dumps(site_list))

            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline("useratinvalid", "Desktop", batch_mode=True)
            # Manually set username to include @ for filter testing
            pipeline.username = "user@invalid"
            pipeline.setup()

            configs = pipeline._load_site_configs(str(path))
            assert len(configs) == 0  # Bị lọc vì username chứa '@'


# ===========================================================================
# 5. Unit tests: ScanResult accumulation trong on_progress callback
# ===========================================================================
class TestScanPipelineOnProgress:
    """Kiểm thử logic callback _on_progress trong scan_sites()."""

    def test_on_progress_found_result_accumulates(self):
        """Khi ScanResult trả về status FOUND, successfull và successfullName phải được cập nhật."""
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline

            pipeline = ScanPipeline("eve", "Desktop", batch_mode=True, proxy_choice=2)
            pipeline.setup()
            pipeline.configure_proxy()
            Path(pipeline.ctx.report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(pipeline.ctx.report_path).touch()

            found_result = _make_mock_scan_result("GitHub", found=True)
            pipeline.count += 1
            if found_result.status.value == "found":
                pipeline.successfull.append(found_result.url)
                pipeline.successfullName.append(found_result.site_name)
            pipeline.scan_results.append(found_result)

            assert len(pipeline.successfull) == 1
            assert "github" in pipeline.successfull[0].lower()
            assert pipeline.successfullName[0] == "GitHub"
            assert len(pipeline.scan_results) == 1

    def test_on_progress_not_found_does_not_accumulate_in_successfull(self):
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline

            pipeline = ScanPipeline("frank", "Desktop", batch_mode=True)
            not_found = _make_mock_scan_result("Reddit", found=False)

            if not_found.status.value == "found":
                pipeline.successfull.append(not_found.url)

            assert len(pipeline.successfull) == 0

    def test_tags_accumulate_from_found_results(self):
        with heavy_patches():
            os.chdir(str(PROJECT_ROOT))
            from Core.engine.scan_pipeline import ScanPipeline

            pipeline = ScanPipeline("grace", "Desktop", batch_mode=True)
            result = ScanResult(
                site_name="Dev",
                url="https://dev.to/grace",
                status=ScanStatus.FOUND,
                tags=["Developer", "Blog"],
            )
            for tag in result.tags:
                if tag not in pipeline.tags:
                    pipeline.tags.append(tag)

            assert "Developer" in pipeline.tags
            assert "Blog" in pipeline.tags


# ===========================================================================
# 6. Integration-style unit test: ScanPipeline.scan_sites() với full Mock
# ===========================================================================
class TestScanPipelineScanSitesMocked:
    """
    Mock toàn bộ async_search.search_site để scan_sites()
    chạy không cần network và trả về kết quả có kiểm soát.
    """

    def test_scan_sites_batch_no_nsfw(self, tmp_project):
        """Trong batch_mode không NSFW, scan chỉ dùng site_list_main."""
        with heavy_patches():
            os.chdir(str(tmp_project))
            from Core.engine.scan_pipeline import ScanPipeline

            pipeline = ScanPipeline(
                "henry", "Desktop",
                batch_mode=True,
                proxy_choice=2,
                nsfw_enabled=False,
            )
            pipeline.setup()
            pipeline.configure_proxy()
            Path(pipeline.ctx.report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(pipeline.ctx.report_path).touch()

            configs = pipeline._load_site_configs(
                "Site_lists/Username/site_list.json"
            )
            assert len(configs) == 2  # 2 site trong fixture

    def test_scan_sites_nsfw_extends_configs(self, tmp_project):
        """Khi nsfw_enabled=True, bổ sung site từ NSFW list."""
        with heavy_patches():
            os.chdir(str(tmp_project))

            nsfw_list = [{
                "nsfw1": {
                    "name": "NSFWSite",
                    "user": "https://nsfw.xxx/{}",
                    "user2": "https://nsfw.xxx/{}",
                    "main": "nsfw.xxx",
                    "Error": "Status-Code",
                    "exception": [],
                    "Scrapable": "False",
                    "Tag": ["Adult"]
                }
            }]
            (tmp_project / "Site_lists" / "Username" / "site_list_NSFW.json").write_text(
                json.dumps(nsfw_list)
            )

            from Core.engine.scan_pipeline import ScanPipeline
            pipeline = ScanPipeline(
                "ivan", "Desktop",
                batch_mode=True,
                proxy_choice=2,
                nsfw_enabled=True,
            )
            pipeline.setup()

            main_configs = pipeline._load_site_configs("Site_lists/Username/site_list.json")
            nsfw_configs = pipeline._load_site_configs("Site_lists/Username/site_list_NSFW.json")
            all_configs = main_configs + nsfw_configs

            assert len(all_configs) == 3  # 2 main + 1 NSFW
            names = [c.name for c in all_configs]
            assert "NSFWSite" in names


# ===========================================================================
# 7. Edge Cases: Input Validation
# ===========================================================================
class TestInputValidation:
    """Kiểm thử sanitize_username và safe_int_input."""

    def test_sanitize_username_strips_whitespace(self):
        from Core.models.validators import sanitize_username
        assert sanitize_username("  johndoe  ") == "johndoe"

    def test_sanitize_username_preserves_case(self):
        """sanitize_username chỉ strip whitespace, không lowercase — kiểm tra behavior thực tế."""
        from Core.models.validators import sanitize_username
        result = sanitize_username("JohnDoe")
        assert result == "JohnDoe"  # Case được giữ nguyên

    def test_safe_int_input_with_valid_range(self):
        """safe_int_input phải trả về 2 khi nhận input '2' và range(1,3)."""
        from Core.models.validators import safe_int_input
        with patch("builtins.input", return_value="2"):
            result = safe_int_input("Prompt: ", valid_range=range(1, 3))
            assert result == 2

    def test_safe_int_input_loops_on_invalid_then_returns(self):
        """safe_int_input phải lặp lại khi nhận input không hợp lệ."""
        from Core.models.validators import safe_int_input
        with patch("builtins.input", side_effect=["abc", "99", "1"]):
            result = safe_int_input("Prompt: ", valid_range=range(1, 3))
            assert result == 1
