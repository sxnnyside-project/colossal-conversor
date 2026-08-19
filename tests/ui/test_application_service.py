from __future__ import annotations

from pathlib import Path

from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.request import DestinationIntent
from colossal.services.conversion_service import ConversionApplicationService


def test_service_format_detection(tmp_path: Path) -> None:
    service = ConversionApplicationService()
    png_file = tmp_path / "test.png"
    png_file.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00"
    )

    fmt = service.detect_format(png_file)
    assert fmt.id == "png"
    assert "PNG" in fmt.label


def test_service_available_outputs() -> None:
    service = ConversionApplicationService()
    outputs = service.get_available_outputs(["png"])
    assert (
        "jpeg" in outputs
        or "jpg" in outputs
        or "bmp" in outputs
        or "pdf" in outputs
        or "ppm" in outputs
    )


def test_service_capability_details() -> None:
    service = ConversionApplicationService()
    details = service.get_capability_details("wav", "mp3")
    assert details["engine_id"] == "ffmpeg"
    assert "fidelity" in details


def test_service_create_single_job(tmp_path: Path) -> None:
    service = ConversionApplicationService()
    in_file = tmp_path / "sound.wav"
    in_file.write_bytes(b"RIFFmockwav")
    out_file = tmp_path / "sound.mp3"

    job = service.create_single_job(
        input_path=in_file,
        output_format_id="mp3",
        destination_path=out_file,
    )
    assert job.plan.request.primary_input.format_id == "wav"
    assert job.plan.request.output_format_id == "mp3"
    assert job.plan.request.destination_intent == DestinationIntent.FILE


def test_service_create_batch(tmp_path: Path) -> None:
    service = ConversionApplicationService()
    f1 = tmp_path / "a.wav"
    f2 = tmp_path / "b.wav"
    f1.write_bytes(b"RIFFmock1")
    f2.write_bytes(b"RIFFmock2")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    batch = service.create_batch(
        input_paths=[f1, f2],
        output_format_id="mp3",
        destination_directory=out_dir,
    )
    assert batch.total_count == 2
    assert batch.jobs[0].plan.request.destination_path == out_dir / "a.mp3"
    assert batch.jobs[1].plan.request.destination_path == out_dir / "b.mp3"


def test_service_format_error_message() -> None:
    service = ConversionApplicationService()

    err_dep = ConversionError(
        code=ConversionErrorCode.MISSING_DEPENDENCY,
        message="soffice missing",
    )
    msg_dep = service.format_error_message(err_dep)
    assert "requires an external tool" in msg_dep or "soffice missing" in msg_dep

    err_pipe = ConversionError(
        code=ConversionErrorCode.PIPELINE_FAILURE,
        message="Stage broken",
        stage_index=1,
    )
    msg_pipe = service.format_error_message(err_pipe)
    assert "Stage 1" in msg_pipe or "Stage broken" in msg_pipe
