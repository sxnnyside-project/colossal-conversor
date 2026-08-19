# Colossal Conversor — User Guide

<p align="center">
  <em>Everything you need to install, run, and troubleshoot Colossal Conversor day to day.</em>
</p>

<p align="center">
  <sub>Languages: <a href="../en/README.md">English</a> · <a href="../es/README.md">Español</a> · <a href="../fr/README.md">Français</a> · <a href="../ja/README.md">日本語</a> · <a href="../pt/README.md">Português</a> · <a href="../zh/README.md">中文</a></sub>
</p>

---

## 1. What is Colossal Conversor?

Colossal Conversor is an offline desktop application for converting files
across audio, video, image, document, spreadsheet, and presentation formats.
Everything runs locally through a C++20 native execution core — there is no
cloud upload, no account, and no network dependency for the conversion
itself. See the main [README](../../../README.md) for the full technical
overview.

This guide covers how to actually use the application day to day: installing
it, running your first conversion, working with batches and pipelines, and
recovering when something goes wrong.

## 2. Supported Platforms

Colossal Conversor targets **macOS, Linux, and Windows**. The native process
supervisor has a dedicated backend per platform, so process creation, output
capture, cancellation, and cleanup behave the same way everywhere.

| Platform | Status |
|---|---|
| macOS | Verified — built, tested, and used for day-to-day development |
| Linux | Implemented (shares the macOS backend); not yet verified on a Linux runner |
| Windows | Implemented against the Windows process APIs; not yet verified on a Windows runner |

"Implemented but not yet verified" means the code exists and is written to
the correct platform contracts, but no one has yet confirmed a real
conversion succeeds on that platform. This will be updated as verification
happens — see the main README's Platform Support section for the current
status, and [CONTRIBUTING.md](../../../CONTRIBUTING.md) if you'd like to help verify Linux or Windows.

## 3. Installation

Installing Colossal Conversor itself is separate from installing the
external tools it uses for some conversions (see the External Dependencies
section below).

### macOS / Linux

```bash
git clone https://github.com/sxnnyside-project/colossal-conversor.git
cd colossal-conversor
just install
just dev
```

### Windows

```powershell
git clone https://github.com/sxnnyside-project/colossal-conversor.git
cd colossal-conversor
just install
just dev
```

`just install` syncs Python dependencies and builds the native extension.
`just dev` launches the application. If you don't have `just`, see its
[installation instructions](https://github.com/casey/just#installation) — or
run the equivalent `uv sync --all-groups` followed by the native CMake build
described in the main README.

## 4. External Dependencies

Some conversion categories call an external tool; others run entirely
in-process and need nothing extra.

| Tool | Needed for |
|---|---|
| FFmpeg | Audio and video conversions |
| LibreOffice | Document, spreadsheet, and slide/presentation conversions |
| Poppler (`pdftoppm`) | Document → image page rendering |
| Pandoc | Markdown ↔ document conversions |
| ImageMagick | Image conversions other than BMP/PPM/TGA (which run natively, no tool needed) |

To check what's already available:

```bash
just verify-tools
```

To install what's missing:

- **macOS**: `bash tools/macos_install_deps.sh` (Homebrew)
- **Linux**: `bash tools/linux_install_deps.sh` (apt, dnf, or pacman — auto-detected)
- **Windows**: run `tools/windows_install_deps.ps1` in PowerShell (winget, or Chocolatey if already installed)

Installing these tools does **not** by itself guarantee every conversion
will work — it makes the relevant engine available. The application detects
each tool at runtime and only offers conversions it can actually execute.

## 5. First Conversion

1. Launch the app (`just dev`).
2. Click **Select File(s)** or drag a file into the intake area.
3. Colossal Conversor detects the input format and shows only the target
   formats it can actually produce from it, grouped by category.
4. Click a target format.
5. Click **Save As...** to choose (or confirm) the destination, if you want
   something other than the default.
6. Click **Convert** (or press <kbd>Enter</kbd>).

When it finishes, a dialog reports how many files were produced, with
buttons to open the result or reveal it in your file manager.

## 6. Multiple Files

Click **Select File(s)** and choose more than one file, or drag several
files at once. Colossal Conversor shows only the output formats common to
every selected input. Choose a destination **folder** (not a single file)
via **Save As...**, then **Convert** — each input produces its own output
in that folder.

## 7. Multi-Output Conversions

Some conversions produce more than one file from a single input — for
example, rendering each page of a PDF as a separate image. These are
detected automatically from the format pair you choose; the destination you
pick becomes a folder containing all the produced pages, and the completion
dialog reports the actual number of files generated.

## 8. Pipelines

A few conversions can't happen in a single step and are automatically
broken into stages internally — for example, a presentation converted to an
image goes through an intermediate PDF first. You don't need to configure
this: pick your input and target format as usual, and the progress bar
shows which stage is currently running. Intermediate files are cleaned up
automatically once the pipeline finishes (or if it fails or is cancelled).

## 9. Choosing an Output Format

The format grid only ever shows targets Colossal Conversor can actually
produce from your current input — it does not advertise conversions it
can't run. When you select a format, a fidelity note appears (e.g. "high",
"medium", "layout") describing how closely the output preserves the
original — useful when converting between formats with different
capabilities (e.g. a styled document to plain text).

