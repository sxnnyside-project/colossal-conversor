"""
ImageConverterBuilder
Reads resources/formats/image.json and generates per-target converter modules in
colossal/converters/image/ as standalone files.

Usage (project root):
    python3 src/colossal/builder/image_converter_builder.py

The builder is intended for build-time use only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

# Location of the manifest relative to project root
MANIFEST_PATH = Path(__file__).parents[1] / "resources" / "formats" / "image.json"
OUTPUT_DIR = Path(__file__).parents[1] / "converters" / "image"


def _class_name_for(target: str) -> str:
    return f"ImageTo{target.upper()}Converter"


def _file_name_for(target: str) -> str:
    return f"{target.lower()}_converter.py"


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_manifest(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _render_imports(need_cairosvg: bool, need_heif: bool, need_bytesio: bool) -> str:
    """Return import block as string ensuring future-import is first line."""
    lines: List[str] = [
        "from __future__ import annotations",
    ]

    # optional backends - place after future import
    if need_heif:
        lines.extend([
            "try:",
            "    import pillow_heif  # noqa: F401",
            "    _HAS_PILLOW_HEIF = True",
            "except ImportError:",
            "    _HAS_PILLOW_HEIF = False",
            "",
        ])

    if need_cairosvg:
        lines.extend([
            "try:",
            "    import cairosvg",
            "except ImportError:",
            "    cairosvg = None",
            "",
        ])

    # common imports - include BytesIO only if cairosvg will be used and this file uses it
    if need_cairosvg and need_bytesio:
        lines.extend([
            "from pathlib import Path",
            "from typing import Callable, Optional",
            "from io import BytesIO",
            "from PIL import Image",
            "from colossal.core.base_converter import BaseConverter",
            "from colossal.models.conversion_task import ConversionTask",
        ])
    else:
        lines.extend([
            "from pathlib import Path",
            "from typing import Callable, Optional",
            "from PIL import Image",
            "from colossal.core.base_converter import BaseConverter",
            "from colossal.models.conversion_task import ConversionTask",
        ])

    return "\n".join(lines)


def _render_png_factory() -> str:
    return (
        "    @staticmethod\n"
        "    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:\n"
        "        # simple open -> save flow using Pillow\n"
        "        src = Path(task.input_path)\n"
        "        dst = Path(task.output_path)\n"
        "        dst.parent.mkdir(parents=True, exist_ok=True)\n"
        "        # handle SVG input via cairosvg if available\n"
        "        if src.suffix.lower() == '.svg':\n"
        "            if 'cairosvg' not in globals() or cairosvg is None:\n"
        "                raise RuntimeError('cairosvg is required to rasterize SVG')\n"
        "            png_bytes = cairosvg.svg2png(url=str(src))\n"
        "            img = Image.open(BytesIO(png_bytes))\n"
        "        else:\n"
        "            img = Image.open(str(src))\n"
        "        img.save(str(dst), format='PNG')\n"
    )


def _render_jpeg_factory() -> str:
    return (
        "    @staticmethod\n"
        "    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:\n"
        "        src = Path(task.input_path)\n"
        "        dst = Path(task.output_path)\n"
        "        dst.parent.mkdir(parents=True, exist_ok=True)\n"
        "        img = Image.open(str(src))\n"
        "        if getattr(img, 'mode', None) != 'RGB':\n"
        "            img = img.convert('RGB')\n"
        "        img.save(str(dst), format='JPEG', quality=int(getattr(task, 'options', {}).get('quality', 85)))\n"
    )


def _render_webp_factory() -> str:
    return (
        "    @staticmethod\n"
        "    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:\n"
        "        src = Path(task.input_path)\n"
        "        dst = Path(task.output_path)\n"
        "        dst.parent.mkdir(parents=True, exist_ok=True)\n"
        "        img = Image.open(str(src))\n"
        "        img.save(str(dst), format='WEBP', quality=int(getattr(task, 'options', {}).get('quality', 80)))\n"
    )


def _render_ico_factory() -> str:
    return (
        "    @staticmethod\n"
        "    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:\n"
        "        src = Path(task.input_path)\n"
        "        dst = Path(task.output_path)\n"
        "        dst.parent.mkdir(parents=True, exist_ok=True)\n"
        "        img = Image.open(str(src))\n"
        "        # Pillow will generate ICO; sizes can be provided via options\n"
        "        sizes = getattr(task, 'options', {}).get('sizes', [16,32,48,64,128,256])\n"
        "        img.save(str(dst), format='ICO', sizes=sizes)\n"
    )


def _render_generic_factory(target: str) -> str:
    fmt = target.upper()
    return (
        "    @staticmethod\n"
        "    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:\n"
        "        src = Path(task.input_path)\n"
        "        dst = Path(task.output_path)\n"
        "        dst.parent.mkdir(parents=True, exist_ok=True)\n"
        f"        img = Image.open(str(src))\n"
        f"        img.save(str(dst), format='{fmt}')\n"
    )


def _render_factory(target: str, inputs: List[str], modes: List[str]) -> str:
    """Choose and render a factory function for a given target using inputs/modes info."""
    # prioritize svg handling when present
    handles_svg = 'svg' in inputs
    handles_gif_first = ('gif' in inputs) and ('first_frame' in modes)

    if target == 'png':
        # PNG factory that can handle SVG rasterization, GIF first frame and regular raster
        parts = []
        parts.append("    @staticmethod\n")
        parts.append("    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:\n")
        parts.append("        src = Path(task.input_path)\n")
        parts.append("        dst = Path(task.output_path)\n")
        parts.append("        dst.parent.mkdir(parents=True, exist_ok=True)\n")
        # SVG branch
        if handles_svg:
            parts.append("        if src.suffix.lower() == '.svg':\n")
            parts.append("            if 'cairosvg' not in globals() or cairosvg is None:\n")
            parts.append("                raise RuntimeError('cairosvg is required to rasterize SVG')\n")
            parts.append("            png_bytes = cairosvg.svg2png(url=str(src))\n")
            parts.append("            img = Image.open(BytesIO(png_bytes))\n")
            parts.append("        else:\n")
        # GIF first-frame branch
        if handles_gif_first:
            parts.append("            if src.suffix.lower() == '.gif':\n")
            parts.append("                img = Image.open(str(src))\n")
            parts.append("                img.seek(0)\n")
            parts.append("                frame = img.convert('RGBA')\n")
            parts.append("                frame.save(str(dst), format='PNG')\n")
            parts.append("                return\n")
            parts.append("            else:\n")

        # Default open
        parts.append("            img = Image.open(str(src))\n")
        parts.append("        img.save(str(dst), format='PNG')\n")
        return "".join(parts)

    if target in ('jpg', 'jpeg'):
        return _render_jpeg_factory()

    if target == 'webp':
        return _render_webp_factory()

    if target == 'ico':
        return _render_ico_factory()

    # fallback
    return _render_generic_factory(target)


def _render_class(target: str) -> str:
    # placeholder; real content is filled by _generate_target_file using inputs/modes
    # keep a minimal class if called directly
    class_name = _class_name_for(target)
    lines: List[str] = [
        f"class {class_name}(BaseConverter):",
        f"    id = 'image-{target}'",
        f"    name = '{class_name}'",
        "    category = 'image'",
        "    input_formats = []",
        f"    output_formats = ['{target}']",
        "    options_schema = {}\n",
    ]
    lines.append(_render_generic_factory(target))
    lines.append("    def convert(self, task: ConversionTask) -> None:")
    lines.append("        return self.factory(task, None)\n")
    return "\n".join(lines)


def _generate_target_file(target: str, overwrite: bool) -> None:
    """Generate a single converter module for `target`.

    This function expects that build() aggregated per-target inputs/modes and will write
    a class with proper input_formats and a factory able to handle modes like svg/gif/heic.
    """
    # The build() will call this function with context; here we assume the caller has
    # attached per-target info to global TEMP_TARGET_INFO mapping (set in build).
    info = _TEMP_TARGET_INFO.get(target, {})
    inputs: List[str] = sorted(info.get('inputs', []))
    modes: List[str] = sorted(info.get('modes', []))

    need_bytesio = ('svg' in inputs)
    file_name = _file_name_for(target)
    path = OUTPUT_DIR / file_name

    # build import block
    content_parts: List[str] = []
    need_cairosvg = ('svg' in inputs)
    need_heif = ('heic' in inputs)
    content_parts.append(_render_imports(need_cairosvg, need_heif, need_bytesio))

    # class header
    class_name = _class_name_for(target)
    header_lines: List[str] = [
        f"class {class_name}(BaseConverter):",
        f"    id = 'image-{target}'",
        f"    name = '{class_name}'",
        "    category = 'image'",
        f"    input_formats = {inputs}",
        f"    output_formats = ['{target}']",
        "    options_schema = {}",
        "",
    ]
    content_parts.append("\n".join(header_lines))

    # factory body based on inputs/modes
    factory = _render_factory(target, inputs, modes)
    content_parts.append(factory)
    content_parts.append("    def convert(self, task: ConversionTask) -> None:")
    content_parts.append("        return self.factory(task, None)\n")

    content = "\n\n".join(content_parts)
    if path.exists() and not overwrite:
        print(f"Skipping existing {path}")
        return
    with path.open('w', encoding='utf-8') as fh:
        fh.write(content)
    print(f"Wrote {path}")


def build(overwrite: bool = True) -> None:
    """Read image.json and generate converter modules."""
    manifest = _load_manifest(MANIFEST_PATH)
    conversions = manifest.get('conversions', [])
    _ensure_output_dir()

    # aggregate per-target info
    target_info: Dict[str, Dict[str, set]] = {}
    for conv in conversions:
        froms = conv.get('from')
        tos = conv.get('to')
        mode = conv.get('mode')
        if not tos:
            continue
        if isinstance(froms, str):
            froms = [froms]
        if isinstance(tos, str):
            tos = [tos]
        for t in tos:
            info = target_info.setdefault(t, {'inputs': set(), 'modes': set(), 'engines': set()})
            for f in froms:
                info['inputs'].add(f)
            if mode:
                info['modes'].add(mode)
            engine = conv.get('engine')
            if engine:
                info['engines'].add(engine)

    # expose temporary global for _generate_target_file to read (simpler than changing signature)
    global _TEMP_TARGET_INFO
    _TEMP_TARGET_INFO = {k: {'inputs': v['inputs'], 'modes': v['modes'], 'engines': v['engines']} for k, v in target_info.items()}

    for target in sorted(_TEMP_TARGET_INFO.keys()):
        _generate_target_file(target, overwrite)


if __name__ == '__main__':
    build()
    print('Image converter generation complete.')
