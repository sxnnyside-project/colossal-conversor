# Dependency Provisioning Tools

Colossal Conversor's native `ToolDiscovery` finds external conversion tools
on `PATH` at runtime — it never installs anything itself. The scripts here
are a convenience layer for getting those tools onto `PATH` in the first
place, using each platform's native package manager. They are optional:
if you already have the tools installed some other way, `ToolDiscovery`
will find them regardless of how they got there.

## Dependency model

| Tool | Package | Used for |
|---|---|---|
| `ffmpeg` | `ffmpeg` | Audio and video conversions |
| `soffice` | LibreOffice | Document (office formats, PDF rendering), spreadsheet, and slide/presentation conversions |
| `pdftoppm` | Poppler (`poppler`/`poppler-utils`) | Document → image page rendering |
| `pandoc` | Pandoc | Markdown ↔ document format conversions |
| `magick` | ImageMagick | Image conversions not handled by the built-in native encoder (SVG, GIF, and formats other than BMP/PPM/TGA) |

Image conversions among BMP, PPM, and TGA, and PCM/WAV audio manipulation,
run entirely in-process (`native/src/engines/native_image_engine.cpp`,
`native_audio_engine.cpp`) and need no external tool at all.

This list is not the v3 dependency list — it reflects what
`native/src/runtime.cpp` actually registers and what
`src/colossal/resources/formats/*.json` actually routes through. In
particular, ImageMagick is included because the current image engine
(`magick_engine.cpp`) is genuinely the default/SVG/GIF handler today, not
because v3 happened to use it.

## Scripts

| Script | Platform | Package manager |
|---|---|---|
| `macos_install_deps.sh` | macOS | Homebrew |
| `linux_install_deps.sh` | Linux | apt, dnf, or pacman (auto-detected) |
| `windows_install_deps.ps1` | Windows | winget (preferred), falls back to Chocolatey if present |
| `verify_deps.py` | All | — (reports what `ToolDiscovery` would actually find on `PATH`) |

Each installer:
- checks whether its package manager is present before doing anything;
- checks whether each tool is already resolvable on `PATH` and skips it if so;
- installs only the packages above, nothing else;
- never pipes a remote script into a shell, downloads a bare binary, or
  silently elevates privileges — it uses the package manager's own install
  command, which prompts for `sudo`/admin itself when it needs to;
- reports success/failure per tool rather than failing silently.

Run `just verify-tools` (or `python3 tools/verify_deps.py` directly) to see
the current state without installing anything.
