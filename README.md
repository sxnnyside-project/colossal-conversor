# Colossal Conversor

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![License](https://img.shields.io/badge/License-MIT-green)
[![CI](https://github.com/sxnnyside-project/colossal-conservor/workflows/CI/badge.svg)](https://github.com/sxnnyside-project/colossal-conservor/actions)

<p align="center">
  <strong>Offline-first ✦ Zero Cloud Dependencies ✦ Multi-format Engine</strong><br>
  <em>A privacy-first local file conversion desktop utility supporting audio, video, image, document, spreadsheet, and slide formats.</em>
</p>

<p align="center">
  <a href="#about">About</a> ✦
  <a href="#features">Features</a> ✦
  <a href="#installation">Installation</a> ✦
  <a href="#usage">Usage</a> ✦
  <a href="#architecture">Architecture</a> ✦
  <a href="#contributing">Contributing</a>
</p>

---

## About

**Colossal Conversor** is an offline desktop application designed to convert files across multiple media and document categories without relying on cloud services or external servers.

Most modern file conversion tools rely on remote APIs, introduce tracking, or require subscriptions for basic conversions. Colossal Conversor runs completely locally, combining a C++20 native execution core with a clean desktop interface to deliver predictable, fast, and privacy-respecting file transformations.

Conversions are processed through a structured domain model that coordinates both in-process native transcoders and controlled external engines through a multi-threaded, asynchronous C++ runtime.

### Philosophy

> _"Local hardware is sufficient for local data: conversion should be fast, private, and deterministic."_

Colossal Conversor is A Sxnnyside Project Release, part of the Sxnnyside Project's desktop utility ecosystem.

## Features

- **Multi-Category Conversion**: Converts audio, video, image, document, spreadsheet, and presentation formats.
- **C++20 Native Core**: GIL-released native execution with real-time progress streaming for external-tool conversions (e.g. ffmpeg).
- **In-Process Transcoding**: Built-in zero-CLI native encoders for raw image (BMP, PPM, TGA) and PCM audio manipulation.
- **Batch & Folder Intake**: Drag-and-drop support for individual files, multiple selections, and recursive directory scanning.
- **Multi-Output & Pipelines**: Handles 1-to-N page extraction and multi-stage intermediate conversions seamlessly.
- **Multilingual UI**: Native support for 6 languages (`en`, `es`, `fr`, `ja`, `pt`, `zh`) with dynamic zero-restart switching.
- **Windows 95 Aesthetics**: Classic 3D beveled desktop design language optimized for high contrast, legibility, and keyboard ergonomics.

## Platform Support

Colossal Conversor targets **macOS, Linux, and Windows**. The native process
supervisor has a dedicated backend per platform — POSIX (fork/exec/process
groups) on macOS and Linux, Win32 (`CreateProcessW` + Job Objects) on Windows
— so process creation, output capture, cancellation, and process-tree
cleanup behave the same way on every platform.

| Platform | Status                                                                              |
| -------- | ----------------------------------------------------------------------------------- |
| macOS    | Verified — built, tested, and used for day-to-day development                       |
| Linux    | Implemented (shares the macOS POSIX backend); not yet verified on a Linux runner    |
| Windows  | Implemented against the documented Win32 APIs; not yet verified on a Windows runner |

CI coverage for Linux and Windows is tracked in [CI](https://github.com/sxnnyside-project/colossal-conservor/actions). Contributions verifying either platform are especially welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Installation

### Prerequisites

- Python (>= 3.10)
- CMake (>= 3.20) and a C++20-compliant compiler (Clang/GCC on macOS/Linux, MSVC on Windows — see [Platform Support](#platform-support) for verification status)
- External engines for specialized formats (optional, detected at runtime):
  - `ffmpeg` (for complex video/audio codecs)
  - `libreoffice` / `soffice` (for office documents, spreadsheets, slides)
  - `pdftoppm` (for PDF rendering)
  - `pandoc` (for markup documents)

### From Source

```bash
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor

# Install dependencies and build native extension via just
just install
```

## Usage

```bash
# Launch the desktop application
just dev

# Or run directly via python package entry point
uv run colossal
```

To run conversions:

1. Drag and drop files or folders into the intake area (or click **Select File(s)** / **Select Folder**).
2. Choose your target output format from the categorized grid.
3. Select an output destination with **Save As...**.
4. Click **Convert** (or press <kbd>Enter</kbd>) to start conversion.

## Architecture

```
colossal-conservor/
├── native/          # C++20 native runtime, supervisor, and in-process engines
├── src/colossal/    # Python domain, UI, i18n subsystem, and application services
└── tests/           # Comprehensive domain, native, and UI test suites
```

The application adheres to a strict layered topology:

```text
PySide6 Presentation (UI)
        ↓
Application Services (ConversionApplicationService)
        ↓
Domain Model (Request, Plan, Job, Batch, Pipeline, Artifact, Error)
        ↓
Python ↔ C++ Boundary (pybind11 / colossal_native)
        ↓
C++20 Native Runtime (NativeRuntime, ProcessSupervisor, ToolDiscovery)
        ↓
Native Engines & Controlled Binaries
        ↓
Produced Artifacts
```

## Notes

Localized user guides (batches, multi-output conversions, pipelines,
cancellation, troubleshooting) live in [docs/guides/](docs/guides/):
[English](docs/guides/en/README.md) · [Español](docs/guides/es/README.md) · [Français](docs/guides/fr/README.md) · [日本語](docs/guides/ja/README.md) · [Português](docs/guides/pt/README.md) · [中文](docs/guides/zh/README.md)

## Contributing

Contributions are accepted. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Before contributing, read the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Colossal Conversor</strong> — A Sxnnyside Project Release<br>
  <em>&copy; 2026 Sxnnyside Project</em>
</p>
