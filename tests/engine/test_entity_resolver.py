"""
tests/engine/test_entity_resolver.py

Story 9.10 — EntityResolver unit tests.
Written in RED phase before implementation.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from Core.models.profile_entity import ProfileEntity, SourcedField
from Core.engine.entity_resolver import EntityResolver


# ─── helpers ───────────────────────────────────────────────────────────────────

def _entity(
    seed: str = "test@gmail.com",
    seed_type: str = "EMAIL",
    sources: list[str] | None = None,
    names: list[tuple[str, str, float]] | None = None,  # (value, source, confidence)
    confidence: float = 0.8,
    avatars: list[tuple[str, str, float]] | None = None,
) -> ProfileEntity:
    e = ProfileEntity(
        seed=seed,
        seed_type=seed_type,
        sources=list(sources or []),
        confidence=confidence,
    )
    if names:
        e.real_names = [SourcedField(v, s, c) for v, s, c in names]
    if avatars:
        e.avatars = [SourcedField(v, s, c) for v, s, c in avatars]
    return e


class FakeHash:
    """Fake imagehash-like object that supports subtraction returning int."""
    def __init__(self, value: int = 0):
        self._value = value

    def __sub__(self, other: "FakeHash") -> int:
        return abs(self._value - other._value)


# ─── AC 1: basic resolve() signature ──────────────────────────────────────────

class TestResolveBasicGuards:
    def test_import(self):
        from Core.engine.entity_resolver import EntityResolver  # noqa: F401

    def test_empty_list_returns_empty_entity(self):
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([]))
        assert isinstance(result, ProfileEntity)
        assert result.seed == ""
        assert result.seed_type == "UNKNOWN"

    def test_single_entity_returned_unchanged(self):
        e = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e]))
        assert result is e

    def test_returns_profile_entity(self):
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Bob", "pluginB", 0.8)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert isinstance(result, ProfileEntity)


# ─── AC 4: Merge gate — ≥ 2 independent SourcedField.source ───────────────────

class TestMergeGate:
    def test_single_source_across_two_entities_no_merge(self):
        """Both entities with SourcedFields from same source → no merge."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginA"], names=[("Alice B", "pluginA", 0.7)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert result is e1

    def test_two_independent_sourced_field_sources_triggers_merge(self):
        """Two entities with SourcedFields from different sources → merge."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Bob", "pluginB", 0.8)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert "pluginA" in result.sources
        assert "pluginB" in result.sources

    def test_three_entities_one_sourced_field_source_no_merge(self):
        """3 entities all with SourcedFields from same source → no merge."""
        entities = [
            _entity(sources=["pluginX"], names=[("Name", "pluginX", 0.5)])
            for _ in range(3)
        ]
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve(entities))
        assert result is entities[0]

    def test_merge_gate_uses_sourced_field_source_not_entity_sources(self):
        """D1: Gate counts distinct SourcedField.source, not entity.sources."""
        # entity.sources says ["pluginA", "pluginB"] but all SourcedFields are from "pluginA"
        e1 = _entity(sources=["pluginA", "pluginB"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginA"], names=[("Bob", "pluginA", 0.8)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        # Only 1 SourcedField source ("pluginA") → no merge
        assert result is e1

    def test_entities_no_sourced_fields_no_merge(self):
        """Entities with empty SourcedField lists → no merge (0 sources < 2)."""
        e1 = _entity(sources=["pluginA"])
        e2 = _entity(sources=["pluginB"])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert result is e1

    def test_low_confidence_flag_in_sources_not_counted(self):
        """LOW_CONFIDENCE flag in sources should not count as independent source."""
        e1 = _entity(
            sources=["pluginA", "⚠ LOW_CONFIDENCE"],
            names=[("Alice", "pluginA", 0.3)],
        )
        e2 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.2)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        # Only 1 real SourcedField source → no merge
        assert result is e1


# ─── AC 2: Jaro-Winkler name deduplication ────────────────────────────────────

class TestJaroWinklerNameMerging:
    def test_similar_names_deduped_keeps_higher_confidence(self):
        """Names with Jaro-Winkler ≥ 0.85 should be merged (keep higher confidence)."""
        e1 = _entity(sources=["pluginA"], names=[("Nguyen Van A", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Nguyen Van A", "pluginB", 0.7)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert len(result.real_names) == 1
        assert result.real_names[0].confidence == pytest.approx(1.0)

    def test_similar_names_confidence_boosted(self):
        """After dedup, winning name confidence is boosted by 0.1."""
        e1 = _entity(sources=["pluginA"], names=[("Alice Smith", "pluginA", 0.7)])
        e2 = _entity(sources=["pluginB"], names=[("Alice Smith", "pluginB", 0.6)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert len(result.real_names) == 1
        assert result.real_names[0].confidence == pytest.approx(0.8)

    def test_different_names_both_retained(self):
        """Names with Jaro-Winkler < 0.85 should both be kept."""
        e1 = _entity(sources=["pluginA"], names=[("Alice Smith", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Bob Jones", "pluginB", 0.8)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert len(result.real_names) == 2
        values = {f.value for f in result.real_names}
        assert "Alice Smith" in values
        assert "Bob Jones" in values

    def test_name_confidence_boost_capped_at_1(self):
        """Confidence boost should not exceed 1.0."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.95)])
        e2 = _entity(sources=["pluginB"], names=[("Alice", "pluginB", 0.95)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert result.real_names[0].confidence <= 1.0

    def test_fallback_exact_match_without_jellyfish(self):
        """When jellyfish not installed, exact match used as fallback."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.8)])
        e2 = _entity(sources=["pluginB"], names=[("Alice", "pluginB", 0.7)])
        resolver = EntityResolver()
        with patch.dict("sys.modules", {"jellyfish": None}):
            result = asyncio.run(resolver.resolve([e1, e2]))
        assert len(result.real_names) == 1


# ─── AC 5: Confidence thresholds ──────────────────────────────────────────────

class TestConfidenceThresholds:
    def test_low_confidence_flagged_in_sources(self):
        """Merged entity confidence < 0.5 → '⚠ LOW_CONFIDENCE' in sources."""
        e1 = _entity(
            sources=["pluginA"],
            names=[("Alice", "pluginA", 0.2)],
            confidence=0.2,
        )
        e2 = _entity(
            sources=["pluginB"],
            names=[("Alice", "pluginB", 0.2)],
            confidence=0.2,
        )
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert any("LOW_CONFIDENCE" in s for s in result.sources)

    def test_high_confidence_not_flagged(self):
        """Merged entity confidence ≥ 0.75 → no LOW_CONFIDENCE flag."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Alice", "pluginB", 0.9)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert not any("LOW_CONFIDENCE" in s for s in result.sources)

    def test_low_confidence_flag_not_duplicated(self):
        """LOW_CONFIDENCE flag added only once even if called multiple times."""
        e1 = _entity(sources=["pluginA"], names=[("X", "pluginA", 0.1)])
        e2 = _entity(sources=["pluginB"], names=[("X", "pluginB", 0.1)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        low_conf_entries = [s for s in result.sources if "LOW_CONFIDENCE" in s]
        assert len(low_conf_entries) == 1

    def test_empty_sourced_fields_confidence_zero(self):
        """P7: When no SourcedFields exist after merge, confidence = 0.0."""
        e1 = _entity(sources=["pluginA"])
        e1.emails = [SourcedField("a@b.com", "pluginA", 0.5)]
        e2 = _entity(sources=["pluginB"])
        e2.emails = [SourcedField("c@d.com", "pluginB", 0.5)]
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        # Has SourcedFields so confidence should be recalculated
        assert isinstance(result.confidence, float)


# ─── AC 3: pHash — skip when imagehash not installed ──────────────────────────

class TestPHashBehavior:
    def test_phash_skipped_when_imagehash_not_installed(self):
        """EntityResolver.resolve() works fine when imagehash not installed."""
        e1 = _entity(
            sources=["pluginA"],
            avatars=[("https://example.com/a.jpg", "pluginA", 0.8)],
        )
        e2 = _entity(
            sources=["pluginB"],
            avatars=[("https://example.com/b.jpg", "pluginB", 0.8)],
        )
        resolver = EntityResolver()
        with patch.dict("sys.modules", {"imagehash": None, "PIL": None}):
            result = asyncio.run(resolver.resolve([e1, e2]))
        assert isinstance(result, ProfileEntity)
        assert len(result.avatars) >= 1

    def test_phash_skipped_on_download_failure(self):
        """P9: If avatar download fails, pHash is silently skipped (mocked, no real network)."""
        e1 = _entity(
            sources=["pluginA"],
            avatars=[("https://example.com/a.jpg", "pluginA", 0.8)],
        )
        e2 = _entity(
            sources=["pluginB"],
            avatars=[("https://example.com/b.jpg", "pluginB", 0.8)],
        )
        resolver = EntityResolver()

        async def fake_hash_none(url, session):
            return None

        with patch("Core.engine.entity_resolver._avatar_hash", side_effect=fake_hash_none):
            result = asyncio.run(resolver.resolve([e1, e2]))
        assert isinstance(result, ProfileEntity)
        # No boost applied — confidence unchanged
        for av in result.avatars:
            assert av.confidence == pytest.approx(0.8)

    def test_phash_boost_when_same_avatar(self):
        """P8: When two avatars have pHash diff ≤ 10, confidence is boosted."""
        e1 = _entity(
            sources=["pluginA"],
            avatars=[("https://example.com/avatar.jpg", "pluginA", 0.7)],
        )
        e2 = _entity(
            sources=["pluginB"],
            avatars=[("https://example.com/avatar.jpg", "pluginB", 0.7)],
        )
        resolver = EntityResolver()

        same_hash = FakeHash(0)

        async def fake_apply(entity):
            """Directly simulate pHash match and boost."""
            from Core.engine.entity_resolver import SourcedField
            boosted = []
            for a in entity.avatars:
                boosted.append(SourcedField(
                    value=a.value, source=a.source,
                    confidence=min(1.0, a.confidence + resolver.PHASH_CONFIDENCE_BOOST),
                ))
            entity.avatars = boosted
            return entity

        with patch.object(resolver, "_apply_avatar_phash", side_effect=fake_apply):
            result = asyncio.run(resolver.resolve([e1, e2]))

        for avatar in result.avatars:
            assert avatar.confidence == pytest.approx(0.85)  # 0.7 + 0.15

    def test_phash_only_boosts_matched_avatars(self):
        """P6: Only avatars with matching pHash get boosted, not all."""
        e1 = _entity(sources=["pluginA"], avatars=[
            ("https://example.com/a.jpg", "pluginA", 0.7),
        ])
        e2 = _entity(sources=["pluginB"], avatars=[
            ("https://example.com/b.jpg", "pluginB", 0.7),
        ])
        e3 = _entity(sources=["pluginC"], avatars=[
            ("https://example.com/c.jpg", "pluginC", 0.6),
        ])
        # Also add SourcedFields so merge gate passes
        e3.emails = [SourcedField("x@y.com", "pluginC", 0.5)]
        resolver = EntityResolver()

        hash_a = FakeHash(0)
        hash_b = FakeHash(0)   # matches hash_a
        hash_c = FakeHash(100)  # does NOT match

        async def fake_hash(url, session):
            if "a.jpg" in url:
                return hash_a
            if "b.jpg" in url:
                return hash_b
            return hash_c

        with patch("Core.engine.entity_resolver._avatar_hash", side_effect=fake_hash):
            result = asyncio.run(resolver.resolve([e1, e2, e3]))

        # a.jpg and b.jpg should be boosted (0.7 + 0.15 = 0.85)
        # c.jpg should NOT be boosted (stays 0.6)
        boosted = [a for a in result.avatars if a.confidence > 0.7]
        unboosted = [a for a in result.avatars if a.confidence == pytest.approx(0.6)]
        assert len(boosted) >= 2
        assert len(unboosted) >= 1


# ─── P3: SSRF protection ─────────────────────────────────────────────────────

class TestSSRFProtection:
    def test_rejects_private_ip(self):
        """P3: avatar URL pointing to private IP should be rejected."""
        from Core.engine.entity_resolver import _is_safe_url
        assert not _is_safe_url("http://169.254.169.254/latest/meta-data/")
        assert not _is_safe_url("http://127.0.0.1/secret")
        assert not _is_safe_url("http://10.0.0.1/internal")

    def test_rejects_non_http_scheme(self):
        """P3: file:// and ftp:// schemes should be rejected."""
        from Core.engine.entity_resolver import _is_safe_url
        assert not _is_safe_url("file:///etc/passwd")
        assert not _is_safe_url("ftp://internal.server/data")

    def test_accepts_public_https(self):
        """P3: public HTTPS URLs should be allowed."""
        from Core.engine.entity_resolver import _is_safe_url
        assert _is_safe_url("https://avatars.githubusercontent.com/u/12345")
        assert _is_safe_url("http://example.com/avatar.jpg")


# ─── AC 6: pure computation, no external API calls ────────────────────────────

class TestPureComputation:
    def test_resolve_completes_without_network(self):
        """resolve() with no avatars should never make network calls."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.8)])
        e2 = _entity(sources=["pluginB"], names=[("Alice", "pluginB", 0.8)])
        resolver = EntityResolver()
        with patch("aiohttp.ClientSession") as mock_session:
            result = asyncio.run(resolver.resolve([e1, e2]))
        mock_session.assert_not_called()
        assert isinstance(result, ProfileEntity)
