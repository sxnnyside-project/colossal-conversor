from __future__ import annotations

from pathlib import Path

from colossal.domain.batch import ConversionBatch
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.request import ConversionRequest
from colossal.domain.resolver import SimplePlanResolver


def test_batch_aggregate_status_and_progress(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req1 = ConversionRequest.from_single_file(tmp_path / "a.wav", "wav", "mp3", tmp_path / "a.mp3")
    req2 = ConversionRequest.from_single_file(tmp_path / "b.wav", "wav", "mp3", tmp_path / "b.mp3")

    job1 = ConversionJob(plan=resolver.create_plan(req1))
    job2 = ConversionJob(plan=resolver.create_plan(req2))

    batch = ConversionBatch(jobs=(job1, job2))
    initial_status: JobStatus = batch.status
    assert initial_status == JobStatus.PENDING
    assert batch.aggregate_progress == 0.0

    job1.start()
    job2.start()
    job1.update_progress(1.0)
    job1.complete()
    job2.update_progress(0.5)

    assert batch.completed_count == 1

    job2.complete()
    final_status: JobStatus = batch.status
    assert final_status == JobStatus.COMPLETED
    assert batch.aggregate_progress == 1.0
    assert batch.is_terminal


def test_batch_cancel_all(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req1 = ConversionRequest.from_single_file(tmp_path / "a.wav", "wav", "mp3", tmp_path / "a.mp3")
    req2 = ConversionRequest.from_single_file(tmp_path / "b.wav", "wav", "mp3", tmp_path / "b.mp3")

    job1 = ConversionJob(plan=resolver.create_plan(req1))
    job2 = ConversionJob(plan=resolver.create_plan(req2))

    batch = ConversionBatch(jobs=(job1, job2))
    batch.cancel_all()

    j1_status: JobStatus = job1.status
    j2_status: JobStatus = job2.status
    batch_status: JobStatus = batch.status

    assert j1_status == JobStatus.CANCELLED
    assert j2_status == JobStatus.CANCELLED
    assert batch_status == JobStatus.CANCELLED
