"""
tests/proxy/test_proxy_manager.py

Unit tests for ProxyManager — Story 1.5.
AC6: Mock ip-api.com response, verify configure/get_proxy/get_identity/reset.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call

from Core.proxy.manager import ProxyManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_urlopen(region="Hanoi", country="Vietnam"):
    """Return a mock context-manager for urllib.request.urlopen."""
    payload = json.dumps({
        "regionName": region,
        "country": country,
    }).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_mock_proxies(ip="192.168.1.1"):
    """Return a mock Proxies module."""
    mock_proxy = MagicMock()
    mock_proxy.choice3 = ip
    mock_proxy.final_proxis = {"http": "//"+ip, "https": "//"+ip}
    mock_proxies = MagicMock()
    mock_proxies.proxy = mock_proxy
    return mock_proxies


# ---------------------------------------------------------------------------
# configure() — AC3
# ---------------------------------------------------------------------------

class TestConfigure:
    def test_choice_1_enables_proxy(self):
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("10.0.0.1")
        mock_resp = _make_mock_urlopen()

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)

        assert pm.is_enabled() is True

    def test_choice_2_disables_proxy(self):
        pm = ProxyManager()
        pm.configure(2)
        assert pm.is_enabled() is False

    def test_choice_0_disables_proxy(self):
        pm = ProxyManager()
        pm.configure(0)
        assert pm.is_enabled() is False

    def test_configure_resets_state_on_second_call(self):
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("1.2.3.4")
        mock_resp = _make_mock_urlopen()

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)
        assert pm.is_enabled() is True

        pm.configure(2)
        assert pm.is_enabled() is False
        assert pm.get_proxy() is None


# ---------------------------------------------------------------------------
# get_proxy() — AC3
# ---------------------------------------------------------------------------

class TestGetProxy:
    def test_returns_dict_when_enabled(self):
        pm = ProxyManager()
        from Core.Support import Proxies  # ensure module imported
        expected_dict = {"http": "//5.5.5.5", "https": "//5.5.5.5"}
        mock_resp = _make_mock_urlopen()

        with patch.object(Proxies.proxy, "choice3", "5.5.5.5"), \
             patch.object(Proxies.proxy, "final_proxis", expected_dict), \
             patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
            pm.configure(1)
            result = pm.get_proxy()

        assert result == expected_dict

    def test_returns_none_when_disabled(self):
        pm = ProxyManager()
        pm.configure(2)
        assert pm.get_proxy() is None

    def test_returns_none_before_configure(self):
        pm = ProxyManager()
        assert pm.get_proxy() is None


# ---------------------------------------------------------------------------
# get_identity() — AC3 / AC4
# ---------------------------------------------------------------------------

class TestGetIdentity:
    def test_returns_identity_string_when_proxy_enabled(self):
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("8.8.8.8")
        mock_resp = _make_mock_urlopen(region="California", country="United States")

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)

        identity = pm.get_identity()
        # Identity string must contain region and country info
        assert identity is not None
        assert "California" in identity or "United States" in identity

    def test_returns_none_when_disabled(self):
        pm = ProxyManager()
        pm.configure(2)
        assert pm.get_identity() is None

    def test_ip_api_failure_returns_none_not_raises(self):
        """ip-api failure must NOT propagate — returns None gracefully."""
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("9.9.9.9")

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen",
                       side_effect=OSError("network down")):
                pm.configure(1)

        assert pm.get_identity() is None

    def test_ip_api_bad_json_returns_none(self):
        """Malformed JSON from ip-api must return None gracefully."""
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("9.9.9.9")
        bad_resp = MagicMock()
        bad_resp.read.return_value = b"not-json!!!"
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=bad_resp):
                pm.configure(1)

        assert pm.get_identity() is None


# ---------------------------------------------------------------------------
# reset() — AC3
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_disables_proxy(self):
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("1.1.1.1")
        mock_resp = _make_mock_urlopen()

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)

        assert pm.is_enabled() is True
        pm.reset()
        assert pm.is_enabled() is False
        assert pm.get_proxy() is None

    def test_reset_preserves_identity_cache(self):
        """Identity is still accessible after reset (useful for logging)."""
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("2.2.2.2")
        mock_resp = _make_mock_urlopen(region="Tokyo", country="Japan")

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)

        pm.reset()
        # Identity cache retained for logging/recap purposes
        identity = pm.get_identity()
        assert identity is not None


# ---------------------------------------------------------------------------
# is_enabled() — convenience
# ---------------------------------------------------------------------------

class TestIsEnabled:
    def test_false_on_init(self):
        assert ProxyManager().is_enabled() is False

    def test_true_after_choice_1(self):
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("3.3.3.3")
        mock_resp = _make_mock_urlopen()
        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)
        assert pm.is_enabled() is True

    def test_false_after_reset(self):
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("4.4.4.4")
        mock_resp = _make_mock_urlopen()
        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
                pm.configure(1)
        pm.reset()
        assert pm.is_enabled() is False


# ---------------------------------------------------------------------------
# proxy_ip property — D3 fix
# ---------------------------------------------------------------------------

class TestProxyIp:
    def test_proxy_ip_returns_none_string_before_configure(self):
        pm = ProxyManager()
        assert pm.proxy_ip == "None"

    def test_proxy_ip_returns_ip_string_when_configured(self):
        pm = ProxyManager()
        from Core.Support import Proxies  # ensure module imported
        mock_resp = _make_mock_urlopen()
        with patch.object(Proxies.proxy, "choice3", "7.7.7.7"), \
             patch.object(Proxies.proxy, "final_proxis", {}), \
             patch("Core.proxy.manager.urllib.request.urlopen", return_value=mock_resp):
            pm.configure(1)
            assert pm.proxy_ip == "7.7.7.7"

    def test_proxy_ip_none_string_when_choice_2(self):
        pm = ProxyManager()
        pm.configure(2)
        assert pm.proxy_ip == "None"


# ---------------------------------------------------------------------------
# Edge cases — P2 + P3
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_configure_with_string_raises_or_handles(self):
        """P2: configure() with non-int should not corrupt state."""
        pm = ProxyManager()
        # Non-int choice goes to else branch (not 1), so result = disabled
        pm.configure("invalid")
        assert pm.is_enabled() is False
        assert pm.get_proxy() is None

    def test_configure_with_none_disables(self):
        pm = ProxyManager()
        pm.configure(None)
        assert pm.is_enabled() is False

    def test_urlopen_called_with_timeout(self):
        """P3: Verify that urlopen is called with timeout=10."""
        pm = ProxyManager()
        mock_proxies = _make_mock_proxies("6.6.6.6")
        mock_resp = _make_mock_urlopen()

        with patch.dict("sys.modules", {"Core.Support.Proxies": mock_proxies}):
            with patch("Core.proxy.manager.urllib.request.urlopen",
                       return_value=mock_resp) as mock_urlopen:
                pm.configure(1)

        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args
        assert call_args[1].get("timeout") == 10 or \
               (len(call_args[0]) > 1 and call_args[0][1] == 10), \
               "urlopen must be called with timeout=10"
