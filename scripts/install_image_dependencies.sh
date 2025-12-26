#!/usr/bin/env bash
# install_image_dependencies.sh
# Purpose: Try to install common image processing engines used by the project.
# Supported engines/tools: ImageMagick (magick/convert), gifsicle, cairosvg (pip), libheif (heif-convert), rsvg-convert
# Usage: ./scripts/install_image_dependencies.sh [--yes]

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

check_and_install() {
  local cmd="$1"
  local install_cmd="$2"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd already installed: $(command -v "$cmd")"
    return 0
  fi
  if confirm "Install $cmd?"; then
    eval "$install_cmd"
    return $?
  fi
  return 1
}

OS_NAME="$(uname -s)"
echo "Detected OS: $OS_NAME"

if [[ "$OS_NAME" == "Darwin" ]]; then
  # macOS: prefer Homebrew
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install from https://brew.sh/ and re-run this script."
    exit 1
  fi
  check_and_install magick "brew install imagemagick"
  check_and_install gifsicle "brew install gifsicle"
  check_and_install heif-convert "brew install libheif"
  check_and_install rsvg-convert "brew install librsvg"

elif [[ "$OS_NAME" == "Linux" ]]; then
  # Detect package manager
  if command -v apt-get >/dev/null 2>&1; then
    PM=apt
  elif command -v dnf >/dev/null 2>&1; then
    PM=dnf
  elif command -v pacman >/dev/null 2>&1; then
    PM=pacman
  else
    PM=unknown
  fi

  case "$PM" in
    apt)
      if confirm "Install imagemagick, gifsicle, libheif (apt)?"; then
        run_sudo apt-get update
        run_sudo apt-get install -y imagemagick gifsicle libheif-dev librsvg2-bin
      fi
      ;;
    dnf)
      if confirm "Install ImageMagick and gifsicle via dnf? (may require additional repos)"; then
        run_sudo dnf install -y ImageMagick gifsicle libheif librsvg2-python3
      fi
      ;;
    pacman)
      if confirm "Install imagemagick, gifsicle, libheif via pacman?"; then
        run_sudo pacman -Syu --noconfirm imagemagick gifsicle libheif librsvg
      fi
      ;;
    *)
      echo "Unknown package manager. Please install the following tools manually: imagemagick (magick), gifsicle, libheif (heif-convert), librsvg (rsvg-convert)."
      ;;
  esac

elif [[ "$OS_NAME" == CYGWIN* || "$OS_NAME" == MINGW* || "$OS_NAME" == MSYS* || "$OS_NAME" == "Windows_NT" ]]; then
  echo "On Windows, best options are using Chocolatey or winget in an elevated PowerShell:"
  echo "  choco install imagemagick gifsicle libheif -y"
  echo "  winget install ImageMagick.ImageMagick -e"
  echo "Alternatively download binaries from their project pages."
  exit 0

else
  echo "Unsupported OS: $OS_NAME. Please install dependencies manually."
  exit 1
fi

# Summary
echo "Installed/available tools:"
for t in magick gifsicle heif-convert rsvg-convert; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "  $t -> $(command -v $t)"
  else
    echo "  $t -> MISSING"
  fi
done

echo "If some tools are MISSING, please install them manually using your system package manager."
