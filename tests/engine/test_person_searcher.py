"""tests/engine/test_person_searcher.py — Person searcher tests."""
import os
import pytest
from Core.engine.person_searcher import PersonSearcher

class TestPersonSearcher:
    def test_class_exists(self):
        for m in ('normalize_name', 'get_report_path', 'google_dorks'):
            assert hasattr(PersonSearcher, m)
    
    def test_normalize_spaces_to_underscores(self):
        assert PersonSearcher.normalize_name("John Doe") == "John_Doe"
    
    def test_normalize_no_spaces(self):
        assert PersonSearcher.normalize_name("JohnDoe") == "JohnDoe"
    
    def test_normalize_multiple_spaces(self):
        assert PersonSearcher.normalize_name("John Michael Doe") == "John_Michael_Doe"
    
    def test_get_report_path_has_people(self):
        path = PersonSearcher.get_report_path("John Doe")
        assert "People" in path
        assert "John_Doe" in path
    
    def test_google_dorks_creates_dir(self, tmp_path):
        report = PersonSearcher.google_dorks("John Doe", str(tmp_path))
        assert os.path.exists(tmp_path)
        assert "John_Doe" in report
    
    def test_google_dorks_removes_existing(self, tmp_path):
        report = PersonSearcher.google_dorks("John Doe", str(tmp_path))
        with open(report, 'w') as f:
            f.write("old")
        PersonSearcher.google_dorks("John Doe", str(tmp_path))
        assert not os.path.exists(report)
