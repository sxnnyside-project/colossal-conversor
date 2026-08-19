from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.error import ConversionErrorCode
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner

if HAS_NATIVE:
    from colossal import colossal_native


def _create_mock_script(path: Path, code: str) -> Path:
    path.write_text(f"#!{sys.executable}\n{code}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_zero_byte_single_output_is_rejected_not_reported_complete(tmp_path: Path) -> None:
    """A subprocess that exits 0 but writes an empty file is not a successful
    conversion — a truthful engine must reject it rather than reporting a
    zero-byte artifact as COMPLETED.
    """
    # Exits successfully but creates the destination as an empty file.
    script = "import sys, pathlib\npathlib.Path(sys.argv[-1]).touch()\nsys.exit(0)\n"
    mock_pandoc = _create_mock_script(tmp_path / "mock_pandoc_empty", script)
    colossal_native.ToolDiscovery.instance().register_custom_path("pandoc", mock_pandoc)

    try:
        req = ConversionRequest.from_single_file(
            input_path=tmp_path / "doc.md",
            input_format_id="md",
            output_format_id="html",
            destination_path=tmp_path / "doc.html",
        )
        cap = Capability(
            id="cap_md_html_empty",
            name="Markdown to HTML",
            input_formats=frozenset(["md"]),
            output_formats=frozenset(["html"]),
            engine_id="pandoc",
        )
        stage = PipelineStage(0, "convert", cap, "md", "html")
        plan = ConversionPlan(req, ConversionPipeline((stage,)))
        job = ConversionJob(plan=plan)

        runner = NativeJobRunner(thread_count=2)
        result = runner.execute_job(job)

        assert result.status == JobStatus.FAILED
        assert job.status == JobStatus.FAILED
        assert job.produced_artifacts == []
        assert result.error is not None
        assert result.error.code == ConversionErrorCode.OUTPUT_FAILURE

        runner.shutdown()
    finally:
        colossal_native.ToolDiscovery.instance().clear_cache()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_zero_byte_multi_output_page_is_rejected(tmp_path: Path) -> None:
    """A multi-output (1->N) capability where one of the produced pages is
    empty must fail the whole stage rather than silently reporting a
    truncated/invalid page as part of a successful multi-output result.
    """
    script = (
        "import sys, pathlib\n"
        "prefix = sys.argv[-1]\n"
        "pathlib.Path(f'{prefix}-1.png').write_bytes(b'page1')\n"
        "pathlib.Path(f'{prefix}-2.png').touch()\n"  # empty second page
        "sys.exit(0)\n"
    )
    mock_pdftoppm = _create_mock_script(tmp_path / "mock_pdftoppm_empty", script)
    colossal_native.ToolDiscovery.instance().register_custom_path("pdftoppm", mock_pdftoppm)

    try:
        in_pdf = tmp_path / "doc.pdf"
        in_pdf.write_bytes(b"%PDF-1.4 mock")
        out_dir = tmp_path / "pages"
        out_dir.mkdir()

        req = ConversionRequest.from_single_file(in_pdf, "pdf", "png", out_dir)
        cap = Capability(
            id="cap_pdftoppm_multi_empty",
            name="PDF to PNG pages",
            input_formats=frozenset(["pdf"]),
            output_formats=frozenset(["png"]),
            engine_id="pdftoppm",
            requirements=("pdftoppm",),
            cardinality=ConversionCardinality.ONE_TO_MANY,
        )
        stage = PipelineStage(0, "rasterize_pages", cap, "pdf", "png")
        plan = ConversionPlan(req, ConversionPipeline((stage,)))
        job = ConversionJob(plan=plan)

        runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
        result = runner.execute_job(job)

        assert result.status == JobStatus.FAILED
        assert job.status == JobStatus.FAILED
        assert job.produced_artifacts == []
        assert result.error is not None
        assert result.error.code == ConversionErrorCode.OUTPUT_FAILURE

        runner.shutdown()
    finally:
        colossal_native.ToolDiscovery.instance().clear_cache()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_failed_stage_in_pipeline_cannot_produce_completed(tmp_path: Path) -> None:
    """If the second stage of a multi-stage pipeline fails, the job must end
    FAILED, must not report the never-reached final artifact, and the first
    stage's intermediate artifact must still be tracked (for diagnosis), not
    silently discarded.
    """
    ok_script = (
        "import sys, pathlib\n"
        "outdir = pathlib.Path(sys.argv[sys.argv.index('--outdir') + 1])\n"
        "infile = pathlib.Path(sys.argv[-1])\n"
        "(outdir / f'{infile.stem}.pdf').write_bytes(b'%PDF-1.4 mock pdf')\n"
        "sys.exit(0)\n"
    )
    mock_soffice = _create_mock_script(tmp_path / "mock_soffice_ok", ok_script)
    colossal_native.ToolDiscovery.instance().register_custom_path("soffice", mock_soffice)

    failing_script = "import sys\nsys.stderr.write('boom: cannot rasterize\\n')\nsys.exit(1)\n"
    mock_pdftoppm = _create_mock_script(tmp_path / "mock_pdftoppm_fail", failing_script)
    colossal_native.ToolDiscovery.instance().register_custom_path("pdftoppm", mock_pdftoppm)

    try:
        in_pptx = tmp_path / "slides.pptx"
        in_pptx.write_bytes(b"PK mock pptx")
        out_png = tmp_path / "slides.png"

        req = ConversionRequest.from_single_file(in_pptx, "pptx", "png", out_png)
        cap_pptx_pdf = Capability(
            id="cap_soffice_pptx_pdf_fail",
            name="PPTX to PDF",
            input_formats=frozenset(["pptx"]),
            output_formats=frozenset(["pdf"]),
            engine_id="soffice",
            requirements=("soffice",),
        )
        cap_pdf_png = Capability(
            id="cap_pdftoppm_pdf_png_fail",
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
        result = runner.execute_job(job)

        assert result.status == JobStatus.FAILED
        assert job.status == JobStatus.FAILED
        assert not out_png.exists()
        assert job.produced_artifacts == []
        assert result.error is not None
        assert result.error.code == ConversionErrorCode.EXECUTION_FAILED
        assert result.error.stage_index == 1
        # Stage 0's intermediate output was genuinely produced before stage 1
        # failed; it must be tracked, not silently dropped.
        assert len(job.intermediate_artifacts) == 1

        # The multi-stage workspace itself must be cleaned up even on
        # failure, not left behind because cleanup only ran on the
        # success path.
        workspace_dir = tmp_path / f"colossal_native_{job.id}"
        assert not workspace_dir.exists(), "intermediate workspace was not cleaned up after failure"

        runner.shutdown()
    finally:
        colossal_native.ToolDiscovery.instance().clear_cache()
