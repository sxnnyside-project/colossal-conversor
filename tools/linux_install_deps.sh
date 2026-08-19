#!/usr/bin/env bash
# Installs Colossal Conversor's external conversion tools on Linux via the
# system package manager (apt, dnf, or pacman — auto-detected).
# Safe to re-run: skips anything already resolvable on PATH.
set -euo pipefail

if command -v apt-get >/dev/null 2>&1; then
    PM="apt"
elif command -v dnf >/dev/null 2>&1; then
    PM="dnf"
elif command -v pacman >/dev/null 2>&1; then
    PM="pacman"
else
    echo "No supported package manager found (looked for apt, dnf, pacman)." >&2
    echo "Install ffmpeg, libreoffice, poppler-utils, pandoc, and imagemagick manually." >&2
    exit 1
fi

case "$PM" in
    apt)
        declare -a TOOLS=(
            "ffmpeg:ffmpeg"
            "soffice:libreoffice"
            "pdftoppm:poppler-utils"
            "pandoc:pandoc"
            "magick:imagemagick"
        )
        INSTALL_CMD=(sudo apt-get install -y)
        UPDATE_CMD=(sudo apt-get update)
        ;;
    dnf)
        declare -a TOOLS=(
            "ffmpeg:ffmpeg"
            "soffice:libreoffice"
            "pdftoppm:poppler-utils"
            "pandoc:pandoc"
            "magick:ImageMagick"
        )
        INSTALL_CMD=(sudo dnf install -y)
        UPDATE_CMD=()
        ;;
    pacman)
        declare -a TOOLS=(
            "ffmpeg:ffmpeg"
            "soffice:libreoffice-fresh"
            "pdftoppm:poppler"
            "pandoc:pandoc"
            "magick:imagemagick"
        )
        INSTALL_CMD=(sudo pacman -S --noconfirm)
        UPDATE_CMD=()
        ;;
esac

echo "Detected package manager: $PM"

if [ "${#UPDATE_CMD[@]}" -gt 0 ]; then
    "${UPDATE_CMD[@]}"
fi

failures=0
for entry in "${TOOLS[@]}"; do
    tool="${entry%%:*}"
    package="${entry##*:}"

    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool already available, skipping"
        continue
    fi

    echo "Installing $package (for $tool)..."
    if "${INSTALL_CMD[@]}" "$package"; then
        if command -v "$tool" >/dev/null 2>&1; then
            echo "✓ $tool installed successfully"
        else
            echo "✗ $package installed but '$tool' is still not on PATH" >&2
            failures=$((failures + 1))
        fi
    else
        echo "✗ Failed to install $package" >&2
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "$failures tool(s) failed to install. See messages above." >&2
    exit 1
fi

echo "All dependencies available."
