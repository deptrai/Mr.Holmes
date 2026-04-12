"""
tests/cli/test_parser.py

Unit tests for Core.cli.parser — Story 5.1

Verifies:
    - AC2: all flags parse correctly (--username, --phone, --email, --website, --proxy, --nsfw, --output)
    - AC3: no args → no batch target (interactive mode fall-through)
    - AC4: --help exits cleanly
    - AC5: --output choices validated
    - Mutual exclusion of scan targets
"""
from __future__ import annotations

import argparse
import pytest

from Core.cli.parser import build_parser, parse_args, has_batch_target


class TestBuildParser:
    """Parser structure tests."""

    def test_returns_argument_parser(self) -> None:
        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_prog_name(self) -> None:
        parser = build_parser()
        assert parser.prog == "MrHolmes.py"


class TestParseArgs:
    """Flag parsing tests (AC2)."""

    def test_username_flag(self) -> None:
        args = parse_args(["--username", "johndoe"])
        assert args.username == "johndoe"
        assert args.phone is None
        assert args.email is None
        assert args.website is None

    def test_username_short_flag(self) -> None:
        args = parse_args(["-u", "testuser"])
        assert args.username == "testuser"

    def test_phone_flag(self) -> None:
        args = parse_args(["--phone", "+1234567890"])
        assert args.phone == "+1234567890"

    def test_phone_short_flag(self) -> None:
        args = parse_args(["-p", "+1234567890"])
        assert args.phone == "+1234567890"

    def test_email_flag(self) -> None:
        args = parse_args(["--email", "test@example.com"])
        assert args.email == "test@example.com"

    def test_email_short_flag(self) -> None:
        args = parse_args(["-e", "test@example.com"])
        assert args.email == "test@example.com"

    def test_website_flag(self) -> None:
        args = parse_args(["--website", "example.com"])
        assert args.website == "example.com"

    def test_website_short_flag(self) -> None:
        args = parse_args(["-w", "example.com"])
        assert args.website == "example.com"

    def test_proxy_flag_default_false(self) -> None:
        args = parse_args(["--username", "johndoe"])
        assert args.proxy is False

    def test_proxy_flag_enabled(self) -> None:
        args = parse_args(["--username", "johndoe", "--proxy"])
        assert args.proxy is True

    def test_nsfw_flag_default_false(self) -> None:
        args = parse_args(["--username", "johndoe"])
        assert args.nsfw is False

    def test_nsfw_flag_enabled(self) -> None:
        args = parse_args(["--username", "johndoe", "--nsfw"])
        assert args.nsfw is True

    def test_output_default_txt(self) -> None:
        args = parse_args(["--username", "johndoe"])
        assert args.output == "txt"

    def test_output_json(self) -> None:
        args = parse_args(["--username", "johndoe", "--output", "json"])
        assert args.output == "json"

    def test_output_csv(self) -> None:
        args = parse_args(["--username", "johndoe", "--output", "csv"])
        assert args.output == "csv"

    def test_output_short_flag(self) -> None:
        args = parse_args(["--username", "johndoe", "-o", "json"])
        assert args.output == "json"

    def test_output_invalid_choice_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--username", "johndoe", "--output", "pdf"])

    def test_no_args_all_targets_none(self) -> None:
        """AC3: no args → all targets None → interactive mode."""
        args = parse_args([])
        assert args.username is None
        assert args.phone is None
        assert args.email is None
        assert args.website is None

    def test_combined_flags(self) -> None:
        """All optional flags work together."""
        args = parse_args(["--username", "johndoe", "--proxy", "--nsfw", "--output", "json"])
        assert args.username == "johndoe"
        assert args.proxy is True
        assert args.nsfw is True
        assert args.output == "json"


class TestMutualExclusion:
    """Mutually exclusive scan targets (AC2)."""

    def test_username_and_phone_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--username", "johndoe", "--phone", "+1234567890"])

    def test_username_and_email_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--username", "johndoe", "--email", "test@example.com"])

    def test_username_and_website_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--username", "johndoe", "--website", "example.com"])

    def test_phone_and_email_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--phone", "+1234567890", "--email", "test@example.com"])


class TestHasBatchTarget:
    """has_batch_target() helper."""

    def test_username_is_batch(self) -> None:
        args = parse_args(["--username", "johndoe"])
        assert has_batch_target(args) is True

    def test_phone_is_batch(self) -> None:
        args = parse_args(["--phone", "+1234567890"])
        assert has_batch_target(args) is True

    def test_email_is_batch(self) -> None:
        args = parse_args(["--email", "test@example.com"])
        assert has_batch_target(args) is True

    def test_website_is_batch(self) -> None:
        args = parse_args(["--website", "example.com"])
        assert has_batch_target(args) is True

    def test_no_target_is_not_batch(self) -> None:
        """AC3: no target → interactive mode."""
        args = parse_args([])
        assert has_batch_target(args) is False

    def test_only_flags_no_target_is_not_batch(self) -> None:
        """Flags without target → interactive mode."""
        args = parse_args(["--proxy", "--nsfw", "--output", "json"])
        assert has_batch_target(args) is False


class TestHelp:
    """AC4: --help exits cleanly with exit code 0."""

    def test_help_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])
        assert exc_info.value.code == 0
