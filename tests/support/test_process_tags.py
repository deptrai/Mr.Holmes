"""
tests/support/test_process_tags.py

Unit tests cho Search._process_tags() method.
Story 1.2 — Extract Process Tags Method, Epic 1.

Tests verify behavior identical với code cũ.
"""
import pytest
from Core.Support.Requests_Search import Search, UNIQUE_TAGS


class TestProcessTags:
    """Tests cho Search._process_tags() static method."""

    def test_phone_number_skips_all_processing(self):
        """subject == PHONE-NUMBER → không có mutations."""
        all_tags = []
        most_tags = []
        Search._process_tags(
            tag_list=["Social", "Chat"],
            subject="PHONE-NUMBER",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert all_tags == []
        assert most_tags == []

    def test_empty_tag_list_no_mutations(self):
        """tag_list rỗng → không có mutations."""
        all_tags = []
        most_tags = []
        Search._process_tags(
            tag_list=[],
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert all_tags == []
        assert most_tags == []

    def test_new_tag_added_to_all_tags(self):
        """Tag chưa có trong all_tags → được thêm vào all_tags."""
        all_tags = []
        most_tags = []
        Search._process_tags(
            tag_list=["Social"],
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert "Social" in all_tags
        assert "Social" not in most_tags

    def test_recurring_tag_added_to_most_tags(self):
        """Tag đã có trong all_tags nhưng chưa trong most_tags → thêm vào most_tags."""
        all_tags = ["Social"]  # già có từ site trước
        most_tags = []
        Search._process_tags(
            tag_list=["Social"],  # xuất hiện lần 2
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert "Social" in most_tags

    def test_recurring_tag_already_in_most_tags_not_duplicated(self):
        """Tag đã trong all_tags VÀ trong most_tags → KHÔNG thêm thêm (no duplicate)."""
        all_tags = ["Social"]
        most_tags = ["Social"]
        Search._process_tags(
            tag_list=["Social"],
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert most_tags.count("Social") == 1  # không bị duplicate

    def test_unique_tag_always_added_to_most_tags(self):
        """Tag thuộc UNIQUE_TAGS → luôn thêm vào most_tags (ngay cả lần đầu)."""
        unique_tag = UNIQUE_TAGS[0]  # ví dụ: "Chess"
        all_tags = []
        most_tags = []
        Search._process_tags(
            tag_list=[unique_tag],
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert unique_tag in most_tags

    def test_unique_tag_also_added_to_all_tags_on_first_occurrence(self):
        """Tag thuộc UNIQUE_TAGS + lần đầu gặp → thêm vào cả all_tags lẫn most_tags."""
        unique_tag = "Chess"
        all_tags = []
        most_tags = []
        Search._process_tags(
            tag_list=[unique_tag],
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        # UNIQUE_TAGS logic: thêm vào most_tags TRƯỚC khi kiểm tra all_tags
        # rồi vì chưa có trong all_tags → cũng thêm vào all_tags
        assert unique_tag in most_tags
        assert unique_tag in all_tags

    def test_multiple_tags_processed_independently(self):
        """Nhiều tags được xử lý độc lập nhau."""
        all_tags = ["ExistingTag"]
        most_tags = []
        Search._process_tags(
            tag_list=["NewTag", "ExistingTag", "AnotherNew"],
            subject="USERNAME",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert "NewTag" in all_tags
        assert "AnotherNew" in all_tags
        assert "ExistingTag" in most_tags  # recurring

    def test_all_unique_tags_constant_accessible(self):
        """UNIQUE_TAGS constant có đủ 29 entries."""
        assert len(UNIQUE_TAGS) == 29
        assert "Chess" in UNIQUE_TAGS
        assert "Python" in UNIQUE_TAGS
        assert "Badge" in UNIQUE_TAGS

    def test_subject_email_processes_tags(self):
        """subject == EMAIL (không phải PHONE-NUMBER) → tags được xử lý."""
        all_tags = []
        most_tags = []
        Search._process_tags(
            tag_list=["Social"],
            subject="EMAIL",
            all_tags=all_tags,
            most_tags=most_tags,
        )
        assert "Social" in all_tags

    def test_behavior_matches_original_duplication(self):
        """Integration: verify logic khớp 100% với behavior code cũ.

        Note: UNIQUE_TAGS được append vào most_tags mỗi lần gặp (not deduplicated).
        Đây là behavior của code gốc — không phải bug cần fix trong Story 1.2.
        """
        all_tags = []
        most_tags = []

        # Site 1: tags=["Python", "Developer"]
        Search._process_tags(["Python", "Developer"], "USERNAME", all_tags, most_tags)
        # Python là UNIQUE → added to most_tags
        # Developer → new → added to all_tags
        assert "Python" in most_tags
        assert "Developer" in all_tags
        assert "Python" in all_tags  # cũng thêm vào all_tags vì lần đầu gặp

        # Site 2: tags=["Python", "Social"]
        Search._process_tags(["Python", "Social"], "USERNAME", all_tags, most_tags)
        # Python: UNIQUE → append lại vào most_tags (original behavior)
        # Social → new → added to all_tags
        assert most_tags.count("Python") == 2  # UNIQUE được append mỗi lần (original behavior)
        assert "Social" in all_tags

        # Site 3: tags=["Social", "Chess"] (Chess is UNIQUE)
        Search._process_tags(["Social", "Chess"], "USERNAME", all_tags, most_tags)
        # Social: already in all_tags, not in most_tags → add to most_tags
        # Chess: UNIQUE → add to most_tags; new → add to all_tags
        assert "Social" in most_tags
        assert "Chess" in most_tags
        assert "Chess" in all_tags
