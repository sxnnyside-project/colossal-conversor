from __future__ import annotations

from pathlib import Path

import pytest

from colossal.domain.artifact import ConversionArtifact
from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.request import ConversionRequest
from colossal.domain.resolver import SimplePlanResolver


def test_job_successful_lifecycle(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "in.wav",
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=tmp_path / "out.mp3",
    )
    plan = resolver.create_plan(req)
    job = ConversionJob(plan=plan)

    s0: JobStatus = job.status
    assert s0 == JobStatus.PENDING
    assert job.progress == 0.0

    job.start()
    s1: JobStatus = job.status
    assert s1 == JobStatus.RUNNING
    assert job.started_at is not None

    job.update_progress(0.45)
    assert job.progress == 0.45

    out_artifact = ConversionArtifact(path=tmp_path / "out.mp3", format_id="mp3")
    job.complete(artifacts=[out_artifact])

    s2: JobStatus = job.status
    assert s2 == JobStatus.COMPLETED
    assert job.progress == 1.0
    assert job.finished_at is not None
    assert len(job.produced_artifacts) == 1


def test_job_cancellation_flow(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "video.mp4",
        input_format_id="mp4",
        output_format_id="mkv",
        destination_path=tmp_path / "video.mkv",
    )
    plan = resolver.create_plan(req)

    # Cancel while pending
    job_pending = ConversionJob(plan=plan)
    job_pending.request_cancel()
    sp: JobStatus = job_pending.status
    assert sp == JobStatus.CANCELLED

    # Cancel while running
    job_running = ConversionJob(plan=plan)
    job_running.start()
    job_running.request_cancel()
    sr1: JobStatus = job_running.status
    assert sr1 == JobStatus.CANCELLING

    job_running.mark_cancelled()
    sr2: JobStatus = job_running.status
    assert sr2 == JobStatus.CANCELLED


def test_job_failure_flow(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "bad.txt",
        input_format_id="txt",
        output_format_id="pdf",
        destination_path=tmp_path / "bad.pdf",
    )
    plan = resolver.create_plan(req)
    job = ConversionJob(plan=plan)
    job.start()

    error = ConversionError(
        code=ConversionErrorCode.EXECUTION_FAILED,
        message="Converter crashed with exit code 1",
    )
    job.fail(error)

    sf: JobStatus = job.status
    assert sf == JobStatus.FAILED
    assert len(job.errors) == 1
    assert job.errors[0].code == ConversionErrorCode.EXECUTION_FAILED


def test_invalid_state_transition_raises_error(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "in.wav",
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=tmp_path / "out.mp3",
    )
    plan = resolver.create_plan(req)
    job = ConversionJob(plan=plan)
    job.start()
    job.complete()

    with pytest.raises(ConversionError) as exc_info:
        job.start()
    assert exc_info.value.code == ConversionErrorCode.INVALID_REQUEST

    with pytest.raises(ConversionError) as exc_info2:
        job.update_progress(0.5)
    assert exc_info2.value.code == ConversionErrorCode.INVALID_REQUEST
