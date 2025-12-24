from pathlib import Path
import shutil
import subprocess
import tempfile

from colossal.core.base_converter import BaseConverter
from colossal.models.conversion_task import ConversionTask

def _report(cb, task, value: float):
    try:
        task.progress = float(value)
        if cb:
            cb(float(value))
    except (AttributeError, TypeError, ValueError):
        pass

def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool '{name}' not found in PATH")
    return path

def soffice_convert(src: Path, outdir: Path, to_ext: str) -> Path:
    soffice = _ensure_tool("soffice")
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        soffice,
        "--headless",
        "--convert-to",
        to_ext,
        "--outdir",
        str(outdir),
        str(src)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"LibreOffice failed converting {src.name}: {e.stderr.decode(errors='ignore')}"
        )

    out = outdir / f"{src.stem}.{to_ext}"
    if not out.exists():
        raise RuntimeError(f"LibreOffice did not produce output {out}")

    return out

# Converter base for soffice-based slide conversions
class SofficeConverter(BaseConverter):
    category = "slide"
    options_schema = {}

    input_formats: list[str] = []
    output_formats: list[str] = []
    to_ext: str

    @classmethod
    def factory(cls, task: ConversionTask, report_progress=None):
        _report(report_progress, task, 0.0)

        src = Path(task.input_path)
        target = Path(task.output_path)
        outdir = target.parent

        _report(report_progress, task, 20.0)
        out = soffice_convert(src, outdir, cls.to_ext)
        _report(report_progress, task, 80.0)

        if out.resolve() != target.resolve():
            out.replace(target)

        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# pptx -> pdf
class PPTXToPDF(SofficeConverter):
    id = "slide-pptx-to-pdf"
    name = "PPTX to PDF"
    input_formats = ["pptx"]
    output_formats = ["pdf"]
    to_ext = "pdf"

# ppt -> pdf
class PPTToPDF(PPTXToPDF):
    id = "slide-ppt-to-pdf"
    name = "PPT to PDF"
    input_formats = ["ppt"]

# odp -> pdf
class ODPToPDF(PPTXToPDF):
    id = "slide-odp-to-pdf"
    name = "ODP to PDF"
    input_formats = ["odp"]


# pdf -> pptx
class PDFToPPTX(SofficeConverter):
    id = "slide-pdf-to-pptx"
    name = "PDF to PPTX"
    input_formats = ["pdf"]
    output_formats = ["pptx"]
    to_ext = "pptx"


# pdf -> ppt
class PDFToPPT(SofficeConverter):
    id = "slide-pdf-to-ppt"
    name = "PDF to PPT"
    input_formats = ["pdf"]
    output_formats = ["ppt"]
    to_ext = "ppt"

# pdf -> odp
class PDFToODP(SofficeConverter):
    id = "slide-pdf-to-odp"
    name = "PDF to ODP"
    input_formats = ["pdf"]
    output_formats = ["odp"]
    to_ext = "odp"

# pptx, ppt, odp -> html
class SlideToHTML(SofficeConverter):
    id = "slide-to-html"
    name = "Slide to HTML"
    input_formats = ["pptx", "ppt", "odp"]
    output_formats = ["html"]
    to_ext = "html"

# html -> pptx
class HTMLToPPTX(SofficeConverter):
    id = 'html-to-pptx'
    name = 'HTML to Slide (PPTX)'
    input_formats = ['html', 'htm']
    output_formats = ['pptx']
    to_ext = 'pptx'

# html -> ppt
class HTMLToPPT(SofficeConverter):
    id = 'html-to-ppt'
    name = 'HTML to Slide (PPT)'
    input_formats = ['html', 'htm']
    output_formats = ['ppt']
    to_ext = 'ppt'

# html -> odp
class HTMLToODP(SofficeConverter):
    id = 'html-to-odp'
    name = 'HTML to Slide (ODP)'
    input_formats = ['html', 'htm']
    output_formats = ['odp']
    to_ext = 'odp'

# Converter base for image slide conversions
class ImageSlideConverter(BaseConverter):
    category = "slide"
    options_schema = {
        "resolution": {"type": "int", "default": 1920},
        "max_pages": {"type": "int", "default": None}
    }

    @staticmethod
    def factory(task: ConversionTask, report_progress=None, image_format: str = "png"):
        from shutil import copy2

        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        out = Path(task.output_path)

        if src.suffix.lower() != ".pdf":
            src = soffice_convert(src, out.parent, "pdf")

        _report(report_progress, task, 20.0)

        pdftoppm = _ensure_tool("pdftoppm")
        res = task.options.get("resolution", 1920)
        max_pages = task.options.get("max_pages", None)

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            base = tmp / src.stem

            cmd = [pdftoppm, f"-{image_format}", "-scale-to", str(res)]
            if max_pages is not None:
                cmd += ["-f", "1", "-l", str(max_pages)]
            cmd += [str(src), str(base)]

            subprocess.run(cmd, check=True)

            images = sorted(tmp.glob(f"*.{image_format}"))
            out.parent.mkdir(parents=True, exist_ok=True)

            for i, img in enumerate(images, 1):
                dest = out.parent / f"{out.stem}_page_{i}.{image_format}"
                _report(report_progress, task, 20.0 + 80.0 * (i / len(images)))
                copy2(img, dest)

        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)

# pptx, ppt, odp, pdf -> jpg
class SlideToJPG(ImageSlideConverter):
    id = "slide-to-jpg"
    name = "Slide to JPG"
    input_formats = ["pptx", "ppt", "odp", "pdf"]
    output_formats = ["jpg"]

    def convert(self, task: ConversionTask):
        return self.factory(task, None, image_format="jpeg")

class SlideToPNG(ImageSlideConverter):
    id = "slide-to-png"
    name = "Slide to PNG"
    input_formats = ["pptx", "ppt", "odp", "pdf"]
    output_formats = ["png"]

    def convert(self, task: ConversionTask):
        return self.factory(task, None, image_format="png")

class SlideToTIFF(ImageSlideConverter):
    id = "slide-to-tiff"
    name = "Slide to TIFF"
    input_formats = ["pptx", "ppt", "odp", "pdf"]
    output_formats = ["tiff"]

    def convert(self, task: ConversionTask):
        return self.factory(task, None, image_format="tiff")

class SlideToWEBP(ImageSlideConverter):
    id = "slide-to-webp"
    name = "Slide to WEBP"
    input_formats = ["pptx", "ppt", "odp", "pdf"]
    output_formats = ["webp"]

    def convert(self, task: ConversionTask):
        return self.factory(task, None, image_format="webp")

__all__ = [
    'PPTXToPDF', 'PPTToPDF', 'ODPToPDF', 'PDFToPPTX', 'PDFToPPT',
    'PDFToODP', 'SlideToHTML', 'HTMLToPPTX', 'HTMLToPPT', 'HTMLToODP',
    'SlideToJPG', 'SlideToPNG', 'SlideToTIFF', 'SlideToWEBP'
]