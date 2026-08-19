from __future__ import annotations

from pathlib import Path

from colossal import colossal_native


def detect_file_format(path: Path | str) -> str:
    """Detect file format using binary magic byte inspection."""
    return colossal_native.FormatDetector.detect_format(path)


def detect_file_mime(path: Path | str) -> str:
    """Detect file MIME type using binary magic byte inspection."""
    return colossal_native.FormatDetector.detect_mime(path)