## 10. Destination Selection

**Save As...** lets you pick where the output goes. For a single-output
conversion, pick a file path; for a batch or a multi-output conversion,
pick a folder. If you don't choose explicitly, the app proposes a sensible
default next to the input file.

## 11. Cancellation

Click **Cancel** while a conversion is running to stop it. This actually
terminates the underlying process (not just the UI state) — no partial
output is reported as a successful result, and the status bar reads
"Conversion cancelled," distinct from both success and failure. You can
start a new conversion immediately afterward.

## 12. Errors and Recovery

If a conversion fails, a dialog explains what happened in plain language,
with a **Show Details...** button for the underlying technical output (only
shown if you ask for it). The application does not crash or lock up on a
failed conversion — dismiss the dialog and try again, adjusting the input,
target format, or destination as needed.

## 13. Missing Dependencies

If a conversion needs a tool that isn't installed, the error message says
so explicitly and names the tool — it will not be confused with a generic
failure. Run `just verify-tools` to see the full picture, and see the
External Dependencies section above for how to install what's missing.

## 14. Supported Formats

The format grid inside the application is the authoritative, live list —
it's generated from the same catalog the conversion engine uses, so it can
never advertise something the current build can't actually do. In broad
terms, Colossal Conversor supports:

- **Audio**: common formats such as MP3, WAV, FLAC, AAC, OGG, and others.
- **Video**: common formats such as MP4, MKV, MOV, AVI, WebM, and others.
- **Image**: common formats such as PNG, JPEG, WebP, BMP, TIFF, GIF, and others.
- **Document**: DOC/DOCX, ODT, RTF, TXT, PDF, Markdown, HTML, EPUB.
- **Spreadsheet**: XLS/XLSX, ODS, CSV, TSV.
- **Presentation**: PPTX/PPT, ODP.

Select an input file in the application to see the exact, current list of
targets for that specific file.

## 15. Troubleshooting

**A conversion I expect to work isn't offered.** The target format list is
generated from your specific input's detected format — double-check the
input was detected correctly (shown next to the file name), and that the
conversion you want is actually supported for that pair.

**"Missing dependency" error.** Run `just verify-tools`, then install the
named tool (see External Dependencies / Missing Dependencies above).

**Conversion fails immediately.** Check **Show Details...** in the error
dialog. Common causes: a corrupted or unreadable input file, or a format
the detected input doesn't actually match (e.g. a file renamed with the
wrong extension).

**Cancel doesn't seem to do anything visually.** For very short conversions,
the operation may finish before Cancel registers — this is expected, not a
bug; the result will be a normal success or failure, not a stuck UI.

**The destination path is invalid.** Make sure the folder exists and you
have write permission to it; for a single-file output, make sure the parent
folder exists.

**Still stuck?** Open an issue — see [SUPPORT.md](../../../SUPPORT.md).

---

<p align="center">
  <sub>Part of the <a href="../../../README.md">Colossal Conversor</a> documentation — A Sxnnyside Project Release</sub>
</p>
