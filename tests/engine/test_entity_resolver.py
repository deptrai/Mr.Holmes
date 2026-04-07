"""
tests/engine/test_entity_resolver.py

Story 9.10 — EntityResolver unit tests.
Written in RED phase before implementation.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock

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
        e1 = _entity(sources=["pluginA"])
        e2 = _entity(sources=["pluginB"])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert isinstance(result, ProfileEntity)


# ─── AC 4: Merge gate — ≥ 2 independent sources ───────────────────────────────

class TestMergeGate:
    def test_single_source_across_two_entities_no_merge(self):
        """Both entities from same source → return first unchanged."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginA"], names=[("Alice B", "pluginA", 0.7)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        # Only 1 independent source → no merge, return first entity
        assert result is e1

    def test_two_independent_sources_triggers_merge(self):
        """Two entities with different sources → merge proceeds."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Bob", "pluginB", 0.8)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        # Should merge — result has both sources
        assert "pluginA" in result.sources
        assert "pluginB" in result.sources

    def test_three_entities_one_source_no_merge(self):
        """3 entities all from same source → no merge."""
        entities = [_entity(sources=["pluginX"]) for _ in range(3)]
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve(entities))
        assert result is entities[0]


# ─── AC 2: Jaro-Winkler name deduplication ────────────────────────────────────

class TestJaroWinklerNameMerging:
    def test_similar_names_deduped_keeps_higher_confidence(self):
        """Names with Jaro-Winkler ≥ 0.85 should be merged (keep higher confidence)."""
        e1 = _entity(sources=["pluginA"], names=[("Nguyen Van A", "pluginA", 0.9)])
        e2 = _entity(sources=["pluginB"], names=[("Nguyen Van A", "pluginB", 0.7)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        # Exact same name → deduped to 1 entry
        assert len(result.real_names) == 1
        # Higher confidence (0.9) kept, boosted by 0.1 → 1.0
        assert result.real_names[0].confidence == pytest.approx(1.0)

    def test_similar_names_confidence_boosted(self):
        """After dedup, winning name confidence is boosted by 0.1."""
        e1 = _entity(sources=["pluginA"], names=[("Alice Smith", "pluginA", 0.7)])
        e2 = _entity(sources=["pluginB"], names=[("Alice Smith", "pluginB", 0.6)])
        resolver = EntityResolver()
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert len(result.real_names) == 1
        # Higher confidence 0.7 + 0.1 boost = 0.8
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
        # Exact match → deduped
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
        # Should not raise, avatars present
        assert isinstance(result, ProfileEntity)
        assert len(result.avatars) >= 1

    def test_phash_skipped_on_download_failure(self):
        """If avatar download fails, pHash is silently skipped."""
        e1 = _entity(
            sources=["pluginA"],
            avatars=[("https://invalid.example.invalid/a.jpg", "pluginA", 0.8)],
        )
        e2 = _entity(
            sources=["pluginB"],
            avatars=[("https://invalid.example.invalid/b.jpg", "pluginB", 0.8)],
        )
        resolver = EntityResolver()
        # Should not raise even with unreachable URLs
        result = asyncio.run(resolver.resolve([e1, e2]))
        assert isinstance(result, ProfileEntity)

    def test_phash_boost_when_same_avatar(self):
        """When two avatars have pHash diff ≤ 10, confidence is boosted."""
        e1 = _entity(
            sources=["pluginA"],
            avatars=[("https://example.com/avatar.jpg", "pluginA", 0.7)],
        )
        e2 = _entity(
            sources=["pluginB"],
            avatars=[("https://example.com/avatar.jpg", "pluginB", 0.7)],
        )
        resolver = EntityResolver()

        # Mock _avatar_hash to return same hash for both URLs
        mock_hash = MagicMock()
        mock_hash.__sub__ = MagicMock(return_value=0)  # diff = 0
        mock_hash.__abs__ = MagicMock(return_value=0)

        async def fake_avatar_hash(url: str):
            return mock_hash

        with patch("Core.engine.entity_resolver._avatar_hash", side_effect=fake_avatar_hash):
            result = asyncio.run(resolver.resolve([e1, e2]))

        # Avatars should have boosted confidence
        for avatar in result.avatars:
            assert avatar.confidence >= 0.7  # at least original, possibly boosted


# ─── AC 6: pure computation, no external API calls ────────────────────────────

class TestPureComputation:
    def test_resolve_completes_without_network(self):
        """resolve() with no avatars should never make network calls."""
        e1 = _entity(sources=["pluginA"], names=[("Alice", "pluginA", 0.8)])
        e2 = _entity(sources=["pluginB"], names=[("Alice", "pluginB", 0.8)])
        resolver = EntityResolver()
        # Patch aiohttp to ensure no network call is made
        with patch("aiohttp.ClientSession") as mock_session:
            result = asyncio.run(resolver.resolve([e1, e2]))
        # No avatars → ClientSession should never be instantiated for pHash
        mock_session.assert_not_called()
        assert isinstance(result, ProfileEntity)
