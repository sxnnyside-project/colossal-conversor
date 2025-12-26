#!/usr/bin/env bash
# install_audio_dependecies.sh
# Purpose: Try to install common audio processing tools used by the project.
# Supported engines/tools: ffmpeg
#Usage: ./scripts/install_audio_dependencies.sh [--yes]

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

echo "Checking for ffmpeg..."
if command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg already installed: $(ffmpeg -version | head -n 1)"
  exit 0
fi

OS_NAME="$(uname -s)"
# Linux distro detection
detect_linux_distro() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    echo "$ID" || true
  else
    echo "unknown"
  fi
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

install_with_pkgmgr() {
  local mgr="$1"; shift
  case "$mgr" in
    brew)
      if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found. Install it from https://brew.sh/ and re-run this script."
        return 2
      fi
      if confirm "Install ffmpeg via Homebrew?"; then
        brew install ffmpeg
      else
        return 1
      fi
      ;;
    apt)
      if confirm "Run apt-get update and install ffmpeg?"; then
        run_sudo apt-get update
        run_sudo apt-get install -y ffmpeg
      else
        return 1
      fi
      ;;
    dnf)
      if confirm "Attempt to install ffmpeg via dnf? (may require rpmfusion)"; then
        run_sudo dnf install -y ffmpeg || return 3
      else
        return 1
      fi
      ;;
    yum)
      if confirm "Attempt to install ffmpeg via yum? (may require EPEL/rpmfusion)"; then
        run_sudo yum install -y ffmpeg || return 3
      else
        return 1
      fi
      ;;
    pacman)
      if confirm "Install ffmpeg via pacman?"; then
        run_sudo pacman -Syu --noconfirm ffmpeg
      else
        return 1
      fi
      ;;
    apk)
      if confirm "Install ffmpeg via apk?"; then
        run_sudo apk add --no-cache ffmpeg
      else
        return 1
      fi
      ;;
    zypper)
      if confirm "Install ffmpeg via zypper?"; then
        run_sudo zypper install -y ffmpeg
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
    echo "Detected macOS"
    install_with_pkgmgr brew || {
      echo "Failed to install via Homebrew or Homebrew missing. See https://brew.sh/"
      exit 1
    }
    ;;
  Linux)
    DISTRO_ID="$(detect_linux_distro)"
    echo "Detected Linux distro: ${DISTRO_ID:-unknown}"
    case "${DISTRO_ID}" in
      ubuntu|debian|linuxmint)
        install_with_pkgmgr apt || exit 1
        ;;
      fedora)
        # Fedora frequently needs rpmfusion for ffmpeg
        if install_with_pkgmgr dnf; then
          true
        else
          echo "Automatic installation with dnf failed or ffmpeg not in default repos."
          echo "To install on Fedora, enable RPM Fusion free/nonfree and then install ffmpeg. Example:"
          echo "  sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm"
          echo "  sudo dnf install ffmpeg"
          exit 1
        fi
        ;;
      centos|rhel)
        echo "On CentOS/RHEL you may need EPEL and RPM Fusion; the script cannot reliably enable repos for you."
        echo "Recommended manual steps: enable EPEL/rpmfusion and then install ffmpeg."
        exit 1
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
        echo "Unsupported or unknown Linux distribution. Try installing ffmpeg manually. Common commands:"
        echo "  Debian/Ubuntu: sudo apt-get install ffmpeg"
        echo "  Fedora: sudo dnf install ffmpeg (or enable RPM Fusion)"
        echo "  Arch: sudo pacman -S ffmpeg"
        exit 1
        ;;
    esac
    ;;
  CYGWIN*|MINGW*|MSYS*|Windows_NT)
    echo "Detected Windows-like environment. The script cannot automatically install ffmpeg on Windows from bash."
    echo "Recommended options (run in an elevated PowerShell or admin CMD):"
    echo "  Chocolatey: choco install ffmpeg -y"
    echo "  winget:    winget install --id=Gyan.FFmpeg -e --source winget"
    echo "Or download a static build from: https://ffmpeg.org/download.html"
    exit 1
    ;;
  *)
    echo "Unknown OS: $OS_NAME. Please install ffmpeg manually."
    exit 1
    ;;
esac

# Final check
if command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg installed: $(ffmpeg -version | head -n 1)"
  exit 0
else
  echo "ffmpeg not found after attempted installation. Please install it manually and re-run this script."
  exit 1
fi

