from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.cardinality import ConversionCardinality
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
def test_native_one_to_many_cardinality(tmp_path: Path) -> None:
    # pdftoppm producing 3 pages
    pdftoppm_script = (
        "import sys, pathlib\n"
        "prefix = sys.argv[-1]\n"
        "pathlib.Path(f'{prefix}-1.png').write_bytes(b'page1')\n"
        "pathlib.Path(f'{prefix}-2.png').write_bytes(b'page2')\n"
        "pathlib.Path(f'{prefix}-3.png').write_bytes(b'page3')\n"
        "sys.exit(0)\n"
    )
    mock_pdftoppm = _create_mock_script(tmp_path / "mock_pdftoppm_multi", pdftoppm_script)
    colossal_native.ToolDiscovery.instance().register_custom_path("pdftoppm", mock_pdftoppm)

    in_pdf = tmp_path / "doc.pdf"
    in_pdf.write_bytes(b"%PDF-1.4 mock")
    out_dir = tmp_path / "pages"
    out_dir.mkdir()

    req = ConversionRequest.from_single_file(in_pdf, "pdf", "png", out_dir)
    cap = Capability(
        id="cap_pdftoppm_multi",
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
    res = runner.execute_job(job)

    assert res.is_success
    assert job.status == JobStatus.COMPLETED
    assert len(res.output_artifacts) == 3
    assert len(job.produced_artifacts) == 3
    for art in res.output_artifacts:
        assert art.path.exists()
        assert art.format_id == "png"
    runner.shutdown()
