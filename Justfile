set shell := ["bash", "-uc"]

# Default recipe: show available commands
default:
    @just --list

# Compile C++ native core extension
native-build:
    uv run cmake -B build/native -S native -DPython_EXECUTABLE="$(uv run python -c 'import sys; print(sys.executable)')" -Dpybind11_DIR="$(uv run python -c 'import pybind11; print(pybind11.get_cmake_dir())')"
    uv run cmake --build build/native --config Release

# Install/sync all dependencies and build native extension
install:
    uv sync --all-groups
    @just native-build

# Run application in development mode
dev: native-build
    uv run python -m colossal.main

# Build package artifacts (wheel and sdist)
build: native-build
    uv build

# Run test suite with pytest
test: native-build
    uv run pytest

# Run native test suite under AddressSanitizer and UndefinedBehaviorSanitizer
test-sanitizers:
    uv run cmake -B build/native-asan -S native -DENABLE_SANITIZERS=ON -Dpybind11_DIR="$(uv run python -c 'import pybind11; print(pybind11.get_cmake_dir())')"
    uv run cmake --build build/native-asan --config Debug
    @just native-build

# Run strict static type checking with mypy
typecheck:
    uv run mypy src tests

# Run linter with Ruff
lint:
    uv run ruff check .

# Format codebase with Ruff and clang-format
format:
    uv run ruff format .
    find native/src native/include -name "*.cpp" -o -name "*.hpp" | xargs clang-format -i 2>/dev/null || true

# Check formatting without modifying files
format-check:
    uv run ruff format --check .

# Run complete quality gate
check: format-check lint typecheck test build

# Clean build artifacts, cache directories, and bytecode
clean:
    rm -rf dist build .pytest_cache .mypy_cache .ruff_cache src/*.egg-info src/colossal/*.egg-info src/colossal/*.so src/colossal/*.dylib src/colossal/*.pyd
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Report which external conversion tools (ffmpeg, LibreOffice, Poppler, Pandoc, ImageMagick) are on PATH
verify-tools:
    uv run python3 tools/verify_deps.py

# Install external conversion tools via the platform's package manager (macOS/Linux; run tools/windows_install_deps.ps1 directly on Windows)
install-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    case "$(uname -s)" in
        Darwin) bash tools/macos_install_deps.sh ;;
        Linux) bash tools/linux_install_deps.sh ;;
        *) echo "Run tools/windows_install_deps.ps1 in PowerShell on Windows." >&2; exit 1 ;;
    esac

# Validate the localized user guides for structural consistency
check-docs:
    uv run python3 docs/validate_guides.py
