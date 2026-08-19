#!/usr/bin/env bash
# Installs Colossal Conversor's external conversion tools on macOS via Homebrew.
# Safe to re-run: skips anything already resolvable on PATH.
set -euo pipefail

# tool_name -> homebrew formula
declare -a TOOLS=(
    "ffmpeg:ffmpeg"
    "soffice:libreoffice"
    "pdftoppm:poppler"
    "pandoc:pandoc"
    "magick:imagemagick"
)

if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is not installed. Install it from https://brew.sh and re-run this script." >&2
    exit 1
fi

LIBREOFFICE_APP_BIN="/Applications/LibreOffice.app/Contents/MacOS/soffice"

failures=0
for entry in "${TOOLS[@]}"; do
    tool="${entry%%:*}"
    formula="${entry##*:}"

    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool already available, skipping"
        continue
    fi

    if [ "$tool" = "soffice" ]; then
        # LibreOffice ships as a Homebrew cask (a .app bundle), not a
        # formula — its binary is never placed on PATH automatically.
        echo "Installing libreoffice (cask, for soffice)..."
        if brew install --cask libreoffice; then
            if [ -x "$LIBREOFFICE_APP_BIN" ]; then
                brew_bin="$(brew --prefix)/bin"
                ln -sf "$LIBREOFFICE_APP_BIN" "$brew_bin/soffice"
                echo "✓ soffice linked into $brew_bin"
            else
                echo "✗ LibreOffice installed but $LIBREOFFICE_APP_BIN not found" >&2
                failures=$((failures + 1))
            fi
        else
            echo "✗ Failed to install libreoffice" >&2
            failures=$((failures + 1))
        fi
        continue
    fi

    echo "Installing $formula (for $tool)..."
    if brew install "$formula"; then
        if command -v "$tool" >/dev/null 2>&1; then
            echo "✓ $tool installed successfully"
        else
            echo "✗ $formula installed but '$tool' is still not on PATH — check brew's output above" >&2
            failures=$((failures + 1))
        fi
    else
        echo "✗ Failed to install $formula" >&2
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "$failures tool(s) failed to install. See messages above." >&2
    exit 1
fi

echo "All dependencies available."
