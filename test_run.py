import sys
from tests.unit.test_email_searcher import TestEmailReportFolder

t = TestEmailReportFolder()
t.test_search_creates_email_folder_if_not_exists()
print("Success 1!")
t.test_search_deletes_existing_folder_first()
print("Success 2!")
