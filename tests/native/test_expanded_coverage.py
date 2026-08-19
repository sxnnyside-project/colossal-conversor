from __future__ import annotations

from pathlib import Path

import pytest

from colossal.runtime.catalog import FormatCatalog
from colossal.runtime.native_runner import HAS_NATIVE
from colossal.services.conversion_service import ConversionApplicationService


@pytest.mark.skipif(not HAS_NATIVE, reason="Native C++ extension not available")
def test_markdown_to_pdf_capability_resolution() -> None:
    catalog = FormatCatalog.load_default()
    cap = catalog.find_capability("md", "pdf")
    assert cap is not None, "Markdown to PDF capability is missing from catalog"
    assert cap.supports("md", "pdf")
    assert cap.engine_id in ("soffice", "pandoc")


@pytest.mark.skipif(not HAS_NATIVE, reason="Native C++ extension not available")
def test_in_process_native_image_ppm_to_bmp(tmp_path: Path) -> None:
    # 2x2 PPM image
    ppm_content = b"P6\n2 2\n255\n\xff\x00\x00\x00\xff\x00\x00\x00\xff\xff\xff\xff"
    ppm_file = tmp_path / "input.ppm"
    ppm_file.write_bytes(ppm_content)

    bmp_out = tmp_path / "output.bmp"

    service = ConversionApplicationService()
    job = service.create_single_job(ppm_file, "bmp", bmp_out)
    result = service.execute_job(job)

    assert result.is_success, f"PPM to BMP conversion failed: {result.error}"
    assert bmp_out.exists()
    assert bmp_out.stat().st_size > 54  # BMP header is 54 bytes
    assert bmp_out.read_bytes()[:2] == b"BM"


@pytest.mark.skipif(not HAS_NATIVE, reason="Native C++ extension not available")
def test_audio_job_creation_and_capability_resolution(tmp_path: Path) -> None:
    wav_file = tmp_path / "raw.wav"
    wav_file.write_bytes(
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    mp3_out = tmp_path / "output.mp3"

    service = ConversionApplicationService()
    job = service.create_single_job(wav_file, "mp3", mp3_out)
    assert job is not None
    assert job.plan.pipeline.stage_count == 1
    assert job.plan.pipeline.stages[0].output_format_id == "mp3"


@pytest.mark.skipif(not HAS_NATIVE, reason="Native C++ extension not available")
def test_markdown_to_html_or_docx_resolution(tmp_path: Path) -> None:
    service = ConversionApplicationService()
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test Document\n\nHello from Colossal Conversor v4.", encoding="utf-8")

    html_out = tmp_path / "test.html"
    job = service.create_single_job(md_file, "html", html_out)
    assert job.plan.pipeline.stage_count == 1
    assert job.plan.pipeline.stages[0].output_format_id == "html"
