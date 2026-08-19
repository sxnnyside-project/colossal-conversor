#!/usr/bin/env python3
"""Reports which of Colossal Conversor's external conversion tools are
resolvable on PATH — the same lookup native/src/discovery.cpp performs at
runtime (this script deliberately doesn't call into the native module, so
it also works before the extension has been built).
"""

from __future__ import annotations

import shutil
import sys

# tool name -> (display name, capabilities that depend on it)
TOOLS: dict[str, tuple[str, str]] = {
    "ffmpeg": ("FFmpeg", "audio and video conversions"),
    "soffice": ("LibreOffice", "document, spreadsheet, and slide conversions"),
    "pdftoppm": ("Poppler", "document-to-image page rendering"),
    "pandoc": ("Pandoc", "markdown/document conversions"),
    "magick": ("ImageMagick", "image conversions beyond BMP/PPM/TGA (e.g. SVG, GIF)"),
}


def main() -> int:
    print("Colossal Conversor — external dependency check\n")

    missing: list[tuple[str, str]] = []
    name_width = max(len(display) for display, _ in TOOLS.values())

    for tool, (display, capabilities) in TOOLS.items():
        found = shutil.which(tool)
        status = f"✓ available ({found})" if found else "✗ missing"
        print(f"{display:<{name_width}}  {status}")
        if not found:
            missing.append((display, capabilities))

    if missing:
        print("\nMissing dependencies affect these capabilities:")
        for display, capabilities in missing:
            print(f"  - {display}: {capabilities}")
        print(
            "\nSee tools/README.md, or run the provisioning script for your "
            "platform (tools/macos_install_deps.sh, tools/linux_install_deps.sh, "
            "tools/windows_install_deps.ps1)."
        )
        return 1

    print("\nAll external dependencies are available.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
