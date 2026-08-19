# Changelog

All notable changes to **Colossal Conversor** are documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.0.0] — 2026-08-19

### Added

- C++20 Native Core runtime (`native/`) with pybind11 integration and GIL-released execution.
- Cross-platform `ProcessSupervisor`: POSIX backend (`process_posix.cpp`) for macOS/Linux and a Win32 backend (`process_windows.cpp`) using `CreateProcessW` and Job Objects for process-tree termination, selected per-platform at build time.
- In-process native zero-CLI image transcoding for BMP, PPM, and TGA formats.
- In-process native zero-CLI audio container transcoding and channel mixing for PCM/WAV.
- Fast binary magic-byte format detector and media inspector in C++.
- Formal conversion domain model (`ConversionRequest`, `ConversionPlan`, `ConversionPipeline`, `ConversionJob`, `ConversionBatch`, `ConversionArtifact`, `ConversionError`).
- Full 6-language internationalization subsystem (`en`, `es`, `fr`, `ja`, `pt`, `zh`) with zero-restart dynamic retranslation and persistent preferences.
- Authentic Windows 95-inspired desktop design system with 3D beveled geometry, classic blue header hierarchy, and pure black high-contrast typography.
- Coherent vector icon system with 13 bundled SVG icons (zero emoji UI).
- Native drag-and-drop file and directory intake with recursive batch scanning.
- Actionable error diagnostics dialog with expandable technical details.

### Changed

- Reconstructed entire execution pipeline: `UI → Application Services → Domain → Native Runtime → Native Engines → Artifacts`.
- Replaced monolithic synchronous converter runner with asynchronous cancellable multi-stage pipeline executor.
- Modernized command surface and developer workflows to DXQE v2.0.0 using `just`, `uv`, `hatchling`, `Ruff`, and `mypy` (strict mode).

### Removed

- Deleted legacy v3 dynamic converter builders, code generators, and monkey-patched docstring parsers.
- Deleted obsolete Phase 3 Python process runtime in favor of C++20 `ProcessSupervisor` and `ToolDiscovery`.
- Deleted unused PyInstaller spec files, unreferenced bash installation scripts, and dead utility functions.

---

[4.0.0]: https://github.com/sxnnyside-project/colossal-conservor/releases/tag/v4.0.0
