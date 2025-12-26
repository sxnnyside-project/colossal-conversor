"""ImageConverterBuilder

Build-time tool that reads the declarative manifest for image conversions and
emits concrete Converter classes as Python files under `colossal/converters/image/`.

Usage (from repository root):
    python src/colossal/builder/image_converter_builder.py

Notes:
- Source manifest (by default): src/colossal/resources/formats/image.json
- Output directory (by default): src/colossal/converters/image/
"""
from __future__ import annotations

import json
from pathlib import Path
from colossal.utils.file_format import to_snake_case
import textwrap
import argparse

MANIFEST_PATH = Path(__file__).parents[1] / "resources" / "formats" / "image.json"
OUTPUT_DIR = Path(__file__).parents[1] / "converters" / "image"

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


# Specific preset options for this converter (injected when present)
PRESET_OPTIONS = {preset_options}

def _ensure_tool(name: str) -> str:
    if path := shutil.which(name):
        return path
    else:
        raise RuntimeError(f"Required tool '{{name}}' not found in PATH")

def _render_pattern(pattern: str, input_name_no_ext: str, target_ext: str, size: str | int | None = None, frame_number: int | None = None) -> str:
    out = pattern.replace('{{input_name_no_ext}}', input_name_no_ext).replace('{{target_ext}}', target_ext)
    if size is not None:
        out = out.replace('{{size}}', str(size))
    if frame_number is not None:
        out = out.replace('{{frame_number}}', str(frame_number))
    return out


