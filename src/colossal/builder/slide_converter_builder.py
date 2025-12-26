"""SlideConverterBuilder

Build-time tool that reads the declarative manifest for slide conversions and
emits concrete Converter classes as Python files under `colossal/converters/slide/`.

Usage (from repository root):
    python src/colossal/builder/slide_converter_builder.py

Notes:
- Source manifest (by default): src/colossal/resources/formats/slide.json
- Output directory (by default): src/colossal/converters/slide/
"""
from __future__ import annotations

import json
from pathlib import Path
from colossal.utils.file_format import to_snake_case
import textwrap
import argparse

MANIFEST_PATH = Path(__file__).parents[1] / "resources" / "formats" / "slide.json"
OUTPUT_DIR = Path(__file__).parents[1] / "converters" / "slide"

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


def _render_pattern(pattern: str, input_name_no_ext: str, target_ext: str, page_number: int | None = None) -> str:
    out = pattern.replace('{{input_name_no_ext}}', input_name_no_ext).replace('{{output_ext}}', target_ext)
    if page_number is not None:
        out = out.replace('{{page_number}}', str(page_number))
    return out


class {class_name}(BaseConverter):
    """Convert slide to {to_fmt} using configured engine.

    input_formats = {input_formats}
    output_formats = [{output_fmt!r}]
    category = 'slide'
    options_schema = {{}}

    # manifest hints
    engine = {engine!r}
    mode = {mode!r}
    output_pattern = {output_pattern!r}
    output_type = {output_type!r}
    default_preset = {default_preset!r}
    """

    id = 'slide-to-{to_fmt}'
    name = 'Slide to {to_fmt_upper}'

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        _ensure_tool('{engine}')
        src = Path(task.input_path)
        dst = Path(task.output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        input_name_no_ext = src.stem
        target_ext = {to_fmt!r}

        # Mode-specific command construction
{mode_block}

        commands = [cmd]

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
    mode = conv.get('mode')
    output = conv.get('output') or {}
    pattern = output.get('pattern') or '{{input_name_no_ext}}.{{output_ext}}'
    multi_page = output.get('multi_page', False)

    pattern_literal = repr(pattern)
    engine_literal = repr(engine)

    lines: list[str] = []

    if mode in ('semantic', 'visual'):
        # Use LibreOffice (soffice) to convert documents to target format
        lines.extend([
            f"        # Convert using {engine}",
            f"        cmd = [shutil.which({engine_literal}), '--headless', '--convert-to', '{'{'}to_fmt{'}'}', '--outdir', str(dst.parent), str(src)]",
        ])

    elif mode == 'render':
        # Render slides/pages to images using poppler's pdftoppm (assumes input is pdf or can be converted beforehand)
        # multi_page -> export all pages
        fmt = conv.get('to') if isinstance(conv.get('to'), str) else (conv.get('to')[0] if isinstance(conv.get('to'), list) else 'png')
        flag_map = {'jpeg': 'jpeg', 'png': 'png', 'tiff': 'tiff', 'webp': 'png'}
        pdfflag = flag_map.get(fmt, 'png')
        if multi_page:
            lines.extend([
                "        # Export all pages to images using pdftoppm",
                "        out_prefix = str(Path(dst.parent) / (input_name_no_ext + '_page'))",
                f"        cmd = [shutil.which('pdftoppm'), '-{pdfflag}', str(src), out_prefix]",
            ])
        else:
            lines.extend([
                f"        out_path = Path(_render_pattern({pattern_literal}, input_name_no_ext, target_ext, page_number=None))",
                f"        cmd = [shutil.which('pdftoppm'), '-{pdfflag}', str(src), str(out_path.with_suffix(''))]",
            ])

    else:
        # fallback: try calling the engine with source and destination (generic)
        lines.extend([
            f"        cmd = [shutil.which({engine_literal}), str(src), str(dst)]",
        ])

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

    engine = conv.get('engine')

    mode_block = _build_mode_block(conv, engine)

    default_preset = conv.get('default_preset')
    preset_options = {}
    if default_preset:
        preset_options = manifest.get('presets', {}).get(default_preset, {})

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
        mode_block=mode_block,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
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
    p = argparse.ArgumentParser(prog='slide_converter_builder')
    p.add_argument('--manifest', '-m', type=Path,
                   default=MANIFEST_PATH,
                   help='Path to slide manifest JSON')
    p.add_argument('--out', '-o', type=Path,
                   default=OUTPUT_DIR,
                   help='Output directory for generated converters')
    p.add_argument('--no-force', dest='force', action='store_false', help='Do not overwrite existing files')
    args = p.parse_args(argv)

    created = build(args.manifest, args.out, force=args.force)
    print(f"Created {len(created)} files in {args.out}")


if __name__ == '__main__':
    main()

