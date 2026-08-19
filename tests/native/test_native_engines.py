from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.error import ConversionErrorCode
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
def test_native_tool_discovery(tmp_path: Path) -> None:
    discovery = colossal_native.ToolDiscovery.instance()
    discovery.clear_cache()

    # Create dummy tool
    dummy_tool = _create_mock_script(tmp_path / "dummy_ffmpeg", "import sys; sys.exit(0)")
    discovery.register_custom_path("ffmpeg", dummy_tool)

    found = discovery.find_tool("ffmpeg")
    assert found == dummy_tool

    req_path = discovery.require_tool("ffmpeg")
    assert req_path == dummy_tool


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_ffmpeg_execution(tmp_path: Path) -> None:
    # Register mock ffmpeg creating output
    script = (
        "import sys, pathlib\n"
        "out_file = sys.argv[-1]\n"
        "pathlib.Path(out_file).write_bytes(b'ID3mockmp3data')\n"
        "sys.exit(0)\n"
    )
    mock_bin = _create_mock_script(tmp_path / "mock_ffmpeg", script)
    colossal_native.ToolDiscovery.instance().register_custom_path("ffmpeg", mock_bin)

    in_file = tmp_path / "track.wav"
    in_file.write_bytes(b"RIFFmockwav")
    out_file = tmp_path / "track.mp3"

    req = ConversionRequest.from_single_file(in_file, "wav", "mp3", out_file)
    cap = Capability(
        id="cap_wav_mp3",
        name="WAV to MP3",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["mp3"]),
        engine_id="ffmpeg",
        requirements=("ffmpeg",),
    )
    stage = PipelineStage(0, "transcode", cap, "wav", "mp3")
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
    res = runner.execute_job(job)

    assert res.is_success
    assert job.status == JobStatus.COMPLETED
    assert len(res.output_artifacts) == 1
    assert res.output_artifacts[0].path == out_file
    assert out_file.exists()
    runner.shutdown()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_engine_failure_propagation(tmp_path: Path) -> None:
    script = "import sys\nsys.stderr.write('ffmpeg: invalid codec parameter\\n')\nsys.exit(1)\n"
    mock_bin = _create_mock_script(tmp_path / "failing_ffmpeg", script)
    colossal_native.ToolDiscovery.instance().register_custom_path("ffmpeg", mock_bin)

    in_file = tmp_path / "bad.wav"
    in_file.write_bytes(b"bad")
    out_file = tmp_path / "bad.mp3"

    req = ConversionRequest.from_single_file(in_file, "wav", "mp3", out_file)
    cap = Capability(
        id="cap_wav_mp3",
        name="WAV to MP3",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["mp3"]),
        engine_id="ffmpeg",
        requirements=("ffmpeg",),
    )
    stage = PipelineStage(0, "transcode", cap, "wav", "mp3")
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
    res = runner.execute_job(job)

    assert res.is_failed
    assert job.status == JobStatus.FAILED
    assert res.error is not None
    assert res.error.code == ConversionErrorCode.EXECUTION_FAILED
    assert "FFmpeg failed with exit code 1" in res.error.message
    runner.shutdown()
