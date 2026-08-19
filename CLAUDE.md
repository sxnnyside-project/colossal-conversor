# CLAUDE.md — Colossal Conversor Developer & Agent Guide

## 1. Project Overview & Purpose
**Colossal Conversor** is an offline multi-format file conversion desktop utility featuring a **C++20 native runtime core**, a **PySide6 presentation layer**, pure domain-driven execution, and a 6-language internationalization subsystem (`en`, `es`, `fr`, `ja`, `pt`, `zh`).

> **Topology:** Dual Python/C++ Architecture (`src/colossal` + `native/` bound via `pybind11`).

---

## 2. Technical Stack Profile & Tooling
The project adheres to the **DXQE v2.0.0** Multi-Language Stack Profile:

| Category | Tool | Configuration / Notes |
| :--- | :--- | :--- |
| **Package / Environment Manager** | `uv` | Canonical package and environment runner (`uv sync`, `uv run`) |
| **Build Backend (Python)** | `hatchling` | Standard PEP 517 build via `uv build` |
| **Native Build System (C++)** | `CMake` (>= 3.20) | C++20 shared library compilation with `pybind11` |
| **Linter & Formatter** | `Ruff` | Deterministic formatting and strict production linting |
| **Type Checker** | `mypy` (strict mode) | Strict static type checking across `src/` and `tests/` |
| **Testing Framework** | `pytest` | Comprehensive domain, native, and UI test execution |
| **Git Hooks** | `pre-commit` | Automated formatting, linting, and hygiene verification |
| **Command Surface** | `just` | Standard contributor-facing command abstraction |

---

## 3. Standard Command Surface (`just`)
All contributor and agent operations **must** go through `just`:

```bash
just install       # Sync virtualenv, install dependencies, and build native C++ core
just dev           # Launch desktop application in development mode
just build         # Compile native C++ extension and build distribution packages (wheel & sdist)
just test          # Run test suite via pytest
just typecheck     # Run strict static type checking via mypy
just lint          # Run linter via ruff check
just format        # Format codebase via ruff format
just format-check  # Verify formatting deterministically without modifying files
just check         # Run full quality gate (format-check, lint, typecheck, cmake build, test, build)
just clean         # Clean build artifacts, CMake outputs, temporary caches, and bytecode
```

---

## 4. Architecture Overview

```text
Colossal-Conversor/
├── native/                             # C++20 Native Core
│   ├── CMakeLists.txt                  # CMake build configuration for pybind11 module
│   ├── include/colossal/               # C++ engine, runtime, inspector, supervisor headers
│   │   ├── artifact.hpp, capability.hpp, discovery.hpp, engine.hpp, error.hpp
│   │   ├── image_engine.hpp, audio_engine.hpp, inspector.hpp, job.hpp, pipeline.hpp
│   │   ├── process.hpp, request.hpp, result.hpp, runtime.hpp, types.hpp
│   └── src/                            # Implementation files
│       ├── bindings.cpp                # pybind11 module bindings
│       ├── discovery.cpp               # C++ binary tool discovery & caching
│       ├── inspector.cpp               # Fast binary magic-byte format detection
│       ├── process.cpp                 # Multi-platform process supervisor & timeouts
│       ├── runtime.cpp                 # Engine registry & sequential job execution
│       └── engines/                    # In-process and controlled CLI engines
│           ├── native_image_engine.cpp # In-process BMP/PPM/TGA transcoding
│           ├── native_audio_engine.cpp # In-process PCM/WAV manipulation & mixing
│           ├── ffmpeg_engine.cpp       # Controlled FFmpeg audio/video transcode
│           ├── libreoffice_engine.cpp  # Controlled LibreOffice document transcode
│           ├── poppler_engine.cpp      # Controlled pdftoppm rendering
│           └── pandoc_engine.cpp       # Controlled Pandoc markup translation
├── src/colossal/
│   ├── app.py                          # Application bootstrap
│   ├── colossal_native.pyi             # Native pybind11 module type stubs
│   ├── main.py                         # Canonical CLI launcher
│   ├── domain/                         # Pure Python Domain Model (zero external deps)
│   │   ├── artifact.py, batch.py, capability.py, cardinality.py, error.py
│   │   ├── format.py, job.py, pipeline.py, plan.py, request.py, resolver.py, result.py
│   ├── i18n/                           # Internationalization Subsystem
│   │   ├── locales.py                  # Supported languages (en, es, fr, ja, pt, zh)
│   │   ├── settings.py                 # Persistent user preferences (~/.config/colossal/)
│   │   ├── translator.py               # Pluralization & parameter interpolation
│   │   └── translations/               # 6 localized JSON translation dictionaries
│   ├── resources/                      # Assets & Format Manifests
│   │   ├── format_manifest.json        # Normalized format definitions & MIME metadata
│   │   ├── formats/                    # Category conversion rules (audio, image, document, etc.)
│   │   ├── icons/                      # 13 scalable SVG vector icons
│   │   └── theme.qss                   # Windows 95-inspired 3D beveled stylesheet
│   ├── runtime/                        # Python Runtime Integration
│   │   ├── catalog.py                  # FormatCatalog metadata loader & validator
│   │   └── native_runner.py            # NativeJobRunner pybind11 adapter
│   ├── services/                       # Application Services
│   │   └── conversion_service.py       # ConversionApplicationService facade
│   ├── ui/                             # Presentation Layer (PySide6)
│   │   ├── main_window.py              # Windows 95 main desktop window & drag-and-drop
│   │   └── theme.py                    # Design tokens, font helpers & icon loaders
│   └── utils/
│       └── file_format.py              # Format detection utility facade
└── tests/                              # Comprehensive Test Suite
    ├── conftest.py                     # Shared domain fixtures
    ├── domain/                         # Domain model & pipeline tests (11 suites)
    ├── native/                         # C++20 engine & supervisor tests (9 suites)
    ├── runtime/                        # Format catalog tests
    └── ui/                             # Application service & i18n tests
```

---

## 5. Architectural Invariants

When working on this repository, strictly maintain these core invariants:

1. **Clean Domain Separation:** The `domain/` package must never depend on PySide6, subprocess, external CLIs, or Qt widgets.
2. **Native Execution Authority:** Process lifecycle, concurrency, timeout enforcement, cancellation, and in-process transcoding belong in `native/` (C++20).
3. **No Emoji in UI:** All UI icons must be vector SVGs from `resources/icons/` loaded via `get_icon()`.
4. **Multilingual Completeness:** Any new user-facing string must have corresponding entries in all 6 translation files (`en.json`, `es.json`, `fr.json`, `ja.json`, `pt.json`, `zh.json`).
5. **No Fictitious Green Gates:** Never lower tooling strictness, silence errors, or exclude paths to make `just check` pass.
