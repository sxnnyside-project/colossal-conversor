from __future__ import annotations

from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner


def _create_minimal_bmp(width: int, height: int) -> bytes:
    row_padded = (width * 3 + 3) & (~3)
    image_size = row_padded * height
    file_size = 54 + image_size

    header = bytearray(54)
    header[0:2] = b"BM"
    header[2:6] = file_size.to_bytes(4, "little")
    header[10:14] = (54).to_bytes(4, "little")
    header[14:18] = (40).to_bytes(4, "little")
    header[18:22] = width.to_bytes(4, "little")
    header[22:26] = height.to_bytes(4, "little")
    header[26:28] = (1).to_bytes(2, "little")
    header[28:30] = (24).to_bytes(2, "little")
    header[34:38] = image_size.to_bytes(4, "little")

    pixels = bytearray(image_size)
    for i in range(0, image_size, 3):
        pixels[i] = 255  # Blue
        if i + 1 < image_size:
            pixels[i + 1] = 0  # Green
        if i + 2 < image_size:
            pixels[i + 2] = 0  # Red

    return bytes(header + pixels)


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_image_engine_in_process_bmp_to_ppm(tmp_path: Path) -> None:
    in_bmp = tmp_path / "input.bmp"
    in_bmp.write_bytes(_create_minimal_bmp(10, 10))
    out_ppm = tmp_path / "output.ppm"

    req = ConversionRequest.from_single_file(in_bmp, "bmp", "ppm", out_ppm)
    cap = Capability(
        id="cap_native_image_bmp_ppm",
        name="Native Image BMP to PPM",
        input_formats=frozenset(["bmp"]),
        output_formats=frozenset(["ppm"]),
        engine_id="native_image",
        requirements=(),  # Zero external tool requirements!
    )
    stage = PipelineStage(0, "transcode_image", cap, "bmp", "ppm")
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
    res = runner.execute_job(job)

    assert res.is_success
    assert job.status == JobStatus.COMPLETED
    assert out_ppm.exists()
    content = out_ppm.read_bytes()
    assert content.startswith(b"P6\n10 10\n255\n")
    runner.shutdown()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_image_engine_resize_option(tmp_path: Path) -> None:
    in_bmp = tmp_path / "orig.bmp"
    in_bmp.write_bytes(_create_minimal_bmp(20, 20))
    out_bmp = tmp_path / "resized.bmp"

    req = ConversionRequest.from_single_file(
        in_bmp, "bmp", "bmp", out_bmp, options={"resize": "40x40"}
    )
    cap = Capability(
        id="cap_native_image_resize",
        name="Native Image Resize",
        input_formats=frozenset(["bmp"]),
        output_formats=frozenset(["bmp"]),
        engine_id="native_image",
        requirements=(),
    )
    stage = PipelineStage(0, "resize", cap, "bmp", "bmp", options={"resize": "40x40"})
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
    res = runner.execute_job(job)

    assert res.is_success
    assert job.status == JobStatus.COMPLETED
    assert out_bmp.exists()
    header = out_bmp.read_bytes()[:54]
    w = int.from_bytes(header[18:22], "little")
    h = int.from_bytes(header[22:26], "little")
    assert w == 40
    assert h == 40
    runner.shutdown()
