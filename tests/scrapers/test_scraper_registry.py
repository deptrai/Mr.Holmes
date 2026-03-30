"""
tests/scrapers/test_scraper_registry.py

Unit tests for ScraperRegistry — Story 1.4.
AC6: Verify dispatch routing and error handling.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from Core.scrapers.registry import ScraperRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_registry(*names) -> tuple[ScraperRegistry, dict]:
    """Build registry pre-loaded with mock callables for the given names."""
    registry = ScraperRegistry()
    mocks = {}
    for name in names:
        m = MagicMock()
        registry.register(name, m)
        mocks[name] = m
    return registry, mocks


# ---------------------------------------------------------------------------
# AC1 / AC5 — register() API
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_returns_self_for_chaining(self):
        reg = ScraperRegistry()
        fn = lambda p: None
        result = reg.register("SitA", fn)
        assert result is reg

    def test_register_multiple_chained(self):
        reg = (ScraperRegistry()
               .register("A", lambda p: None)
               .register("B", lambda p: None)
               .register("C", lambda p: None))
        assert reg.registered_names() == ["A", "B", "C"]

    def test_register_non_callable_raises_type_error(self):
        reg = ScraperRegistry()
        with pytest.raises(TypeError, match="must be callable"):
            reg.register("Bad", "not_a_function")

    def test_registered_names_empty_on_init(self):
        reg = ScraperRegistry()
        assert reg.registered_names() == []

    def test_registered_names_returns_all(self):
        reg, _ = _make_registry("Instagram", "Twitter", "GitHub")
        assert set(reg.registered_names()) == {"Instagram", "Twitter", "GitHub"}


# ---------------------------------------------------------------------------
# AC3 / AC4 — dispatch() routing and proxy fallback
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_dispatch_calls_matching_scrapers(self):
        reg, mocks = _make_registry("Instagram", "Twitter", "GitHub")
        reg.dispatch(["Instagram", "GitHub"], http_proxy={"http": "p"})

        mocks["Instagram"].assert_called_once_with({"http": "p"})
        mocks["GitHub"].assert_called_once_with({"http": "p"})
        mocks["Twitter"].assert_not_called()

    def test_dispatch_skips_unregistered_site(self):
        reg, mocks = _make_registry("Instagram")
        # "UnknownSite" is NOT registered — should not raise
        reg.dispatch(["Instagram", "UnknownSite"], http_proxy=None)
        mocks["Instagram"].assert_called_once_with(None)

    def test_dispatch_empty_sites_list_does_nothing(self):
        reg, mocks = _make_registry("Instagram")
        reg.dispatch([], http_proxy={"http": "p"})
        mocks["Instagram"].assert_not_called()

    def test_dispatch_calls_with_proxy_none(self):
        reg, mocks = _make_registry("TikTok")
        reg.dispatch(["TikTok"], http_proxy=None)
        mocks["TikTok"].assert_called_once_with(None)

    def test_dispatch_all_registered_when_all_in_sites(self):
        names = ["A", "B", "C", "D"]
        reg, mocks = _make_registry(*names)
        reg.dispatch(names, http_proxy=None)
        for m in mocks.values():
            m.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# AC4 — Proxy fallback behaviour
# ---------------------------------------------------------------------------

class TestProxyFallback:
    def test_connection_error_retries_without_proxy(self):
        proxy = {"http": "http://proxy:8080"}
        calls = []

        def scraper(p):
            calls.append(p)
            if p is not None:
                raise ConnectionError("refused")

        reg = ScraperRegistry().register("Site", scraper)
        reg.dispatch(["Site"], http_proxy=proxy)

        assert calls == [proxy, None], "Should try proxy first, then None"

    def test_connection_error_fallback_exception_silenced(self):
        """If retry also raises, dispatch should not propagate."""
        call_count = {"n": 0}

        def always_fail(p):
            call_count["n"] += 1
            raise (ConnectionError("fail") if call_count["n"] == 1 else RuntimeError("also fail"))

        reg = ScraperRegistry().register("Site", always_fail)
        # Should not raise
        reg.dispatch(["Site"], http_proxy={"http": "x"})
        assert call_count["n"] == 2

    def test_generic_exception_silenced(self):
        called = []

        def explodes(p):
            called.append(p)
            raise ValueError("boom")

        reg = ScraperRegistry().register("Site", explodes)
        # Should not raise
        reg.dispatch(["Site"], http_proxy=None)
        assert len(called) == 1

    def test_dispatch_continues_after_failed_scraper(self):
        """Failed scraper should not stop subsequent dispatches."""
        order = []

        def fail(p):
            order.append("fail")
            raise RuntimeError("X")

        def ok(p):
            order.append("ok")

        reg = (ScraperRegistry()
               .register("Bad", fail)
               .register("Good", ok))
        reg.dispatch(["Bad", "Good"], http_proxy=None)
        assert order == ["fail", "ok"]


# ---------------------------------------------------------------------------
# AC2 — build_username_registry factory
# ---------------------------------------------------------------------------

class TestBuildUsernameRegistry:
    def test_factory_returns_registry_instance(self):
        with patch("Core.scrapers.registry.ScraperRegistry.build_username_registry") as m:
            mock_reg = MagicMock(spec=ScraperRegistry)
            m.return_value = mock_reg
            result = ScraperRegistry.build_username_registry(
                "report.txt", "john", [], [], [], [])
        assert result is mock_reg

    def test_factory_registers_19_scrapers(self):
        # Patch the Scraper import inside registry module using sys.modules trick
        import sys, types
        fake_scraper_info = MagicMock()
        fake_scraper_module = types.ModuleType("Scraper")
        fake_scraper_module.info = fake_scraper_info

        fake_username_pkg = types.ModuleType("Core.Support.Username")
        fake_username_pkg.Scraper = fake_scraper_module

        # Temporarily patch the local import inside build_username_registry
        original = sys.modules.get("Core.Support.Username.Scraper")
        sys.modules["Core.Support.Username.Scraper"] = fake_scraper_module
        try:
            reg = ScraperRegistry.build_username_registry(
                "report.txt", "alice", [], [], [], [])
        finally:
            if original is None:
                sys.modules.pop("Core.Support.Username.Scraper", None)
            else:
                sys.modules["Core.Support.Username.Scraper"] = original

        assert len(reg.registered_names()) == 19

    def test_factory_includes_instagram_and_twitter(self):
        import sys, types
        fake_info = MagicMock()
        fake_mod = types.ModuleType("Scraper")
        fake_mod.info = fake_info
        original = sys.modules.get("Core.Support.Username.Scraper")
        sys.modules["Core.Support.Username.Scraper"] = fake_mod
        try:
            reg = ScraperRegistry.build_username_registry(
                "r.txt", "alice", [], [], [], [])
        finally:
            if original is None:
                sys.modules.pop("Core.Support.Username.Scraper", None)
            else:
                sys.modules["Core.Support.Username.Scraper"] = original
        names = reg.registered_names()
        assert "Instagram" in names
        assert "Twitter" in names

    def test_factory_includes_all_expected_scrapers(self):
        import sys, types
        expected = {
            "Instagram", "Twitter", "TikTok", "GitHub", "GitLab",
            "Ngl.link", "Tellonym", "Gravatar", "JoinRoll", "Chess.com",
            "Minecraft", "Disqus", "Imgur", "Pr0gramm", "BinarySearch",
            "MixCloud", "DockerHub", "Kik", "Wattpad",
        }
        fake_mod = types.ModuleType("Scraper")
        fake_mod.info = MagicMock()
        original = sys.modules.get("Core.Support.Username.Scraper")
        sys.modules["Core.Support.Username.Scraper"] = fake_mod
        try:
            reg = ScraperRegistry.build_username_registry(
                "r.txt", "bob", [], [], [], [])
        finally:
            if original is None:
                sys.modules.pop("Core.Support.Username.Scraper", None)
            else:
                sys.modules["Core.Support.Username.Scraper"] = original
        assert set(reg.registered_names()) == expected
