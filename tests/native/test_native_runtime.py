from __future__ import annotations

from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_runner_instantiation() -> None:
    runner = NativeJobRunner(thread_count=2)
    assert runner is not None
    runner.shutdown()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_runner_cancelled_job(tmp_path: Path) -> None:
    runner = NativeJobRunner(thread_count=2)
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "song.wav",
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=tmp_path / "song.mp3",
    )
    cap = Capability(
        id="cap_wav_mp3",
        name="WAV to MP3",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["mp3"]),
        engine_id="ffmpeg",
    )
    stage = PipelineStage(0, "transcode", cap, "wav", "mp3")
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    job.request_cancel()
    result = runner.execute_job(job)

    assert result.is_cancelled
    assert job.status == JobStatus.CANCELLED
    runner.shutdown()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_runner_missing_capability(tmp_path: Path) -> None:
    runner = NativeJobRunner(thread_count=2)
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "song.wav",
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=tmp_path / "song.mp3",
    )
    cap = Capability(
        id="cap_missing_engine",
        name="Missing Engine Cap",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["mp3"]),
        engine_id="nonexistent_engine_xyz",
    )
    stage = PipelineStage(0, "transcode", cap, "wav", "mp3")
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    result = runner.execute_job(job)

    assert result.is_failed
    assert job.status == JobStatus.FAILED
    assert result.error is not None
    assert "No native engine registered" in result.error.message
    runner.shutdown()
