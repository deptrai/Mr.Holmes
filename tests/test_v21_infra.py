"""Tests for v2.1 infrastructure: RateLimiter, BrowserPool, EvidenceStore schema."""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

import pytest


# ─── RateLimiter (AD-12) ──────────────────────────────────────────────────────

class TestRateLimiter:
    def test_singleton(self):
        from Core.utils.rate_limiter import RateLimiter
        a = RateLimiter.get_instance()
        b = RateLimiter.get_instance()
        assert a is b

    def test_domain_limit_enforced(self):
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        limiter.set_domain_limit("test.example.com", 0.5)

        async def _test():
            await limiter.wait_if_needed("test.example.com", "TestPlugin")
            t0 = time.monotonic()
            await limiter.wait_if_needed("test.example.com", "TestPlugin")
            elapsed = time.monotonic() - t0
            assert elapsed >= 0.4, f"Rate limit not enforced: {elapsed:.3f}s"

        asyncio.get_event_loop().run_until_complete(_test())

    def test_no_limit_for_unknown_domain(self):
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()

        async def _test():
            t0 = time.monotonic()
            await limiter.wait_if_needed("unknown.domain.xyz", "TestPlugin")
            elapsed = time.monotonic() - t0
            assert elapsed < 0.1, f"Should not wait for unknown domain: {elapsed:.3f}s"

        asyncio.get_event_loop().run_until_complete(_test())

    def test_can_request_non_blocking(self):
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        # Fresh domain should be requestable
        assert limiter.can_request("fresh.domain.xyz", "TestPlugin")


# ─── EvidenceStore v2.1 Schema (AD-13) ────────────────────────────────────────

class TestEvidenceStoreV21:
    def _get_store(self):
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["MH_EVIDENCE_DB"] = db_path
        from Core.evidence.store import EvidenceStore
        return EvidenceStore()

    def test_save_and_query_entities(self):
        store = self._get_store()
        inv_id = store.create_investigation("test@example.com", "EMAIL")
        ev_id = store.save_evidence(
            inv_id, "Holehe", "test@example.com", "EMAIL",
            {"registered": ["twitter.com"]}
        )
        saved = store.save_entities(ev_id, [
            {"entity_type": "EMAIL", "entity_value": "test@example.com", "confidence": 0.9},
            {"entity_type": "DOMAIN", "entity_value": "twitter.com", "confidence": 0.7},
        ])
        assert saved == 2

        entities = store.query_entities(inv_id)
        assert len(entities) == 2

        emails = store.query_entities(inv_id, "EMAIL")
        assert len(emails) == 1
        assert emails[0]["entity_value"] == "test@example.com"

    def test_save_and_query_cross_refs(self):
        store = self._get_store()
        inv_id = store.create_investigation("test@example.com", "EMAIL")
        ev1 = store.save_evidence(inv_id, "Holehe", "test@example.com", "EMAIL", {})
        ev2 = store.save_evidence(inv_id, "IntelX", "test@example.com", "EMAIL", {})

        ref_id = store.save_cross_ref(inv_id, ev1, ev2, "email", "test@example.com", 0.9)
        assert ref_id > 0

        refs = store.query_cross_refs(inv_id)
        assert len(refs) == 1
        assert refs[0]["match_type"] == "email"
        assert refs[0]["match_value"] == "test@example.com"


# ─── BrowserPool (AD-11) ──────────────────────────────────────────────────────

class TestBrowserPool:
    def test_singleton(self):
        from Core.browser.browser_pool import BrowserPool
        # Reset singleton for test isolation
        BrowserPool._instance = None
        try:
            pool = BrowserPool.get_instance()
            assert pool is not None
            assert pool is BrowserPool.get_instance()
        except RuntimeError:
            # Playwright not installed — skip
            pytest.skip("Playwright not installed")

    def test_stats(self):
        from Core.browser.browser_pool import BrowserPool
        BrowserPool._instance = None
        try:
            pool = BrowserPool.get_instance()
            stats = pool.get_stats()
            assert "max_browsers" in stats
            assert "active_contexts" in stats
            assert "initialized" in stats
        except RuntimeError:
            pytest.skip("Playwright not installed")
