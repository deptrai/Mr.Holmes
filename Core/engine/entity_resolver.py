"""
Core/engine/entity_resolver.py

Story 9.10 — EntityResolver: Golden Record builder.
Merges ProfileEntity objects from multiple sources using confidence-weighted
similarity (Jaro-Winkler for names, pHash for avatars).
"""
from __future__ import annotations

import logging

from Core.models.profile_entity import ProfileEntity, SourcedField

logger = logging.getLogger(__name__)


# ── Name similarity ────────────────────────────────────────────────────────────

def _names_similar(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    Jaro-Winkler similarity comparison.
    Falls back to exact match (case-insensitive) if jellyfish not installed.
    """
    try:
        import jellyfish
        return jellyfish.jaro_winkler_similarity(name1.lower(), name2.lower()) >= threshold
    except (ImportError, TypeError):
        return name1.lower().strip() == name2.lower().strip()


def _dedup_names_by_similarity(
    names: list[SourcedField], threshold: float = 0.85
) -> list[SourcedField]:
    """
    Deduplicate real_names list by Jaro-Winkler similarity.

    When two names are similar (>= threshold):
    - Keep the value with higher confidence.
    - Boost the winner's confidence by 0.1 (capped at 1.0).

    When names are dissimilar (< threshold):
    - Both are retained.
    """
    result: list[SourcedField] = []
    for candidate in names:
        matched = False
        for i, existing in enumerate(result):
            if _names_similar(candidate.value, existing.value, threshold):
                # Keep higher confidence, boost by NAME_CONFIDENCE_BOOST
                if candidate.confidence >= existing.confidence:
                    winner = SourcedField(
                        value=candidate.value,
                        source=candidate.source,
                        confidence=min(1.0, candidate.confidence + EntityResolver.NAME_CONFIDENCE_BOOST),
                    )
                else:
                    winner = SourcedField(
                        value=existing.value,
                        source=existing.source,
                        confidence=min(1.0, existing.confidence + EntityResolver.NAME_CONFIDENCE_BOOST),
                    )
                result[i] = winner
                matched = True
                break
        if not matched:
            result.append(candidate)
    return result


# ── Avatar pHash ───────────────────────────────────────────────────────────────

async def _avatar_hash(url: str):
    """
    Download image from url and compute perceptual hash.
    Returns None on any error (import failure, network error, decode error).
    """
    try:
        import imagehash
        from PIL import Image
        import io
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                img_bytes = await resp.read()
        img = Image.open(io.BytesIO(img_bytes))
        return imagehash.phash(img)
    except Exception:
        return None


# ── EntityResolver ─────────────────────────────────────────────────────────────

class EntityResolver:
    """
    Golden Record builder.

    Merges a list of ProfileEntity objects (one per source/plugin) into a single
    unified ProfileEntity using:
    - Jaro-Winkler similarity for name deduplication (jellyfish, optional)
    - Perceptual hash (pHash) for avatar matching (imagehash + Pillow, optional)
    - Merge gate: only merges if ≥ 2 independent sources (FR23)
    - Confidence threshold flagging (< 0.5 → "⚠ LOW_CONFIDENCE")
    """

    PHASH_THRESHOLD: int = 10          # pHash diff ≤ 10 → same image
    PHASH_CONFIDENCE_BOOST: float = 0.15
    NAME_CONFIDENCE_BOOST: float = 0.1
    NAME_SIMILARITY_THRESHOLD: float = 0.85
    LOW_CONFIDENCE_THRESHOLD: float = 0.5
    LOW_CONFIDENCE_FLAG: str = "⚠ LOW_CONFIDENCE"

    async def resolve(self, entities: list[ProfileEntity]) -> ProfileEntity:
        """
        Merge list of ProfileEntity → 1 Golden Record.

        Args:
            entities: ProfileEntity objects, one per source/plugin.

        Returns:
            Single merged ProfileEntity with deduplication and confidence scoring.
        """
        # Guard: empty input
        if not entities:
            return ProfileEntity(seed="", seed_type="UNKNOWN")

        # Guard: single entity — return as-is, no merge
        if len(entities) == 1:
            return entities[0]

        # Merge gate (FR23): require ≥ 2 independent sources
        all_sources: set[str] = set()
        for e in entities:
            all_sources.update(e.sources)
        if len(all_sources) < 2:
            logger.debug("EntityResolver: only 1 independent source, skipping merge")
            return entities[0]

        # Collect ALL real_names BEFORE ProfileEntity.merge() deduplicates by exact value.
        # This allows Jaro-Winkler to see both "Alice Smith" (0.9) and "Alice Smith" (0.7)
        # and apply the confidence boost before they collapse into one.
        all_names: list[SourcedField] = []
        for e in entities:
            all_names.extend(e.real_names)
        deduped_names = _dedup_names_by_similarity(all_names, self.NAME_SIMILARITY_THRESHOLD)

        # Merge all entities using ProfileEntity.merge()
        merged = entities[0]
        for other in entities[1:]:
            merged = merged.merge(other)

        # Override real_names with our similarity-deduped+boosted version
        merged.real_names = deduped_names

        # Post-merge: pHash avatar comparison (may boost avatar confidence)
        merged = await self._apply_avatar_phash(merged)

        # Recalculate confidence after post-processing (name dedup may have changed scores)
        all_fields: list[SourcedField] = []
        for fname in ProfileEntity._LIST_FIELDS:
            all_fields.extend(getattr(merged, fname))
        if all_fields:
            merged.confidence = sum(f.confidence for f in all_fields) / len(all_fields)

        # Low confidence flagging (AC 5)
        if merged.confidence < self.LOW_CONFIDENCE_THRESHOLD:
            if self.LOW_CONFIDENCE_FLAG not in merged.sources:
                merged.sources.append(self.LOW_CONFIDENCE_FLAG)

        return merged

    async def _apply_avatar_phash(self, entity: ProfileEntity) -> ProfileEntity:
        """
        Compare avatar images using perceptual hash.
        If two avatars match (pHash diff ≤ PHASH_THRESHOLD), boost their confidence.
        Silently skips on any error (missing deps, network failure, decode error).
        """
        if len(entity.avatars) < 2:
            return entity

        # Compute hashes for all avatar URLs
        hashes = []
        for avatar in entity.avatars:
            h = await _avatar_hash(avatar.value)
            hashes.append(h)

        # Find any matching pair
        boost = False
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                if hashes[i] is None or hashes[j] is None:
                    continue
                try:
                    diff = abs(hashes[i] - hashes[j])
                    if diff <= self.PHASH_THRESHOLD:
                        boost = True
                except Exception:
                    continue

        if boost:
            entity.avatars = [
                SourcedField(
                    value=a.value,
                    source=a.source,
                    confidence=min(1.0, a.confidence + self.PHASH_CONFIDENCE_BOOST),
                )
                for a in entity.avatars
            ]

        return entity