class {class_name}(BaseConverter):
    """Convert image to {to_fmt} using configured engine.

    input_formats = {input_formats}
    output_formats = [{output_fmt!r}]
    category = 'image'
    options_schema = {{}}

    # manifest hints
    engine = {engine!r}
    mode = {mode!r}
    output_pattern = {output_pattern!r}
    output_type = {output_type!r}
    default_preset = {default_preset!r}
    family = {family!r}
    type_hint = {type_hint!r}
    """

    id = 'image-to-{to_fmt}'
    name = 'Image to {to_fmt_upper}'

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        _ensure_tool('{engine}')
        src = Path(task.input_path)
        dst = Path(task.output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        input_name_no_ext = src.stem
        target_ext = {to_fmt!r}

        # Resolve preset options: builder injected PRESET_OPTIONS when default preset exists
        options = PRESET_OPTIONS.copy() if PRESET_OPTIONS else {{}}

        # Validar output.type
        if {output_type!r} not in (None, "file", "single_file", "multi_file"):
            raise RuntimeError("Unsupported output.type: {output_type!r}")

        # Mode-specific command construction
{mode_block}

        commands = [cmd]

        # Execute commands (single or multiple)
        try:
            for cmd in commands:
                subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Engine failed converting {{src.name}}: {{e}}") from e

        # mark done
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            task.progress = 1.0
            if report_progress:
                report_progress(100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)
''')


def _build_mode_block(conv: dict, engine: str) -> str:
    """Return the Python code block for mode-specific command generation.

    This generates code that fills `commands` list used by the template.
    """
    mode = conv.get('mode')
    output = conv.get('output') or {}
    pattern = output.get('pattern') or '{{input_name_no_ext}}.{{target_ext}}'
    multi_size = output.get('multi_size', False)
    multi_frame = output.get('multi_frame', False)

    pattern_literal = repr(pattern)
    engine_literal = repr(engine)

    lines: list[str] = []

    if mode in ('raster_convert', 'lossy_convert', 'lossy_or_lossless'):
        # Use ImageMagick (magick) with common flags from preset: max_width, quality, strip_metadata, background, colorspace
        lines.extend([
            "        # Using ImageMagick 'magick' for raster conversion",
            f"        args = [shutil.which({engine_literal}), str(src), '-auto-orient']",
            "        # apply max_width -> -resize {{max_width}}\\\n        if 'max_width' in options:",
            "            args += ['-resize', str(options['max_width'])]",
            "        if options.get('strip_metadata'):",
            "            args += ['-strip']",
            "        if 'quality' in options:",
            "            args += ['-quality', str(options['quality'])]",
            "        if 'colorspace' in options:",
            "            args += ['-colorspace', str(options['colorspace'])]",
        ])

        if multi_size:
            lines.extend([
                "        # Multi-size outputs using configured engine",
                "        sizes = options.get('sizes', [])",
                "        if not sizes:",
                "            sizes = []",
                "        for s in sizes:",
                f"            out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext, size=s))",
                "            cmd = args + [str(out_path)]",
            ])
        else:
            lines.extend([
                "        # Single output file",
                f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext))",
                "        cmd = args + [str(out_path)]",
            ])

    elif mode == 'multi_raster':
        lines.extend([
            "        # Multi-size raster outputs (e.g., ICO) using ImageMagick",
            f"        args = [shutil.which({engine_literal}), str(src)]",
            "        sizes = options.get('sizes', [])",
            "        for s in sizes:",
            f"            out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext, size=s))",
            "            cmd = args + ['-resize', f'{str(s)}x{str(s)}', str(out_path)]",
        ])

    elif mode == 'vector_rasterize':
        lines.extend([
            "        # Vector rasterization using configured engine",
            f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext))",
            f"        cmd = [shutil.which({engine_literal}), str(src), str(out_path)]",
        ])

    elif mode == 'first_frame':
        lines.extend([
            "        # Extract first frame from animated input",
            f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext))",
            f"        cmd = [shutil.which({engine_literal}), f'{{str(src)}}[0]', str(out_path)]",
        ])

    elif mode == 'animated_convert':
        if multi_frame:
            lines.extend([
                "        # Export all frames from animated input using configured engine",
                f"        out_pattern = str(Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext)).as_posix()).replace('{{frame_number}}', '%04d')",
                f"        cmd = [shutil.which({engine_literal}), str(src), out_pattern]",
            ])
        else:
            lines.extend([
                "        # Extract first frame from animated input",
                f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext))",
                f"        cmd = [shutil.which({engine_literal}), f'{{str(src)}}[0]', str(out_path)]",
            ])

    elif mode == 'decode':
        lines.extend([
            "        # Decode-only mode using configured image engine",
            f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext))",
            f"        cmd = [shutil.which({engine_literal}), str(src), str(out_path)]",
        ])

    else:
        lines.extend(
            [
                "        # Fallback: try configured image engine to convert to target extension",
                f"        args = [shutil.which({engine_literal}), str(src)]",
                f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext))",
                f"        cmd = [shutil.which({engine_literal}), str(src), str(out_path)]",
             ]
         )

    return '\n'.join(lines)


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

    # Resolve engine key (manifest stores mapping like 'default' -> 'imagemagick')
    engine_key = conv.get('engine')
    engine = manifest.get('engines', {}).get(engine_key, engine_key)

    # Build mode block (pass the resolved engine name so generated code
    # uses the actual executable via shutil.which(engine))
    mode_block = _build_mode_block(conv, engine)

    # Compute only the specific preset options if a default preset exists
    default_preset = conv.get('default_preset')
    preset_options = {}
    if default_preset:
        preset_options = manifest.get('presets', {}).get(default_preset, {})

    # Determine family and type_hint minimally
    family = conv.get('family') or next((f for f, members in manifest.get('families', {}).items() if targets[0] in members), None)
    type_hint = conv.get('type') or next((t for t, members in manifest.get('types', {}).items() if targets[0] in members), None)

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
        family=family,
        type_hint=type_hint,
        mode_block=mode_block,
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
    p = argparse.ArgumentParser(prog='image_converter_builder')
    p.add_argument('--manifest', '-m', type=Path,
                   default=MANIFEST_PATH,
                   help='Path to image manifest JSON')
    p.add_argument('--out', '-o', type=Path,
                   default=OUTPUT_DIR,
                   help='Output directory for generated converters')
    p.add_argument('--no-force', dest='force', action='store_false', help='Do not overwrite existing files')
    args = p.parse_args(argv)

    created = build(args.manifest, args.out, force=args.force)
    print(f"Created {len(created)} files in {args.out}")


if __name__ == '__main__':
    main()

