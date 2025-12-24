from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
import shutil
import subprocess

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


def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool '{name}' not found in PATH. Install LibreOffice (soffice)")
    return path


def _soffice_convert(src: Path, outdir: Path, to_ext: str) -> Path:
    """Use LibreOffice headless to convert src -> outdir/<basename>.<to_ext>
    Returns the path of converted file.
    """
    soffice = _ensure_tool('soffice')
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [soffice, '--headless', '--convert-to', to_ext, '--outdir', str(outdir), str(src)]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_name = src.with_suffix('.' + to_ext).name
    out_path = outdir.joinpath(out_name)
    if not out_path.exists():
        raise RuntimeError(f"soffice did not produce expected output {out_path}")
    return out_path


# Converters
class SheetToPDFConverter(BaseConverter):
    id = 'sheet-to-pdf'
    name = 'Sheet to PDF'
    category = 'sheet'
    input_formats = ['xls', 'xlsx', 'csv', 'ods', 'tsv']
    output_formats = ['pdf']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        outdir = Path(task.output_path).resolve().parent
        pdf_path = _soffice_convert(src, outdir, 'pdf')
        target = Path(task.output_path)
        if pdf_path.resolve() != target.resolve():
            pdf_path.replace(target)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SheetToXLSXConverter(BaseConverter):
    id = 'sheet-to-xlsx'
    name = 'Sheet to XLSX'
    category = 'sheet'
    input_formats = ['csv', 'xls', 'ods', 'tsv']
    output_formats = ['xlsx']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        outdir = Path(task.output_path).resolve().parent
        out_path = _soffice_convert(src, outdir, 'xlsx')
        target = Path(task.output_path)
        if out_path.resolve() != target.resolve():
            out_path.replace(target)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SheetToXLSConverter(BaseConverter):
    id = 'sheet-to-xls'
    name = 'Sheet to XLS'
    category = 'sheet'
    input_formats = ['csv', 'xlsx', 'ods', 'tsv']
    output_formats = ['xls']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        outdir = Path(task.output_path).resolve().parent
        out_path = _soffice_convert(src, outdir, 'xls')
        target = Path(task.output_path)
        if out_path.resolve() != target.resolve():
            out_path.replace(target)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SheetToODSConverter(BaseConverter):
    id = 'sheet-to-ods'
    name = 'Sheet to ODS'
    category = 'sheet'
    input_formats = ['xls', 'xlsx', 'csv', 'tsv']
    output_formats = ['ods']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        outdir = Path(task.output_path).resolve().parent
        out_path = _soffice_convert(src, outdir, 'ods')
        target = Path(task.output_path)
        if out_path.resolve() != target.resolve():
            out_path.replace(target)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SheetToCSVConverter(BaseConverter):
    id = 'sheet-to-csv'
    name = 'Sheet to CSV'
    category = 'sheet'
    input_formats = ['xls', 'xlsx', 'ods', 'tsv']
    output_formats = ['csv']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        outdir = Path(task.output_path).resolve().parent
        # LibreOffice will produce CSV; for TSV there are filter options but we keep CSV here
        out_path = _soffice_convert(src, outdir, 'csv')
        target = Path(task.output_path)
        if out_path.resolve() != target.resolve():
            out_path.replace(target)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SheetToTSVConverter(BaseConverter):
    id = 'sheet-to-tsv'
    name = 'Sheet to TSV'
    category = 'sheet'
    input_formats = ['xls', 'xlsx', 'ods', 'csv']
    output_formats = ['tsv']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        # Many environments don't support a direct 'tsv' target via soffice; fall back to csv and convert delimiter
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        out = Path(task.output_path)
        outdir = out.resolve().parent
        try:
            out_path = _soffice_convert(src, outdir, 'tsv')
            target = out
            if out_path.resolve() != target.resolve():
                out_path.replace(target)
        except RuntimeError:
            # fallback: generate CSV then replace commas with tabs
            csv_path = _soffice_convert(src, outdir, 'csv')
            # read and write with tab delimiter
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f_in, open(out, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    f_out.write('\t'.join(line.rstrip('\n').split(',')) + '\n')
            try:
                csv_path.unlink()
            except OSError:
                pass
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


class SheetToHTMLConverter(BaseConverter):
    id = 'sheet-to-html'
    name = 'Sheet to HTML'
    category = 'sheet'
    input_formats = ['xls', 'xlsx', 'ods']
    output_formats = ['html']
    options_schema = {}

    @staticmethod
    def factory(task: ConversionTask, report_progress: Optional[Callable[[float], None]] = None) -> None:
        _report(report_progress, task, 0.0)
        src = Path(task.input_path)
        outdir = Path(task.output_path).resolve().parent
        out_path = _soffice_convert(src, outdir, 'html')
        target = Path(task.output_path)
        if out_path.resolve() != target.resolve():
            out_path.replace(target)
        _report(report_progress, task, 100.0)

    def convert(self, task: ConversionTask) -> None:
        return self.factory(task, None)


__all__ = [
    'SheetToPDFConverter', 'SheetToXLSXConverter', 'SheetToXLSConverter', 'SheetToODSConverter',
    'SheetToCSVConverter', 'SheetToTSVConverter', 'SheetToHTMLConverter'
]

