"""AudioConverterBuilder

Build-time tool that reads the declarative manifest for audio conversions and
emits concrete Converter classes as Python files under `colossal/converters/audio/`.

Usage (from repository root):
    python src/colossal/builder/audio_converter_builder.py

Notes:
- Source manifest (by default): src/colossal/resources/formats/audio.json
- Output directory (by default): src/colossal/converters/audio/
"""
from __future__ import annotations

import json
from pathlib import Path
from colossal.utils.file_format import to_snake_case
import textwrap
import argparse

# Location of the manifest relative to project root
MANIFEST_PATH = Path(__file__).parents[1] / "resources" / "formats" / "audio.json"
OUTPUT_DIR = Path(__file__).parents[1] / "converters" / "audio"

TEMPLATE = textwrap.dedent('''
"""Auto-generated converter: {class_name}
Source manifest: {manifest}
"""
import contextlib
from pathlib import Path
import shutil
import subprocess

from colossal.core.base_converter import BaseConverter
from colossal.models.conversion_task import ConversionTask


def _ensure_tool(name: str) -> str:
    if path := shutil.which(name):
        return path
    else:
        raise RuntimeError(f"Required tool '{{name}}' not found in PATH")


class {class_name}(BaseConverter):
    """Convert audio to {to_fmt} using ffmpeg.

    input_formats = {input_formats}
    output_formats = [{output_fmt!r}]
    category = 'audio'
    options_schema = {{}}

    # manifest hints:
    output_pattern = {output_pattern!r}
    container = {container!r}
    mode = {mode!r}
    """

    id = 'audio-to-{to_fmt}'
    name = 'Audio to {to_fmt_upper}'

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        _ensure_tool('{engine}')
        src = Path(task.input_path)
        dst = Path(task.output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        cmd = [shutil.which('ffmpeg'), '-y', '-i', str(src)]

{codec_block}
{constraints_block}
{container_block}

        cmd += [str(dst)]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors='ignore') if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
            raise RuntimeError(f"ffmpeg failed converting {{src.name}}: {{stderr}}") from e

        # mark done
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            task.progress = 1.0
            if report_progress:
                report_progress(100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)
''')


def _codec_block(codec: str | None, mode: str | None) -> str:
    """Return code that sets audio codec flags according to codec and mode.

    Behavior:
      - If mode == 'copy' -> '-c:a copy' (ignore codec)
      - Otherwise, if codec is provided -> '-c:a codec'
      - If codec not provided and not copy -> do not set codec (let ffmpeg choose / infer)
    """
    if mode == 'copy':
        return "        cmd += ['-c:a', 'copy']"
    return f"        cmd += ['-c:a', '{codec}']" if codec else ""

def _constraints_block(constraints: dict | None) -> str:
    """Return a code block (string) that appends ffmpeg flags for common constraints.

    Supported constraints keys (from manifest):
      - sample_rate -> -ar
      - channels    -> -ac
      - bitrate     -> -b:a (accepts strings like '192k' or integers interpreted as bps)
    """
    if not constraints:
        return ""

    lines = []
    sample_rate = constraints.get('sample_rate')
    channels = constraints.get('channels')
    bitrate = constraints.get('bitrate')

    if sample_rate is not None:
        lines.append(f"        cmd += ['-ar', '{sample_rate}']")
    if channels is not None:
        lines.append(f"        cmd += ['-ac', '{channels}']")
    if bitrate is not None:
        if isinstance(bitrate, (int, float)):
            lines.append(f"        cmd += ['-b:a', '{int(bitrate)}k']")
        else:
            lines.append(f"        cmd += ['-b:a', '{bitrate}']")

    return "\n".join(lines)


def _container_block(container: str | None) -> str:
    """Return code that sets ffmpeg output container format if provided."""
    return f"        cmd += ['-f', '{container}']" if container else ""

def _generate_for_conversion(conv: dict, formats: list, manifest_path: Path, out_dir: Path, force: bool, created: list[Path], manifest: dict):
    tos = conv.get('to')
    targets = tos if isinstance(tos, list) else [tos]
    # filter out any None values to satisfy static analysis and avoid runtime errors
    targets = [t for t in targets if t is not None]
    if not targets:
        return

    froms = conv.get('from')
    # normalize input formats: use manifest formats if from == '*'
    if froms in ['*', ['*']]:
        input_formats = formats
    else:
        input_formats = froms if isinstance(froms, list) else [froms]

    codec = conv.get('codec')
    constraints = conv.get('constraints')
    mode = conv.get('mode')
    container = conv.get('container')
    output = conv.get('output') or {}
    output_pattern = output.get('pattern')
    engine = manifest.get('engine')

    for to_fmt in targets:
        # ensure to_fmt is a string (guard for static analysis and malformed manifests)
        if not isinstance(to_fmt, str):
            continue
        class_name = conv.get('name')
        filename = f"{to_snake_case(class_name)}_converter.py"
        out_path = out_dir / filename

        codec_block = _codec_block(codec, mode)
        constraints_block = _constraints_block(constraints)
        container_block = _container_block(container)

        content = TEMPLATE.format(
            class_name=class_name,
            manifest=str(manifest_path),
            input_formats=input_formats,
            output_fmt=to_fmt,
            engine=engine,
            to_fmt=to_fmt,
            to_fmt_upper=to_fmt.upper(),
            codec_block=codec_block,
            constraints_block=constraints_block,
            container_block=container_block,
            output_pattern=output_pattern,
            container=container,
            mode=mode
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
        _generate_for_conversion(conv, formats, manifest_path, out_dir, force, created, manifest)

    return created


def main(argv=None):
    p = argparse.ArgumentParser(prog='audio_converter_builder')
    p.add_argument('--manifest', '-m', type=Path,
                   default=MANIFEST_PATH,
                   help='Path to audio manifest JSON')
    p.add_argument('--out', '-o', type=Path,
                   default=OUTPUT_DIR,
                   help='Output directory for generated converters')
    p.add_argument('--no-force', dest='force', action='store_false', help='Do not overwrite existing files')
    args = p.parse_args(argv)

    created = build(args.manifest, args.out, force=args.force)
    print(f"Created {len(created)} files in {args.out}")

if __name__ == '__main__':
    main()