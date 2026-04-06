"""
tests/models/test_profile_entity.py

Unit tests cho ProfileEntity và SourcedField dataclasses (Story 9.1).
"""
from __future__ import annotations

import pytest

from Core.models.profile_entity import ProfileEntity, SourcedField


# ─────────────────────────────────────────────────────────────────────────────
# SourcedField tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSourcedField:
    def test_basic_creation(self):
        field = SourcedField(value="Nguyen Van A", source="Maigret", confidence=0.85)
        assert field.value == "Nguyen Van A"
        assert field.source == "Maigret"
        assert field.confidence == 0.85

    def test_eq_by_value_only(self):
        """__eq__ compares only value, ignoring source and confidence."""
        f1 = SourcedField(value="test@email.com", source="PluginA", confidence=0.9)
        f2 = SourcedField(value="test@email.com", source="PluginB", confidence=0.5)
        assert f1 == f2

    def test_neq_different_value(self):
        f1 = SourcedField(value="alice@email.com", source="PluginA", confidence=0.9)
        f2 = SourcedField(value="bob@email.com", source="PluginA", confidence=0.9)
        assert f1 != f2

    def test_hashable_by_value(self):
        """Can be used in set() for deduplication by value."""
        f1 = SourcedField(value="name", source="A", confidence=0.8)
        f2 = SourcedField(value="name", source="B", confidence=0.6)
        f3 = SourcedField(value="other", source="A", confidence=0.9)
        result = set([f1, f2, f3])
        assert len(result) == 2  # f1 and f2 are duplicates by value

    def test_eq_with_non_sourced_field(self):
        f = SourcedField(value="x", source="A", confidence=1.0)
        assert f.__eq__("x") == NotImplemented


# ─────────────────────────────────────────────────────────────────────────────
# ProfileEntity basic tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProfileEntityBasic:
    def test_creation_with_seed(self):
        entity = ProfileEntity(seed="test@gmail.com", seed_type="EMAIL")
        assert entity.seed == "test@gmail.com"
        assert entity.seed_type == "EMAIL"
        assert entity.confidence == 0.0
        assert entity.sources == []

    def test_default_mutable_fields(self):
        """Each instance gets independent mutable defaults."""
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2 = ProfileEntity(seed="c@d.com", seed_type="EMAIL")
        e1.real_names.append(SourcedField(value="Alice", source="P1", confidence=0.9))
        assert len(e2.real_names) == 0

    def test_all_list_fields_default_empty(self):
        entity = ProfileEntity(seed="user", seed_type="USERNAME")
        assert entity.real_names == []
        assert entity.emails == []
        assert entity.phones == []
        assert entity.usernames == []
        assert entity.locations == []
        assert entity.avatars == []
        assert entity.bios == []
        assert entity.breach_sources == []

    def test_platforms_dict_default_empty(self):
        entity = ProfileEntity(seed="user", seed_type="USERNAME")
        assert entity.platforms == {}
        assert entity.active_hours == {}


