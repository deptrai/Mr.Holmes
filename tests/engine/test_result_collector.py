"""
tests/engine/test_result_collector.py

Unit tests cho Story 2.3 — ScanResultCollector class.

Test coverage:
    - AC1: add() / add_many() accumulate ScanResult objects
    - AC2: found_urls, found_names, scraper_sites, all_tags, most_tags properties
    - AC3: Replaces 5 mutable lists pattern
    - AC4: Thread-safety (concurrent add)
    - AC5: to_report_text(), to_mh(), to_json() export formats
"""
from __future__ import annotations

import json
import threading

from Core.engine.result_collector import ScanResultCollector
from Core.models.scan_result import ScanResult, ScanStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    name: str = "Site",
    url: str = "https://example.com/user",
    status: ScanStatus = ScanStatus.FOUND,
    is_scrapable: bool = False,
    tags: list = None,
) -> ScanResult:
    return ScanResult(
        site_name=name,
        url=url,
        status=status,
        is_scrapable=is_scrapable,
        tags=tags or [],
    )


# ---------------------------------------------------------------------------
# AC1 — add() / add_many()
# ---------------------------------------------------------------------------

class TestAddMethods:
    def test_add_single_result(self):
        """add() accumulates a single ScanResult."""
        c = ScanResultCollector()
        c.add(make_result("GitHub", "https://github.com/user"))
        assert c.total_count == 1

    def test_add_many_batch(self):
        """add_many() batch-adds a list of results."""
        c = ScanResultCollector()
        results = [make_result(f"Site{i}") for i in range(5)]
        c.add_many(results)
        assert c.total_count == 5

    def test_add_preserves_all_results(self):
        """All added results accessible via all_results."""
        c = ScanResultCollector()
        r1 = make_result("A", status=ScanStatus.FOUND)
        r2 = make_result("B", status=ScanStatus.NOT_FOUND)
        c.add_many([r1, r2])
        names = [r.site_name for r in c.all_results]
        assert "A" in names
        assert "B" in names


# ---------------------------------------------------------------------------
# AC2 — Derived properties
# ---------------------------------------------------------------------------

class TestDerivedProperties:
    def test_found_urls_only_found_status(self):
        """found_urls → only FOUND status URLs."""
        c = ScanResultCollector()
        c.add(make_result("F", "https://found.com", ScanStatus.FOUND))
        c.add(make_result("NF", "https://notfound.com", ScanStatus.NOT_FOUND))
        c.add(make_result("E", "https://error.com", ScanStatus.ERROR))
        assert c.found_urls == ["https://found.com"]

    def test_found_names_only_found_status(self):
        """found_names → site names of FOUND sites only."""
        c = ScanResultCollector()
        c.add(make_result("GitHub", status=ScanStatus.FOUND))
        c.add(make_result("Twitter", status=ScanStatus.NOT_FOUND))
        assert c.found_names == ["GitHub"]
        assert "Twitter" not in c.found_names

    def test_scraper_sites_scrapable_found_only(self):
        """scraper_sites → FOUND + is_scrapable sites only."""
        c = ScanResultCollector()
        c.add(make_result("Instagram", is_scrapable=True, status=ScanStatus.FOUND))
        c.add(make_result("AnonSite", is_scrapable=False, status=ScanStatus.FOUND))
        c.add(make_result("TikTok", is_scrapable=True, status=ScanStatus.NOT_FOUND))
        assert c.scraper_sites == ["Instagram"]

    def test_found_count_accurate(self):
        """found_count counts FOUND only."""
        c = ScanResultCollector()
        c.add_many([
            make_result(status=ScanStatus.FOUND),
            make_result(status=ScanStatus.FOUND),
            make_result(status=ScanStatus.NOT_FOUND),
            make_result(status=ScanStatus.ERROR),
        ])
        assert c.found_count == 2

    def test_total_count_all_statuses(self):
        """total_count counts all regardless of status."""
        c = ScanResultCollector()
        c.add_many([make_result(status=s) for s in [
            ScanStatus.FOUND, ScanStatus.NOT_FOUND, ScanStatus.ERROR
        ]])
        assert c.total_count == 3


# ---------------------------------------------------------------------------
# Tag accumulation — replaces Tags + MostTags lists
# ---------------------------------------------------------------------------

