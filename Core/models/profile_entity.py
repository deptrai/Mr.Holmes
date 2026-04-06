"""
Core/models/profile_entity.py

Story 9.1 — ProfileEntity Data Model

Unified Golden Record dataclass để merge OSINT data từ nhiều nguồn
với confidence scoring. Là foundation cho Epic 9 entity resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class SourcedField:
    """
    Một giá trị data có gắn nguồn và mức độ tin cậy.

    __eq__ chỉ so sánh value (bỏ qua source/confidence) để
    set() có thể dedup theo value khi merge.
    """
    value: str
    source: str       # plugin name hoặc "auto:..." cho derived fields
    confidence: float  # 0.0 – 1.0

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SourcedField):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourcedField:
        return cls(
            value=data["value"],
            source=data["source"],
            confidence=float(data["confidence"]),
        )


def _dedup_sourced_fields(fields: list[SourcedField]) -> list[SourcedField]:
    """Deduplicate SourcedField list by value, preserving first-seen order."""
    seen: set[str] = set()
    result: list[SourcedField] = []
    for f in fields:
        if f.value not in seen:
            seen.add(f.value)
            result.append(f)
    return result


@dataclass
class ProfileEntity:
    """
    Golden Record — unified identity profile merged từ nhiều OSINT sources.

    Mỗi list field chứa SourcedField objects (value + source + confidence).
    Dùng merge() để combine 2 entities; to_dict()/from_dict() cho serialization.
    """

    seed: str       # input ban đầu (email/username/phone)
    seed_type: str  # "EMAIL" | "USERNAME" | "PHONE"

    # Identity fields
    real_names: list[SourcedField] = field(default_factory=list)
    emails: list[SourcedField] = field(default_factory=list)
    phones: list[SourcedField] = field(default_factory=list)
    usernames: list[SourcedField] = field(default_factory=list)
    locations: list[SourcedField] = field(default_factory=list)
    avatars: list[SourcedField] = field(default_factory=list)
    bios: list[SourcedField] = field(default_factory=list)

    # Structured fields
    platforms: dict[str, str] = field(default_factory=dict)    # {platform: profile_url}
    breach_sources: list[str] = field(default_factory=list)
    active_hours: dict[str, Any] = field(default_factory=dict)  # {"timezone": "UTC+7", "peak": "22:00-02:00"}

    # Meta
    confidence: float = 0.0  # overall confidence 0.0-1.0
    sources: list[str] = field(default_factory=list)  # plugin names that contributed

    # ── list field names used by merge/serialization ──────────────────────────
    _LIST_FIELDS: ClassVar[tuple[str, ...]] = (
        "real_names", "emails", "phones", "usernames",
        "locations", "avatars", "bios",
    )

    def merge(self, other: ProfileEntity) -> ProfileEntity:
        """
        Merge 2 ProfileEntity instances thành 1 Golden Record.

        - Dedup values trong mỗi list field
        - Merge platforms dict (no overwrite — first source wins)
        - Merge breach_sources (dedup)
        - Recalculate confidence = mean của tất cả SourcedField.confidence
        - Union sources lists
        """
        merged = ProfileEntity(seed=self.seed, seed_type=self.seed_type)

        # Merge list fields với dedup
        for fname in self._LIST_FIELDS:
            combined = getattr(self, fname) + getattr(other, fname)
            setattr(merged, fname, _dedup_sourced_fields(combined))

        # Merge platforms (no overwrite)
        merged.platforms = dict(self.platforms)
        for k, v in other.platforms.items():
            merged.platforms.setdefault(k, v)

        # Merge breach_sources (dedup, preserve order)
        seen_breaches: set[str] = set()
        for src in self.breach_sources + other.breach_sources:
            if src not in seen_breaches:
                seen_breaches.add(src)
                merged.breach_sources.append(src)

        # Merge active_hours (self wins on conflict)
        merged.active_hours = dict(other.active_hours)
        merged.active_hours.update(self.active_hours)

        # Union sources
        seen_sources: set[str] = set()
        for s in self.sources + other.sources:
            if s not in seen_sources:
                seen_sources.add(s)
                merged.sources.append(s)

        # Recalculate confidence = mean of all SourcedField.confidence
        all_fields: list[SourcedField] = []
        for fname in self._LIST_FIELDS:
            all_fields.extend(getattr(merged, fname))
        if all_fields:
            merged.confidence = sum(f.confidence for f in all_fields) / len(all_fields)

        return merged

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict representation."""
        result: dict[str, Any] = {
            "seed": self.seed,
            "seed_type": self.seed_type,
            "platforms": dict(self.platforms),
            "breach_sources": list(self.breach_sources),
            "active_hours": dict(self.active_hours),
            "confidence": self.confidence,
            "sources": list(self.sources),
        }
        for fname in self._LIST_FIELDS:
            result[fname] = [f.to_dict() for f in getattr(self, fname)]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileEntity:
        """Reconstruct ProfileEntity từ dict (e.g. từ JSON file)."""
        _LIST_FIELDS = (
            "real_names", "emails", "phones", "usernames",
            "locations", "avatars", "bios",
        )
        entity = cls(
            seed=data["seed"],
            seed_type=data["seed_type"],
        )
        for fname in _LIST_FIELDS:
            raw_list = data.get(fname, [])
            setattr(entity, fname, [SourcedField.from_dict(d) for d in raw_list])

        entity.platforms = dict(data.get("platforms", {}))
        entity.breach_sources = list(data.get("breach_sources", []))
        entity.active_hours = dict(data.get("active_hours", {}))
        entity.confidence = float(data.get("confidence", 0.0))
        entity.sources = list(data.get("sources", []))
        return entity
