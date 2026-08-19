from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from colossal.domain.job import ConversionJob, JobStatus


@dataclass
class ConversionBatch:
    jobs: tuple[ConversionJob, ...]
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.jobs:
            raise ValueError("ConversionBatch must contain at least one job")

    @property
    def total_count(self) -> int:
        return len(self.jobs)

    @property
    def completed_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.FAILED)

    @property
    def cancelled_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.CANCELLED)

    @property
    def aggregate_progress(self) -> float:
        if not self.jobs:
            return 0.0
        return sum(j.progress for j in self.jobs) / len(self.jobs)

    @property
    def is_terminal(self) -> bool:
        return all(j.status.is_terminal for j in self.jobs)

    @property
    def status(self) -> JobStatus:
        statuses = {j.status for j in self.jobs}
        if all(s == JobStatus.PENDING for s in statuses):
            return JobStatus.PENDING
        if all(s == JobStatus.COMPLETED for s in statuses):
            return JobStatus.COMPLETED
        if all(s == JobStatus.CANCELLED for s in statuses):
            return JobStatus.CANCELLED
        if all(s == JobStatus.FAILED for s in statuses):
            return JobStatus.FAILED
        if any(s == JobStatus.RUNNING for s in statuses):
            return JobStatus.RUNNING
        if any(s == JobStatus.CANCELLING for s in statuses):
            return JobStatus.CANCELLING
        if self.is_terminal:
            # Mix of completed, failed, cancelled, or partial
            return JobStatus.PARTIAL
        return JobStatus.RUNNING

    def cancel_all(self) -> None:
        for job in self.jobs:
            job.request_cancel()

    def request_cancel(self) -> None:
        self.cancel_all()
