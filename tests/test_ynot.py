"""Smoke tests for ynot."""

import main


def test_version_constant_absent() -> None:
    # Modern code intentionally avoids importing GUI at module import
    assert hasattr(main, "sanitize_filename")


def test_sanitize_filename() -> None:
    assert main.sanitize_filename("A/B:C") == "A-B-C"
    assert main.sanitize_filename("") == "video"


def test_load_config_returns_mapping() -> None:
    result = main.load_config()
    assert isinstance(result, dict)
    assert "save_path" in result
