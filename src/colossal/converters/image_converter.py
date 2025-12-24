from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Any
from io import BytesIO

try:
    from PIL import Image, UnidentifiedImageError
except ImportError as exc:
    raise ImportError("Pillow is required for image converters; install 'pillow'") from exc

# Optional support
try:
    import cairosvg
    _HAS_CAIROSVG = True
except ImportError:
    cairosvg = None
    _HAS_CAIROSVG = False

try:
    import pillow_heif  # noqa: F401
    _HAS_PILLOW_HEIF = True
except ImportError:
    _HAS_PILLOW_HEIF = False

from colossal.core.base_converter import BaseConverter
from colossal.models.conversion_task import ConversionTask


def _report(report_progress: Optional[Callable[[float], None]], task: ConversionTask, value: float) -> None:
    try:
        task.progress = float(value)
    except (AttributeError, ValueError, TypeError):
        pass
    if report_progress:
        try:
            report_progress(float(value))
        except (TypeError, ValueError):
            pass


def _open_image(src: Path) -> Any:
    src = Path(src)
    ext = (src.suffix or "").lower().lstrip('.')
    if ext == 'svg':
        if not _HAS_CAIROSVG:
            raise RuntimeError('cairosvg is required to read SVG files')
        png_bytes = cairosvg.svg2png(url=str(src))
        return Image.open(BytesIO(png_bytes))
    # Pillow (and pillow_heif if installed) will handle other formats
    return Image.open(str(src))


def _save_image(img: Any, dst: Path, fmt: Optional[str] = None, options: Optional[dict] = None) -> None:
    options = options or {}
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    ext = (dst.suffix or "").lower().lstrip('.')
    fmt_map = {
        'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'webp': 'WEBP', 'ico': 'ICO', 'bmp': 'BMP', 'tiff': 'TIFF',
        'tif': 'TIFF', 'jfif': 'JPEG'
    }
    target = fmt_map.get(ext, fmt or 'PNG')
    save_kwargs = {}
    if target in ('JPEG', 'WEBP'):
        save_kwargs['quality'] = int(options.get('quality', 85))
    if target == 'PNG':
        save_kwargs['optimize'] = True
    # Handle alpha for JPEG
    if target == 'JPEG' and getattr(img, 'mode', None) in ('RGBA', 'LA'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[-1])
        img = bg
    img.save(str(dst), format=target, **save_kwargs)


# jpg, jpeg, png, webp, ico, jfif, svg, bmp, tiff, gif, heic -> png
class PNGConverter(BaseConverter):
    id = 'image-png'
    name = 'PNG Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg', 'webp', 'ico', 'jfif', 'svg', 'bmp', 'tiff', 'gif', 'heic']
    output_formats = ['png']
    options_schema = {'quality': {'type': 'integer', 'default': 85}}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 20.0)
        _report(report_progress, task, 60.0)
        _save_image(img, Path(task.output_path), options=task.options)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        # compatibility with BaseConverter abstract method
        return self.factory(task, None)


class JPEGConverter(BaseConverter):
    id = 'image-jpeg'
    name = 'JPEG Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg', 'webp', 'ico', 'jfif', 'svg', 'bmp', 'tiff', 'gif', 'heic']
    output_formats = ['jpg', 'jpeg']
    options_schema = {'quality': {'type': 'integer', 'default': 90}}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        if src.suffix.lower() == '.svg':
            if not _HAS_CAIROSVG:
                raise RuntimeError('cairosvg required for SVG input')
            png_bytes = cairosvg.svg2png(url=str(src))
            img = Image.open(BytesIO(png_bytes))
        else:
            img = _open_image(src)
        _report(report_progress, task, 30.0)
        if getattr(img, 'mode', None) != 'RGB':
            img = img.convert('RGB')
        _report(report_progress, task, 60.0)
        _save_image(img, Path(task.output_path), options=task.options)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class WEBPConverter(BaseConverter):
    id = 'image-webp'
    name = 'WEBP Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg', 'webp', 'ico', 'jfif', 'svg', 'bmp', 'tiff', 'gif', 'heic']
    output_formats = ['webp']
    options_schema = {'quality': {'type': 'integer', 'default': 80}}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 50.0)
        _save_image(img, Path(task.output_path), options=task.options)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class ICOConverter(BaseConverter):
    id = 'image-ico'
    name = 'ICO Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg']
    output_formats = ['ico']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 60.0)
        img.save(str(Path(task.output_path)), format='ICO')
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class JFIFConverter(BaseConverter):
    id = 'image-jfif'
    name = 'JFIF Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg']
    output_formats = ['jfif']
    options_schema = {'quality': {'type': 'integer', 'default': 90}}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        # JFIF is JPEG with specific markers; save as JPEG
        JPEGConverter.factory(task, report_progress)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SVGConverter(BaseConverter):
    id = 'image-svg'
    name = 'SVG Converter'
    category = 'image'
    input_formats = ['svg']
    output_formats = ['png', 'jpg', 'jpeg', 'webp']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        if not _HAS_CAIROSVG:
            raise RuntimeError('cairosvg is required for SVG conversion')
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        png_bytes = cairosvg.svg2png(url=str(src))
        img = Image.open(BytesIO(png_bytes))
        _report(report_progress, task, 50.0)
        _save_image(img, Path(task.output_path), options=task.options)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class BMPConverter(BaseConverter):
    id = 'image-bmp'
    name = 'BMP Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg', 'bmp']
    output_formats = ['bmp']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 50.0)
        _save_image(img, Path(task.output_path))
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class TIFFConverter(BaseConverter):
    id = 'image-tiff'
    name = 'TIFF Converter'
    category = 'image'
    input_formats = ['png', 'jpg', 'jpeg', 'tiff', 'tif']
    output_formats = ['tiff']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 50.0)
        _save_image(img, Path(task.output_path))
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class GIFConverter(BaseConverter):
    id = 'image-gif'
    name = 'GIF Converter'
    category = 'image'
    input_formats = ['gif', 'png', 'jpg', 'jpeg']
    output_formats = ['gif', 'png', 'jpg', 'jpeg']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 50.0)
        if getattr(img, 'is_animated', False):
            img.seek(0)
            frame = img.convert('RGBA')
            _save_image(frame, Path(task.output_path), options=task.options)
        else:
            _save_image(img, Path(task.output_path), options=task.options)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class HEICConverter(BaseConverter):
    id = 'image-heic'
    name = 'HEIC Converter'
    category = 'image'
    input_formats = ['heic']
    output_formats = ['jpg', 'png', 'webp']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        if not _HAS_PILLOW_HEIF:
            raise RuntimeError('pillow_heif is required to read HEIC files')
        img = _open_image(Path(task.input_path))
        _report(report_progress, task, 50.0)
        _save_image(img, Path(task.output_path), options=task.options)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


__all__ = [
    'PNGConverter', 'JPEGConverter', 'WEBPConverter', 'ICOConverter', 'JFIFConverter', 'SVGConverter',
    'BMPConverter', 'TIFFConverter', 'GIFConverter', 'HEICConverter'
]
