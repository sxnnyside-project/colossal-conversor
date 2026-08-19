from __future__ import annotations

import contextlib
import threading
from pathlib import Path

from colossal.domain.artifact import ArtifactRole, ConversionArtifact
from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.request import ConversionRequest
from colossal.domain.resolver import SimplePlanResolver


def _running_job(tmp_path: Path) -> ConversionJob:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "in.wav",
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=tmp_path / "out.mp3",
    )
    job = ConversionJob(plan=resolver.create_plan(req))
    job.start()
    return job


def test_request_cancel_races_with_complete(tmp_path: Path) -> None:
    artifact = ConversionArtifact(
        path=tmp_path / "out.mp3", format_id="mp3", role=ArtifactRole.OUTPUT, size_bytes=10
    )

    for _ in range(200):
        job = _running_job(tmp_path)
        barrier = threading.Barrier(2)

        def do_cancel(job: ConversionJob = job, barrier: threading.Barrier = barrier) -> None:
            barrier.wait()
            job.request_cancel()

        def do_complete(job: ConversionJob = job, barrier: threading.Barrier = barrier) -> None:
            barrier.wait()
            with contextlib.suppress(ConversionError):
                job.complete([artifact])

        t1 = threading.Thread(target=do_cancel)
        t2 = threading.Thread(target=do_complete)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # The job must land in exactly one terminal state with consistent data:
        # either it genuinely completed (real artifacts, no errors) or it is
        # cancelling/cancelled (no artifacts committed).
        assert job.status in (JobStatus.COMPLETED, JobStatus.CANCELLING, JobStatus.CANCELLED)
        if job.status == JobStatus.COMPLETED:
            assert job.produced_artifacts == [artifact]
        else:
            assert job.produced_artifacts == []


def test_request_cancel_races_with_fail(tmp_path: Path) -> None:
    err = ConversionError(code=ConversionErrorCode.EXECUTION_FAILED, message="boom")

    for _ in range(200):
        job = _running_job(tmp_path)
        barrier = threading.Barrier(2)

        def do_cancel(job: ConversionJob = job, barrier: threading.Barrier = barrier) -> None:
            barrier.wait()
            job.request_cancel()

        def do_fail(job: ConversionJob = job, barrier: threading.Barrier = barrier) -> None:
            barrier.wait()
            job.fail(err)

        t1 = threading.Thread(target=do_cancel)
        t2 = threading.Thread(target=do_fail)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert job.status in (JobStatus.FAILED, JobStatus.CANCELLING, JobStatus.CANCELLED)
        if job.status == JobStatus.FAILED:
            assert job.errors == [err]
        else:
            assert job.errors == []


def test_cancel_immediately_before_native_completion_is_reported_as_completed(
    tmp_path: Path,
) -> None:
    """Reproduces the narrow window where a cancel is requested (domain job
    transitions RUNNING -> CANCELLING) at essentially the same instant the
    native side genuinely finishes and reports success. The domain job must
    reach a real terminal state reflecting the artifacts that actually exist
    on disk, not raise and leave the job stuck in CANCELLING forever.
    """
    artifact = ConversionArtifact(
        path=tmp_path / "out.mp3", format_id="mp3", role=ArtifactRole.OUTPUT, size_bytes=10
    )
    job = _running_job(tmp_path)
    job.request_cancel()
    status_after_cancel: JobStatus = job.status
    assert status_after_cancel == JobStatus.CANCELLING

    # Native execution had already produced a valid result before the
    # cancellation could take effect; this must not raise.
    job.complete([artifact])

    status_after_complete: JobStatus = job.status
    assert status_after_complete == JobStatus.COMPLETED
    assert job.produced_artifacts == [artifact]
