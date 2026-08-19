from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner

if HAS_NATIVE:
    from colossal import colossal_native


def _create_mock_script(path: Path, code: str) -> Path:
    script_content = f"#!{sys.executable}\n{code}\n"
    path.write_text(script_content)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_multi_stage_pipeline(tmp_path: Path) -> None:
    # Stage 0: soffice converts PPTX to PDF
    soffice_script = (
        "import sys, pathlib\n"
        "outdir = pathlib.Path(sys.argv[sys.argv.index('--outdir') + 1])\n"
        "infile = pathlib.Path(sys.argv[-1])\n"
        "(outdir / f'{infile.stem}.pdf').write_bytes(b'%PDF-1.4 mock pdf')\n"
        "sys.exit(0)\n"
    )
    mock_soffice = _create_mock_script(tmp_path / "mock_soffice", soffice_script)
    colossal_native.ToolDiscovery.instance().register_custom_path("soffice", mock_soffice)

    # Stage 1: pdftoppm converts PDF to PNG
    pdftoppm_script = (
        "import sys, pathlib\n"
        "prefix = sys.argv[-1]\n"
        "pathlib.Path(f'{prefix}-1.png').write_bytes(b'\\x89PNG\\r\\n mock png')\n"
        "sys.exit(0)\n"
    )
    mock_pdftoppm = _create_mock_script(tmp_path / "mock_pdftoppm", pdftoppm_script)
    colossal_native.ToolDiscovery.instance().register_custom_path("pdftoppm", mock_pdftoppm)

    in_pptx = tmp_path / "slides.pptx"
    in_pptx.write_bytes(b"PK mock pptx")
    out_png = tmp_path / "slides.png"

    req = ConversionRequest.from_single_file(in_pptx, "pptx", "png", out_png)

    cap_pptx_pdf = Capability(
        id="cap_soffice_pptx_pdf",
        name="PPTX to PDF",
        input_formats=frozenset(["pptx"]),
        output_formats=frozenset(["pdf"]),
        engine_id="soffice",
        requirements=("soffice",),
    )
    cap_pdf_png = Capability(
        id="cap_pdftoppm_pdf_png",
        name="PDF to PNG",
        input_formats=frozenset(["pdf"]),
        output_formats=frozenset(["png"]),
        engine_id="pdftoppm",
        requirements=("pdftoppm",),
    )

    stage0 = PipelineStage(0, "convert_to_pdf", cap_pptx_pdf, "pptx", "pdf")
    stage1 = PipelineStage(1, "rasterize_to_png", cap_pdf_png, "pdf", "png")

    pipeline = ConversionPipeline((stage0, stage1))
    plan = ConversionPlan(req, pipeline)
    job = ConversionJob(plan=plan)

    runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
    res = runner.execute_job(job)

    assert res.is_success
    assert job.status == JobStatus.COMPLETED
    assert len(res.output_artifacts) == 1
    assert out_png.exists()
    assert len(job.intermediate_artifacts) == 1
    runner.shutdown()
