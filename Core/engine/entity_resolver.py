"""
Core/engine/entity_resolver.py

Story 9.10 — EntityResolver: Golden Record builder.
Merges ProfileEntity objects from multiple sources using confidence-weighted
similarity (Jaro-Winkler for names, pHash for avatars).
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import aiohttp

from Core.models.profile_entity import ProfileEntity, SourcedField

logger = logging.getLogger(__name__)

# Module-level constants (P2: decoupled from class to avoid fragile reference)
_NAME_CONFIDENCE_BOOST: float = 0.1
_MAX_IMAGE_BYTES: int = 5 * 1024 * 1024  # 5 MB cap for avatar downloads


# ── Name similarity ────────────────────────────────────────────────────────────

def _names_similar(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    Jaro-Winkler similarity comparison.
    Falls back to exact match (case-insensitive) if jellyfish not installed.
    """
    try:
        import jellyfish
        return jellyfish.jaro_winkler_similarity(name1.lower(), name2.lower()) >= threshold
    except ImportError:
        return name1.lower().strip() == name2.lower().strip()


def _dedup_names_by_similarity(
    names: list[SourcedField],
    threshold: float = 0.85,
    confidence_boost: float = _NAME_CONFIDENCE_BOOST,
) -> list[SourcedField]:
    """
    Deduplicate real_names list by Jaro-Winkler similarity.

    When two names are similar (>= threshold):
    - Keep the value with higher confidence.
    - Boost the winner's confidence by confidence_boost (capped at 1.0).

    When names are dissimilar (< threshold):
    - Both are retained.
    """
    result: list[SourcedField] = []
    for candidate in names:
        matched = False
        for i, existing in enumerate(result):
            if _names_similar(candidate.value, existing.value, threshold):
                if candidate.confidence >= existing.confidence:
                    winner = SourcedField(
                        value=candidate.value,
                        source=candidate.source,
                        confidence=min(1.0, candidate.confidence + confidence_boost),
                    )
                else:
                    winner = SourcedField(
                        value=existing.value,
                        source=existing.source,
                        confidence=min(1.0, existing.confidence + confidence_boost),
                    )
                result[i] = winner
                matched = True
                break
        if not matched:
            result.append(candidate)
    return result


# ── Avatar pHash ───────────────────────────────────────────────────────────────

def _is_safe_url(url: str) -> bool:
    """P3: Validate URL scheme and reject private/loopback hosts."""
    import ipaddress
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except ValueError:
        pass  # hostname, not IP — acceptable
    return True


async def _avatar_hash(url: str, session: aiohttp.ClientSession):
    """
    Download image from url and compute perceptual hash.
    Returns None on any error (import failure, network error, decode error).
    P1: accepts shared session to avoid creating one per URL.
    P3: validates URL before fetching.
    P4: logs errors instead of silently swallowing.
    """
    if not _is_safe_url(url):
        logger.debug("_avatar_hash: rejecting unsafe URL: %s", url)
        return None
    try:
        import imagehash
        from PIL import Image
        import io
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.content_length and resp.content_length > _MAX_IMAGE_BYTES:
                logger.debug("_avatar_hash: image too large at %s (%d bytes)", url, resp.content_length)
                return None
            img_bytes = await resp.content.read(_MAX_IMAGE_BYTES)
        img = Image.open(io.BytesIO(img_bytes))
        return imagehash.phash(img)
    except (ImportError, aiohttp.ClientError, OSError) as exc:
        logger.debug("_avatar_hash failed for %s: %r", url, exc)
        return None
    except Exception as exc:
        logger.warning("_avatar_hash unexpected error for %s: %r", url, exc)
        return None


# ── EntityResolver ─────────────────────────────────────────────────────────────

class EntityResolver:
    """
    Golden Record builder.

    Merges a list of ProfileEntity objects (one per source/plugin) into a single
    unified ProfileEntity using:
    - Jaro-Winkler similarity for name deduplication (jellyfish, optional)
    - Perceptual hash (pHash) for avatar matching (imagehash + Pillow, optional)
    - Merge gate: only merges if ≥ 2 independent SourcedField sources (FR23)
    - Confidence threshold flagging (< 0.5 → "⚠ LOW_CONFIDENCE")
    """

    PHASH_THRESHOLD: int = 10          # pHash diff ≤ 10 → same image
    PHASH_CONFIDENCE_BOOST: float = 0.15
    NAME_CONFIDENCE_BOOST: float = _NAME_CONFIDENCE_BOOST
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

        # D1/Merge gate (FR23): require ≥ 2 independent SourcedField.source values
        all_sf_sources: set[str] = set()
        for e in entities:
            for fname in ProfileEntity._LIST_FIELDS:
                for sf in getattr(e, fname):
                    all_sf_sources.add(sf.source)
        # Filter out known flags from source count
        all_sf_sources.discard(self.LOW_CONFIDENCE_FLAG)
        if len(all_sf_sources) < 2:
            logger.debug("EntityResolver: < 2 independent SourcedField sources, skipping merge")
            return entities[0]

        # Collect ALL real_names BEFORE ProfileEntity.merge() deduplicates by exact value.
        all_names: list[SourcedField] = []
        for e in entities:
            all_names.extend(e.real_names)
        deduped_names = _dedup_names_by_similarity(
            all_names, self.NAME_SIMILARITY_THRESHOLD, self.NAME_CONFIDENCE_BOOST
        )

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
        else:
            # P7: no SourcedFields at all → confidence is 0.0
            merged.confidence = 0.0

        # P5: Low confidence flag stored separately from plugin sources
        # to avoid corrupting merge gate on re-resolve
        if merged.confidence < self.LOW_CONFIDENCE_THRESHOLD:
            if self.LOW_CONFIDENCE_FLAG not in merged.sources:
                merged.sources.append(self.LOW_CONFIDENCE_FLAG)

        return merged

    async def _apply_avatar_phash(self, entity: ProfileEntity) -> ProfileEntity:
        """
        Compare avatar images using perceptual hash.
        If two avatars match (pHash diff ≤ PHASH_THRESHOLD), boost ONLY the matched avatars.
        Silently skips on any error (missing deps, network failure, decode error).
        P1: Uses a single shared session for all avatar downloads.
        P6: Only boosts specific matched avatars, not all.
        """
        if len(entity.avatars) < 2:
            return entity

        # P1: Create one session for all avatar downloads
        try:
            async with aiohttp.ClientSession() as session:
                hashes = []
                for avatar in entity.avatars:
                    h = await _avatar_hash(avatar.value, session)
                    hashes.append(h)
        except Exception as exc:
            logger.debug("_apply_avatar_phash session error: %r", exc)
            return entity

        # P6: Find matching pairs and only boost those specific avatars
        boosted_indices: set[int] = set()
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                if hashes[i] is None or hashes[j] is None:
                    continue
                try:
                    diff = hashes[i] - hashes[j]  # Hamming distance, always >= 0
                    if diff <= self.PHASH_THRESHOLD:
                        boosted_indices.add(i)
                        boosted_indices.add(j)
                except Exception:
                    continue

        if boosted_indices:
            entity.avatars = [
                SourcedField(
                    value=a.value,
                    source=a.source,
                    confidence=min(1.0, a.confidence + self.PHASH_CONFIDENCE_BOOST)
                    if idx in boosted_indices else a.confidence,
                )
                for idx, a in enumerate(entity.avatars)
            ]

        return entity
