#!/usr/bin/env bash
# install_sheet_dependecies.sh
# Purpose: Try to install common sheet processing tools used by the project.
# Supported tools: LibreOffice (soffice), ssconvert (gnumeric), pandas (python) and tabula/camelot for PDF tables.
# Usage: ./scripts/install_sheet_dependecies.sh [--yes]

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
        echo "Homebrew not found."
        return 2
      fi
      if confirm "Install LibreOffice, gnumeric, pandas via Homebrew?"; then
        brew install --cask libreoffice
        brew install gnumeric
        brew install python
        pip3 install pandas camelot-py tabula-py
      else
        return 1
      fi
      ;;
    apt)
      if confirm "Install LibreOffice, gnumeric, python3-pip via apt?"; then
        run_sudo apt-get update
        run_sudo apt-get install -y libreoffice gnumeric python3-pip poppler-utils
        pip3 install pandas camelot-py tabula-py
      else
        return 1
      fi
      ;;
    pacman)
      if confirm "Install via pacman?"; then
        run_sudo pacman -Syu --noconfirm libreoffice-fresh gnumeric python-pip
        pip install pandas camelot-py tabula-py
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
    install_with_pkgmgr brew || exit 1
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
      *)
        echo "Unsupported distro: please install libreoffice, gnumeric, pip and python packages manually."
        exit 1
        ;;
    esac
    ;;
  *)
    echo "Unsupported OS: $OS_NAME. Please install dependencies manually."
    exit 1
    ;;
esac

for t in soffice ssconvert python3; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "$t -> $(command -v $t)"
  else
    echo "$t -> MISSING"
  fi
done

