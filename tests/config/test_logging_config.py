"""
tests/config/test_logging_config.py

Unit tests cho Core/config/logging_config.py — Story 4.3.

Test coverage:
    - AC1: Logger setup tại Core/config/logging_config.py
    - AC2: Log levels theo severity
    - AC3: Console handler (stderr)
    - AC4: File handler optional
    - AC5: get_logger() returns child of mrholmes hierarchy
"""
from __future__ import annotations

import logging
import os
import pytest

from Core.config.logging_config import get_logger, setup_logging, _ROOT_LOGGER_NAME


# ---------------------------------------------------------------------------
# AC1 + AC5: get_logger hierarchy
# ---------------------------------------------------------------------------

class TestGetLogger:
    def test_get_logger_returns_logger(self) -> None:
        """AC5: get_logger() returns a logging.Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_uses_mrholmes_prefix(self) -> None:
        """AC5: get_logger('foo') returns logger named 'mrholmes.foo'."""
        logger = get_logger("some.module")
        assert logger.name == f"{_ROOT_LOGGER_NAME}.some.module"

    def test_get_logger_no_double_prefix(self) -> None:
        """AC5: If name starts with 'mrholmes', don't add prefix twice."""
        logger = get_logger("mrholmes.already.prefixed")
        assert logger.name == "mrholmes.already.prefixed"

    def test_get_logger_dunder_name_pattern(self) -> None:
        """AC5: Normal usage with __name__ style."""
        logger = get_logger("Core.engine.scan_pipeline")
        assert logger.name == "mrholmes.Core.engine.scan_pipeline"


# ---------------------------------------------------------------------------
# AC1 + AC2: setup_logging levels
# ---------------------------------------------------------------------------

class TestSetupLogging:
    def setup_method(self) -> None:
        """Reset root logger handlers and _configured flag before each test."""
        import Core.config.logging_config as lc
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        root.handlers.clear()
        lc._configured = False

    def test_setup_logging_adds_console_handler(self) -> None:
        """AC1 + AC3: setup_logging adds a StreamHandler."""
        setup_logging(level=logging.DEBUG)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        stream_handlers = [h for h in root.handlers
                          if isinstance(h, logging.StreamHandler)
                          and not isinstance(h, logging.FileHandler)]
        assert len(stream_handlers) >= 1

    def test_setup_logging_idempotent(self) -> None:
        """AC1: Calling setup_logging() twice does not add duplicates."""
        setup_logging(level=logging.WARNING)
        setup_logging(level=logging.WARNING)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        assert len(root.handlers) == 1

    def test_setup_logging_level_warning_by_default(self) -> None:
        """AC2: Default console level is WARNING."""
        setup_logging()
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        console = next((h for h in root.handlers
                       if isinstance(h, logging.StreamHandler)
                       and not isinstance(h, logging.FileHandler)), None)
        assert console is not None
        assert console.level == logging.WARNING

    def test_setup_logging_root_captures_debug(self) -> None:
        """AC2: Root logger level is always DEBUG (handlers do filtering)."""
        setup_logging(level=logging.INFO)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        assert root.level == logging.DEBUG


# ---------------------------------------------------------------------------
# AC4: File handler optional
# ---------------------------------------------------------------------------

class TestFileHandler:
    def setup_method(self) -> None:
        import Core.config.logging_config as lc
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        root.handlers.clear()
        lc._configured = False

    def test_no_file_handler_by_default(self) -> None:
        """AC4: File handler NOT added when enable_file=False."""
        setup_logging(enable_file=False)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_file_handler_added_when_enabled(self, tmp_path, monkeypatch) -> None:
        """AC4: File handler IS added when enable_file=True."""
        from Core.config import logging_config as lc
        monkeypatch.setattr(lc, "_LOG_DIR", tmp_path)
        monkeypatch.setattr(lc, "_LOG_FILE", tmp_path / "mrholmes.log")

        setup_logging(enable_file=True)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

        # Cleanup: close handler to release file
        for h in file_handlers:
            h.close()
        root.handlers.clear()


# ---------------------------------------------------------------------------
# Patch #3: _auto_setup env var integration
# ---------------------------------------------------------------------------

class TestAutoSetup:
    def setup_method(self) -> None:
        import Core.config.logging_config as lc
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        root.handlers.clear()
        lc._configured = False

    def test_auto_setup_respects_log_level_env(self, monkeypatch) -> None:
        """_auto_setup reads MH_LOG_LEVEL env var and sets console handler level."""
        import Core.config.logging_config as lc
        monkeypatch.setenv("MH_LOG_LEVEL", "DEBUG")
        monkeypatch.setattr(lc, "_configured", False)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        root.handlers.clear()

        # Trigger _auto_setup via get_logger
        logger = get_logger("test_auto")

        console = next((h for h in root.handlers
                       if isinstance(h, logging.StreamHandler)
                       and not isinstance(h, logging.FileHandler)), None)
        assert console is not None
        assert console.level == logging.DEBUG

    def test_auto_setup_default_warning(self, monkeypatch) -> None:
        """_auto_setup defaults to WARNING when MH_LOG_LEVEL not set."""
        import Core.config.logging_config as lc
        monkeypatch.delenv("MH_LOG_LEVEL", raising=False)
        monkeypatch.setattr(lc, "_configured", False)
        root = logging.getLogger(_ROOT_LOGGER_NAME)
        root.handlers.clear()

        get_logger("test_default")

        console = next((h for h in root.handlers
                       if isinstance(h, logging.StreamHandler)
                       and not isinstance(h, logging.FileHandler)), None)
        assert console is not None
        assert console.level == logging.WARNING