# ─────────────────────────────────────────────────────────────────────────────
# merge() tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProfileEntityMerge:
    def test_merge_deduplicates_list_fields(self):
        """Same value from different sources → deduplicated in merged entity."""
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.real_names.append(SourcedField(value="Alice", source="Maigret", confidence=0.8))
        e1.sources.append("Maigret")

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2.real_names.append(SourcedField(value="Alice", source="GitHub", confidence=0.9))
        e2.sources.append("GitHub")

        merged = e1.merge(e2)
        assert len(merged.real_names) == 1
        assert merged.real_names[0].value == "Alice"

    def test_merge_keeps_different_values(self):
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.real_names.append(SourcedField(value="Alice", source="A", confidence=0.8))

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2.real_names.append(SourcedField(value="Nguyen Van A", source="B", confidence=0.7))

        merged = e1.merge(e2)
        assert len(merged.real_names) == 2

    def test_merge_confidence_averaging(self):
        """Overall confidence = mean of all SourcedField.confidence in merged entity."""
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.real_names.append(SourcedField(value="Alice", source="A", confidence=0.8))
        e1.emails.append(SourcedField(value="a@b.com", source="A", confidence=0.6))

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2.phones.append(SourcedField(value="+84123456789", source="B", confidence=1.0))

        merged = e1.merge(e2)
        # mean(0.8, 0.6, 1.0) = 2.4 / 3 = 0.8
        assert abs(merged.confidence - 0.8) < 0.001

    def test_merge_empty_entity(self):
        """Merging with empty entity returns non-empty entity unchanged."""
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.real_names.append(SourcedField(value="Alice", source="A", confidence=0.9))
        e1.sources.append("PluginA")

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")  # empty

        merged = e1.merge(e2)
        assert len(merged.real_names) == 1
        assert "PluginA" in merged.sources

    def test_merge_sources_union(self):
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.sources = ["HIBP", "Holehe"]

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2.sources = ["Holehe", "Maigret"]  # "Holehe" is duplicate

        merged = e1.merge(e2)
        assert set(merged.sources) == {"HIBP", "Holehe", "Maigret"}

    def test_merge_platforms_union(self):
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.platforms = {"github": "https://github.com/alice"}

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2.platforms = {"instagram": "https://instagram.com/alice", "github": "https://github.com/alice2"}

        merged = e1.merge(e2)
        # "github" from e1 takes precedence (no overwrite), instagram added
        assert "github" in merged.platforms
        assert merged.platforms["github"] == "https://github.com/alice"
        assert "instagram" in merged.platforms

    def test_merge_breach_sources_dedup(self):
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e1.breach_sources = ["Adobe", "LinkedIn"]

        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2.breach_sources = ["LinkedIn", "Dropbox"]  # LinkedIn duplicate

        merged = e1.merge(e2)
        assert sorted(merged.breach_sources) == ["Adobe", "Dropbox", "LinkedIn"]

    def test_merge_no_fields_confidence_zero(self):
        """Two empty entities → confidence stays 0.0."""
        e1 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        e2 = ProfileEntity(seed="a@b.com", seed_type="EMAIL")
        merged = e1.merge(e2)
        assert merged.confidence == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# to_dict() / from_dict() roundtrip tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProfileEntitySerialization:
    def _make_entity(self) -> ProfileEntity:
        e = ProfileEntity(seed="test@gmail.com", seed_type="EMAIL")
        e.real_names.append(SourcedField(value="Alice", source="Maigret", confidence=0.85))
        e.emails.append(SourcedField(value="test@gmail.com", source="HIBP", confidence=1.0))
        e.platforms = {"github": "https://github.com/alice"}
        e.breach_sources = ["Adobe", "Canva"]
        e.confidence = 0.85
        e.sources = ["Maigret", "HIBP"]
        return e

    def test_to_dict_is_json_serializable(self):
        import json
        entity = self._make_entity()
        d = entity.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_to_dict_sourced_fields_are_dicts(self):
        entity = self._make_entity()
        d = entity.to_dict()
        assert isinstance(d["real_names"][0], dict)
        assert d["real_names"][0]["value"] == "Alice"
        assert d["real_names"][0]["source"] == "Maigret"
        assert d["real_names"][0]["confidence"] == 0.85

    def test_from_dict_roundtrip(self):
        entity = self._make_entity()
        d = entity.to_dict()
        restored = ProfileEntity.from_dict(d)

        assert restored.seed == entity.seed
        assert restored.seed_type == entity.seed_type
        assert len(restored.real_names) == 1
        assert restored.real_names[0].value == "Alice"
        assert restored.real_names[0].source == "Maigret"
        assert restored.confidence == 0.85
        assert restored.platforms == {"github": "https://github.com/alice"}
        assert set(restored.breach_sources) == {"Adobe", "Canva"}

    def test_from_dict_empty_entity(self):
        entity = ProfileEntity(seed="user", seed_type="USERNAME")
        d = entity.to_dict()
        restored = ProfileEntity.from_dict(d)
        assert restored.seed == "user"
        assert restored.seed_type == "USERNAME"
        assert restored.real_names == []
        assert restored.confidence == 0.0
