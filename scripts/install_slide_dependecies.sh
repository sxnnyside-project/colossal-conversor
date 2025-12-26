#!/usr/bin/env bash
# install_slide_dependecies.sh
# Purpose: Try to install common slide conversion tools used by the project.
# Supported tools: LibreOffice (soffice), Poppler (pdftoppm)
# Usage: ./scripts/install_slide_dependecies.sh [--yes]

set -euo pipefail

AUTO_YES=0
if [[ "${1:-}" == "--yes" ]] || [[ "${1:-}" == "-y" ]]; then
  AUTO_YES=1
fi

confirm() {
  if [[ $AUTO_YES -eq 1 ]]; then
    return 0
  fi
  read -r -p "$1 [y/N]: " response
  case "$response" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) return 1 ;;
  esac
}

run_sudo() {
  if [[ $(id -u) -eq 0 ]]; then
    "$@"
  else
    if command -v sudo >/dev/null 2>&1; then
      sudo "$@"
    else
      echo "This operation requires elevated privileges but 'sudo' is not available."
      return 2
    fi
  fi
}

OS_NAME="$(uname -s)"

detect_linux_distro() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    echo "$ID" || true
  else
    echo "unknown"
  fi
}

install_with_pkgmgr() {
  local mgr="$1"; shift
  case "$mgr" in
    brew)
      if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found. Install it from https://brew.sh/ and re-run this script."
        return 2
      fi
      if confirm "Install LibreOffice and poppler via Homebrew?"; then
        brew install --cask libreoffice
        brew install poppler
      else
        return 1
      fi
      ;;
    apt)
      if confirm "Install LibreOffice and poppler via apt?"; then
        run_sudo apt-get update
        run_sudo apt-get install -y libreoffice poppler-utils
      else
        return 1
      fi
      ;;
    dnf)
      if confirm "Install LibreOffice and poppler via dnf?"; then
        run_sudo dnf install -y libreoffice poppler-utils
      else
        return 1
      fi
      ;;
    pacman)
      if confirm "Install LibreOffice and poppler via pacman?"; then
        run_sudo pacman -Syu --noconfirm libreoffice poppler
      else
        return 1
      fi
      ;;
    apk)
      if confirm "Install LibreOffice and poppler via apk?"; then
        run_sudo apk add --no-cache libreoffice poppler-utils
      else
        return 1
      fi
      ;;
    zypper)
      if confirm "Install LibreOffice and poppler via zypper?"; then
        run_sudo zypper install -y libreoffice poppler-tools
      else
        return 1
      fi
      ;;
    *)
      echo "Unknown package manager: $mgr"
      return 4
      ;;
  esac
}

case "$OS_NAME" in
  Darwin)
    install_with_pkgmgr brew || {
      echo "Failed to install via Homebrew."
      exit 1
    }
    ;;
  Linux)
    DISTRO_ID="$(detect_linux_distro)"
    case "${DISTRO_ID}" in
      ubuntu|debian|linuxmint)
        install_with_pkgmgr apt || exit 1
        ;;
      fedora)
        install_with_pkgmgr dnf || exit 1
        ;;
      arch|manjaro)
        install_with_pkgmgr pacman || exit 1
        ;;
      alpine)
        install_with_pkgmgr apk || exit 1
        ;;
      opensuse*|suse)
        install_with_pkgmgr zypper || exit 1
        ;;
      *)
        echo "Unsupported distro. Please install libreoffice and poppler manually."
        exit 1
        ;;
    esac
    ;;
  CYGWIN*|MINGW*|MSYS*|Windows_NT)
    echo "On Windows, install LibreOffice and Poppler manually or via choco/winget."
    exit 0
    ;;
  *)
    echo "Unsupported OS: $OS_NAME. Please install libreoffice and poppler manually."
    exit 1
    ;;
esac

# Summary
for t in soffice pdftoppm; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "$t -> $(command -v $t)"
  else
    echo "$t -> MISSING"
  fi
done

