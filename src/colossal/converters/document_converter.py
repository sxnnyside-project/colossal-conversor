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
        raise RuntimeError(f"Required tool '{name}' not found in PATH. Install {name}.")
    return path


def _soffice_convert(src: Path, outdir: Path, to_ext: str) -> Path:
    """Use LibreOffice (soffice) to convert src -> outdir/<basename>.<to_ext>
    Returns the path of the converted file.
    """
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
        raise RuntimeError(f"LibreOffice failed converting {src.name}: {e.stderr.decode(errors='ignore')}")

    out = outdir / f"{src.stem}.{to_ext}"
    if not out.exists():
        raise RuntimeError(f"LibreOffice did not produce output {out}")

    return out


def _pandoc_convert(src: Path, dst: Path, extra_args: list | None = None) -> None:
    pandoc = _ensure_tool("pandoc")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [pandoc, str(src), "-o", str(dst)]
    if extra_args:
        cmd[1:1] = extra_args  # insert after pandoc but before input
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="ignore") if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
        raise RuntimeError(f"pandoc failed converting {src.name}: {stderr}")


def _pdftotext_extract(src: Path, dst: Path) -> None:
    pdftotext = _ensure_tool("pdftotext")
    dst.parent.mkdir(parents=True, exist_ok=True)
    # pdftotext src out.txt
    cmd = [pdftotext, str(src), str(dst)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftotext failed extracting {src.name}: {e.stderr.decode(errors='ignore')}")


# Base converter using soffice
class SofficeConverter(BaseConverter):
    category = "document"
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
        out = _soffice_convert(src, outdir, cls.to_ext)
        _report(report_progress, task, 80.0)

        if out.resolve() != target.resolve():
            out.replace(target)

        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# Pandoc-based converter
class PandocConverter(BaseConverter):
    category = "document"
    options_schema = {}

    input_formats: list[str] = []
    output_formats: list[str] = []

    @classmethod
    def factory(cls, task: ConversionTask, report_progress=None):
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        dst = Path(task.output_path)

        _report(report_progress, task, 30.0)
        _pandoc_convert(src, dst)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# PDF extraction converter (to txt or md via pdftotext)
class PDFTextExtractor(BaseConverter):
    category = "document"
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        out = Path(task.output_path)

        # extract text with pdftotext
        _report(report_progress, task, 30.0)
        _pdftotext_extract(src, out)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# Concrete converters based on document.json
# 1) office -> pdf (doc/docx/odt/rtf/txt -> pdf)
class OfficeToPDF(SofficeConverter):
    id = 'document-office-to-pdf'
    name = 'Office to PDF'
    input_formats = ['doc', 'docx', 'odt', 'rtf', 'txt']
    output_formats = ['pdf']
    to_ext = 'pdf'


# 2) md -> pdf via pandoc
class MarkdownToPDF(PandocConverter):
    id = 'markdown-to-pdf'
    name = 'Markdown to PDF'
    input_formats = ['md']
    output_formats = ['pdf']

    @classmethod
    def factory(cls, task: ConversionTask, report_progress=None):
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        dst = Path(task.output_path)
        _report(report_progress, task, 30.0)
        # allow pandoc to choose default PDF engine; callers can provide extra args via options if needed
        extra = task.options.get('pandoc_args')
        _pandoc_convert(src, dst, extra_args=extra if isinstance(extra, list) else None)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# 3) pdf -> docx/txt/md
class PDFToDOCX(SofficeConverter):
    id = 'pdf-to-docx'
    name = 'PDF to DOCX'
    input_formats = ['pdf']
    output_formats = ['docx']
    to_ext = 'docx'


class PDFToTXT(PDFTextExtractor):
    id = 'pdf-to-txt'
    name = 'PDF to TXT'
    input_formats = ['pdf']
    output_formats = ['txt']


class PDFToMD(PDFTextExtractor):
    id = 'pdf-to-md'
    name = 'PDF to MD'
    input_formats = ['pdf']
    output_formats = ['md']

    @staticmethod
    def factory(task: ConversionTask, report_progress=None):
        # Use pdftotext to extract then save as .md (best-effort)
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        out = Path(task.output_path)

        _report(report_progress, task, 30.0)
        # extract to temporary txt then move to .md
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / (src.stem + '.txt')
            _pdftotext_extract(src, tmp)
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp.replace(out)

        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask):
        return self.factory(task, None)


# 4) office transcodes between doc/docx/odt/rtf
class ToDOCX(SofficeConverter):
    id = 'document-to-docx'
    name = 'Document to DOCX'
    input_formats = ['doc', 'docx', 'odt', 'rtf']
    output_formats = ['docx']
    to_ext = 'docx'


class ToODT(SofficeConverter):
    id = 'document-to-odt'
    name = 'Document to ODT'
    input_formats = ['doc', 'docx', 'odt', 'rtf']
    output_formats = ['odt']
    to_ext = 'odt'


class ToRTF(SofficeConverter):
    id = 'document-to-rtf'
    name = 'Document to RTF'
    input_formats = ['doc', 'docx', 'odt', 'rtf']
    output_formats = ['rtf']
    to_ext = 'rtf'


# 5) md/txt -> docx/odt/rtf via pandoc
class MDToDOCX(PandocConverter):
    id = 'md-to-docx'
    name = 'Markdown/TXT to DOCX'
    input_formats = ['md', 'txt']
    output_formats = ['docx']


class MDToODT(PandocConverter):
    id = 'md-to-odt'
    name = 'Markdown/TXT to ODT'
    input_formats = ['md', 'txt']
    output_formats = ['odt']


class MDToRTF(PandocConverter):
    id = 'md-to-rtf'
    name = 'Markdown/TXT to RTF'
    input_formats = ['md', 'txt']
    output_formats = ['rtf']


# 6) doc/docx/odt/rtf -> md/txt via pandoc
class DocToMD(PandocConverter):
    id = 'document-to-md'
    name = 'Document to MD'
    input_formats = ['doc', 'docx', 'odt', 'rtf']
    output_formats = ['md']


class DocToTXT(PandocConverter):
    id = 'document-to-txt'
    name = 'Document to TXT'
    input_formats = ['doc', 'docx', 'odt', 'rtf']
    output_formats = ['txt']


__all__ = [
    'OfficeToPDF', 'MarkdownToPDF', 'PDFToDOCX', 'PDFToTXT', 'PDFToMD',
    'ToDOCX', 'ToODT', 'ToRTF',
    'MDToDOCX', 'MDToODT', 'MDToRTF',
    'DocToMD', 'DocToTXT'
]