class TestTagAccumulation:
    def test_first_occurrence_goes_to_all_tags(self):
        """New tag → added to all_tags (first occurrence)."""
        c = ScanResultCollector(subject="USERNAME")
        c.add(make_result(tags=["Developer"]))
        assert "Developer" in c.all_tags

    def test_recurring_tag_goes_to_most_tags(self):
        """Tag seen twice → added to most_tags on second occurrence."""
        c = ScanResultCollector(subject="USERNAME")
        c.add(make_result(tags=["Social"]))   # first: → all_tags
        c.add(make_result(tags=["Social"]))   # second: → most_tags
        assert "Social" in c.most_tags

    def test_unique_tag_always_in_most_tags(self):
        """UNIQUE_TAGS (e.g. Chess) always added to most_tags."""
        c = ScanResultCollector(subject="USERNAME")
        c.add(make_result(tags=["Chess"]))
        assert "Chess" in c.most_tags

    def test_phone_number_skips_tag_processing(self):
        """PHONE-NUMBER subject → tags never processed."""
        c = ScanResultCollector(subject="PHONE-NUMBER")
        c.add(make_result(tags=["Social", "Developer"]))
        assert c.all_tags == []
        assert c.most_tags == []

    def test_all_tags_contains_unique_first_occurrences(self):
        """all_tags accumulates unique tag names (first occurrence)."""
        c = ScanResultCollector(subject="USERNAME")
        c.add(make_result(tags=["A", "B"]))
        c.add(make_result(tags=["B", "C"]))  # B already in all_tags
        assert sorted(c.all_tags) == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# AC4 — Thread-safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_add_no_data_race(self):
        """Concurrent add() from N threads → all results accumulated correctly."""
        c = ScanResultCollector()
        n_threads = 10
        results_per_thread = 50
        errors = []

        def worker():
            try:
                for i in range(results_per_thread):
                    c.add(make_result(f"Site{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert c.total_count == n_threads * results_per_thread


# ---------------------------------------------------------------------------
# AC5 — Export methods (report format compatible)
# ---------------------------------------------------------------------------

class TestExportMethods:
    def test_to_report_text_only_found_urls(self):
        """to_report_text() → one URL per line, FOUND only."""
        c = ScanResultCollector()
        c.add(make_result("A", "https://a.com", ScanStatus.FOUND))
        c.add(make_result("B", "https://b.com", ScanStatus.NOT_FOUND))
        text = c.to_report_text()
        assert "https://a.com" in text
        assert "https://b.com" not in text

    def test_to_report_text_empty_when_none_found(self):
        """to_report_text() → empty string if no FOUND results."""
        c = ScanResultCollector()
        c.add(make_result(status=ScanStatus.NOT_FOUND))
        assert c.to_report_text() == ""

    def test_to_mh_same_as_report_text(self):
        """to_mh() produces same content as to_report_text()."""
        c = ScanResultCollector()
        c.add(make_result("G", "https://g.com", ScanStatus.FOUND))
        assert c.to_mh() == c.to_report_text()

    def test_to_json_valid_json_structure(self):
        """to_json() → valid JSON with expected keys."""
        c = ScanResultCollector(subject="USERNAME")
        c.add(make_result("GitHub", "https://github.com/u", ScanStatus.FOUND))
        data = json.loads(c.to_json())
        assert data["subject"] == "USERNAME"
        assert data["total"] == 1
        assert data["found"] == 1
        assert isinstance(data["results"], list)
        assert "most_tags" in data
        assert "all_tags" in data

    def test_to_json_results_use_to_dict_format(self):
        """to_json() results use ScanResult.to_dict() field names."""
        c = ScanResultCollector()
        c.add(make_result("Twitter", "https://twitter.com/u", ScanStatus.FOUND))
        data = json.loads(c.to_json())
        result = data["results"][0]
        # ScanResult.to_dict() uses "site" and "name" keys
        assert "site" in result
        assert "name" in result
        assert result["site"] == "https://twitter.com/u"

    def test_to_dict_returns_dict(self):
        """to_dict() returns a Python dict."""
        c = ScanResultCollector()
        c.add(make_result())
        d = c.to_dict()
        assert isinstance(d, dict)
        assert "results" in d
