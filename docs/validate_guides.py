#!/usr/bin/env python3
"""Lightweight structural consistency check for docs/guides/.

Verifies every required locale exists, every guide has the same 15
numbered sections in the same order, and technical identifiers that must
stay untranslated (tool names, platform names) are actually present in
every language. This is intentionally shallow — it checks structure and
presence, not translation quality.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

GUIDES_DIR = Path(__file__).resolve().parent / "guides"
REQUIRED_LOCALES = ["en", "es", "fr", "ja", "pt", "zh"]
REQUIRED_SECTIONS = list(range(1, 16))  # 15 sections, numbered 1..15

# Identifiers that must appear verbatim (untranslated) in every guide.
REQUIRED_IDENTIFIERS = [
    "Colossal Conversor",
    "FFmpeg",
    "LibreOffice",
    "Poppler",
    "Pandoc",
    "ImageMagick",
    "macOS",
    "Linux",
    "Windows",
    "just verify-tools",
]

SECTION_HEADER_RE = re.compile(r"^##\s+(\d+)\.\s", re.MULTILINE)


def check_locale(locale: str) -> list[str]:
    errors: list[str] = []
    guide_path = GUIDES_DIR / locale / "README.md"

    if not guide_path.exists():
        return [f"[{locale}] missing guide file: {guide_path}"]

    text = guide_path.read_text(encoding="utf-8")

    found_sections = [int(n) for n in SECTION_HEADER_RE.findall(text)]
    if found_sections != REQUIRED_SECTIONS:
        missing = sorted(set(REQUIRED_SECTIONS) - set(found_sections))
        extra = sorted(set(found_sections) - set(REQUIRED_SECTIONS))
        if missing:
            errors.append(f"[{locale}] missing section(s): {missing}")
        if extra:
            errors.append(f"[{locale}] unexpected section number(s): {extra}")
        if found_sections != sorted(found_sections):
            errors.append(f"[{locale}] sections are out of order: {found_sections}")

    for identifier in REQUIRED_IDENTIFIERS:
        if identifier not in text:
            errors.append(f"[{locale}] missing required identifier: {identifier!r}")

    return errors


def main() -> int:
    all_errors: list[str] = []

    if not GUIDES_DIR.exists():
        print(f"docs/guides/ does not exist at {GUIDES_DIR}", file=sys.stderr)
        return 1

    present_locales = {p.name for p in GUIDES_DIR.iterdir() if p.is_dir()}
    missing_locales = set(REQUIRED_LOCALES) - present_locales
    if missing_locales:
        all_errors.append(f"missing locale director(ies): {sorted(missing_locales)}")

    for locale in REQUIRED_LOCALES:
        if locale in present_locales:
            all_errors.extend(check_locale(locale))

    if all_errors:
        print(f"docs/guides/ validation FAILED ({len(all_errors)} issue(s)):\n")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(
        f"docs/guides/ validation passed: {len(REQUIRED_LOCALES)} locales, "
        f"{len(REQUIRED_SECTIONS)} sections each, all required identifiers present."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
