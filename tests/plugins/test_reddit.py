"""tests/plugins/test_reddit.py — Reddit plugin tests."""
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from Core.plugins.reddit import RedditPlugin

class TestRedditPlugin:
    def test_name(self):
        assert RedditPlugin().name == "Reddit"
    
    def test_no_api_key(self):
        assert RedditPlugin().requires_api_key is False
    
    def test_stage(self):
        assert RedditPlugin().stage == 2
    
    def test_wrong_target_type(self):
        p = RedditPlugin()
        result = asyncio.run(p.check("test", "email"))
        assert not result.is_success
    
    def test_user_not_found(self):
        p = RedditPlugin()
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status = 404
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = asyncio.run(p.check("nonexistentuser12345", "username"))
            assert not result.is_success
            assert "404" in result.error_message
