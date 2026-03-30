"""
Core/scrapers/__init__.py

Package entrypoint — exposes ScraperRegistry for easy importing.

Story 1.4 — Scraper Registry Pattern, Epic 1.
"""
from Core.scrapers.registry import ScraperRegistry

__all__ = ["ScraperRegistry"]
