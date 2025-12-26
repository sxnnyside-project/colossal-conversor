"""VideoConverterBuilder

Build-time tool that reads the declarative manifest for video conversions and
emits concrete Converter classes as Python files under `colossal/converters/video/`.

Usage (from repository root):
    python src/colossal/builder/video_converter_builder.py

Notes:
- Source manifest (by default): src/colossal/resources/formats/video.json (expected)
- Output directory (by default): src/colossal/converters/video/
"""
from __future__ import annotations

import json
from pathlib import Path
from colossal.utils.file_format import to_snake_case
import textwrap
import argparse

# Location of the manifest relative to project root (video manifest)
MANIFEST_PATH = Path(__file__).parents[1] / "resources" / "formats" / "video.json"
OUTPUT_DIR = Path(__file__).parents[1] / "converters" / "video"

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

# Specific preset options for this converter (injected when present)
PRESET_OPTIONS = {preset_options}


class {class_name}(BaseConverter):
    """Convert video to {to_fmt} using configured engine.

    input_formats = {input_formats}
    output_formats = [{output_fmt!r}]
    category = 'video'
    options_schema = {{}}

    # manifest hints
    engine = {engine!r}
    mode = {mode!r}
    output_pattern = {output_pattern!r}
    output_type = {output_type!r}
    default_preset = {default_preset!r}
    """

    id = 'video-to-{to_fmt}'
    name = 'Video to {to_fmt_upper}'

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        _ensure_tool('{engine}')
        src = Path(task.input_path)
        dst = Path(task.output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        cmd = [shutil.which({engine!r}), '-y', '-i', str(src)]

        options = PRESET_OPTIONS.copy() if PRESET_OPTIONS else {{}}

{codec_block}
{extra_flags_block}

        cmd += [str(dst)]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors='ignore') if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
            raise RuntimeError(f"Engine failed converting {{src.name}}: {{stderr}}") from e

        # mark done
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            task.progress = 1.0
            if report_progress:
                report_progress(100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)
''')


def _codec_block(codecs: dict | None, mode: str | None) -> str:
    """Return a code block that appends codec flags to the ffmpeg command.

    codecs: mapping like { 'video': 'libx264', 'audio': 'aac' }
    mode: may affect flags (e.g., 'copy')
    """
    vcodec = codecs.get('video') if codecs and isinstance(codecs, dict) else None
    acodec = codecs.get('audio') if codecs and isinstance(codecs, dict) else None

    if mode == 'copy':
        return "        cmd += ['-c', 'copy']"

    lines: list[str] = [
        "        if options.get('video_codec'):",
        "            cmd += ['-c:v', options['video_codec']]",
    ]
    # video codec
    if vcodec:
        lines.extend(("        else:", f"            cmd += ['-c:v', '{vcodec}']"))
    lines.extend(
        (
            "        if options.get('audio_codec'):",
            "            cmd += ['-c:a', options['audio_codec']]",
        )
    )
    # audio codec
    if acodec:
        lines.extend(("        else:", f"            cmd += ['-c:a', '{acodec}']"))
    return "\n".join(lines)


def _extra_flags_block(flags: dict | None) -> str:
    """Return extra flags (bitrate, resolution, framerate)"""
    lines: list[str] = [
        "        if options.get('bitrate'):",
        "            cmd += ['-b:v', options['bitrate']]",
    ]
    # bitrate
    if flags and 'bitrate' in flags:
        lines.append(f"        else:\n            cmd += ['-b:v', '{flags['bitrate']}']")
    lines.extend(
        (
            "        if options.get('resolution'):",
            "            cmd += ['-s', options['resolution']]",
        )
    )
    # resolution
    if flags and 'resolution' in flags:
        lines.append(f"        else:\n            cmd += ['-s', '{flags['resolution']}']")
    lines.extend(
        (
            "        if options.get('framerate'):",
            "            cmd += ['-r', options['framerate']]",
        )
    )
    # framerate
    if flags and 'framerate' in flags:
        lines.append(f"        else:\n            cmd += ['-r', '{flags['framerate']}']")
    return "\n".join(lines)


def _generate_for_conversion(conv: dict, formats: list, manifest_path: Path, out_dir: Path, force: bool, created: list[Path], manifest: dict):
    tos = conv.get('to')
    targets = tos if isinstance(tos, list) else [tos]
    targets = [t for t in targets if t is not None]
    if not targets:
        return

    froms = conv.get('from')
    if froms in ['*', ['*']]:
        input_formats = formats
    else:
        input_formats = froms if isinstance(froms, list) else [froms]

    name = conv.get('name')
    filename = f"{to_snake_case(name)}.py"
    out_path = out_dir / filename

    # Compute only the specific preset options if a default preset exists
    default_preset = conv.get('default_preset')
    preset_options = {}
    if default_preset:
        preset_options = manifest.get('presets', {}).get(default_preset, {})

    # Resolve engine key -> executable
    engine_key = conv.get('engine')
    engine = manifest.get('engines', {}).get(engine_key, engine_key)

    codec_block = _codec_block(conv.get('codecs'), conv.get('mode'))
    effective_flags = conv.get('flags') or {
                    fk: preset_options[fk]
                    for fk in ('bitrate', 'resolution', 'framerate')
                    if fk in preset_options
                } or None

    extra_flags_block = _extra_flags_block(effective_flags)

    content = TEMPLATE.format(
        class_name=name,
        manifest=str(manifest_path),
        input_formats=input_formats,
        output_fmt=targets[0],
        to_fmt=targets[0],
        to_fmt_upper=str(targets[0]).upper(),
        preset_options=repr(preset_options),
        engine=engine,
        mode=conv.get('mode'),
        output_pattern=(conv.get('output') or {}).get('pattern'),
        output_type=(conv.get('output') or {}).get('type'),
        default_preset=default_preset,
        codec_block=codec_block,
        extra_flags_block=extra_flags_block,
    )

    if out_path.exists() and not force:
        print(f"Skipping existing {out_path}; use --force to overwrite")
        return

    out_path.write_text(content, encoding='utf-8')
    created.append(out_path)
    print(f"Wrote {out_path}")


def build(manifest_path: Path, out_dir: Path, force: bool = True) -> list[Path]:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    formats = manifest.get('formats', [])
    conversions = manifest.get('conversions', [])

    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for conv in conversions:
        _generate_for_conversion(conv, formats, manifest_path, out_dir, force, created, manifest)

    return created


def main(argv=None):
    p = argparse.ArgumentParser(prog='video_converter_builder')
    p.add_argument('--manifest', '-m', type=Path,
                   default=MANIFEST_PATH,
                   help='Path to video manifest JSON')
    p.add_argument('--out', '-o', type=Path,
                   default=OUTPUT_DIR,
                   help='Output directory for generated converters')
    p.add_argument('--no-force', dest='force', action='store_false', help='Do not overwrite existing files')
    args = p.parse_args(argv)

    created = build(args.manifest, args.out, force=args.force)
    print(f"Created {len(created)} files in {args.out}")


if __name__ == '__main__':
    main()