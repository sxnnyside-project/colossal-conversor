"""AudioConverterBuilder

Build-time tool that reads the declarative manifest for audio conversions and
emits concrete Converter classes as Python files under `colossal/converters/audio/`.

Usage (from repository root):
    python src/colossal/builder/audio_converter_builder.py

Notes:
- Source manifest (by default): src/colossal/resources/formats/audio.json
- Generated files are safe to re-run (will overwrite existing files). Use --out or --manifest
  to customize paths.
"""
from __future__ import annotations

import json
from pathlib import Path
import textwrap
import argparse


TEMPLATE = textwrap.dedent('''
"""Auto-generated converter: {class_name}
Source manifest: {manifest}
"""
from pathlib import Path
import shutil
import subprocess

from colossal.core.base_converter import BaseConverter
from colossal.models.conversion_task import ConversionTask


def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool '{{name}}' not found in PATH")
    return path


class {class_name}(BaseConverter):
    """Convert audio to {to_fmt} using ffmpeg.

    input_formats = {input_formats}
    output_formats = [{output_fmt!r}]
    category = 'audio'
    options_schema = {{}}
    """

    id = 'audio-to-{to_fmt}'
    name = 'Audio to {to_fmt_upper}'

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        _ensure_tool('ffmpeg')
        src = Path(task.input_path)
        dst = Path(task.output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        cmd = [shutil.which('ffmpeg'), '-y', '-i', str(src)]

{codec_block}

        cmd += [str(dst)]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors='ignore') if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
            raise RuntimeError(f"ffmpeg failed converting {{src.name}}: {{stderr}}")

        # mark done
        try:
            task.progress = 1.0
            if report_progress:
                report_progress(100.0)
        except (AttributeError, TypeError, ValueError):
            pass

    def convert(self, task: ConversionTask):
        return self.factory(task, None)
''')


def _make_class_name(to_fmt: str) -> str:
    # Prefer uppercase for extensions (MP3, M4A, etc.)
    return f"AudioTo{to_fmt.upper()}Converter"


def _make_filename(to_fmt: str) -> str:
    return f"{to_fmt.lower()}_converter.py"


def _codec_block(codec: str | None) -> str:
    if codec:
        return f"        cmd += ['-c:a', '{codec}']"
    # default: copy audio stream if codec not required
    return "        cmd += ['-c:a', 'copy']"


def _generate_for_conversion(conv: dict, formats: list, manifest_path: Path, out_dir: Path, force: bool, created: list[Path]):
    tos = conv.get('to')
    if isinstance(tos, list):
        targets = tos
    else:
        targets = [tos]

    # filter out any None values to satisfy static analysis and avoid runtime errors
    targets = [t for t in targets if t is not None]
    if not targets:
        return

    froms = conv.get('from')
    # normalize input formats: use manifest formats if from == '*'
    if froms == '*' or froms == ['*']:
        input_formats = formats
    else:
        input_formats = froms if isinstance(froms, list) else [froms]

    codec = conv.get('codec')

    for to_fmt in targets:
        # ensure to_fmt is a string (guard for static analysis and malformed manifests)
        if not isinstance(to_fmt, str):
            continue
        class_name = _make_class_name(to_fmt)
        filename = _make_filename(to_fmt)
        out_path = out_dir / filename

        codec_block = _codec_block(codec)

        content = TEMPLATE.format(
            class_name=class_name,
            manifest=str(manifest_path),
            input_formats=input_formats,
            output_fmt=to_fmt,
            to_fmt=to_fmt,
            to_fmt_upper=to_fmt.upper(),
            codec_block=codec_block
        )

        if out_path.exists() and not force:
            print(f"Skipping existing {out_path}; use --force to overwrite")
            continue

        out_path.write_text(content, encoding='utf-8')
        created.append(out_path)
        print(f"Wrote {out_path}")


def build(manifest_path: Path, out_dir: Path, force: bool = True) -> list[Path]:
    """Generate converter files. Returns list of created file paths."""
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    formats = manifest.get('formats', [])
    conversions = manifest.get('conversions', [])

    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for conv in conversions:
        _generate_for_conversion(conv, formats, manifest_path, out_dir, force, created)

    return created


def main(argv=None):
    p = argparse.ArgumentParser(prog='audio_converter_builder')
    p.add_argument('--manifest', '-m', type=Path,
                   default=Path(__file__).resolve().parents[1] / 'resources' / 'formats' / 'audio.json',
                   help='Path to audio manifest JSON')
    p.add_argument('--out', '-o', type=Path,
                   default=Path(__file__).resolve().parents[1] / 'converters' / 'audio',
                   help='Output directory for generated converters')
    p.add_argument('--no-force', dest='force', action='store_false', help='Do not overwrite existing files')
    args = p.parse_args(argv)

    created = build(args.manifest, args.out, force=args.force)
    print(f"Created {len(created)} files in {args.out}")


if __name__ == '__main__':
    main()

