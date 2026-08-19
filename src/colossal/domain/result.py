from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from colossal.domain.artifact import ConversionArtifact
from colossal.domain.error import ConversionError
from colossal.domain.job import ConversionJob, JobStatus


@dataclass(frozen=True)
class ConversionResult:
    job_id: str
    status: JobStatus
    output_artifacts: tuple[ConversionArtifact, ...] = field(default_factory=tuple)
    error: ConversionError | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    duration_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == JobStatus.COMPLETED

    @property
    def is_partial(self) -> bool:
        return self.status == JobStatus.PARTIAL

    @property
    def is_cancelled(self) -> bool:
        return self.status == JobStatus.CANCELLED

    @property
    def is_failed(self) -> bool:
        return self.status == JobStatus.FAILED

    @property
    def primary_output(self) -> ConversionArtifact | None:
        return self.output_artifacts[0] if self.output_artifacts else None

    @classmethod
    def from_job(cls, job: ConversionJob) -> ConversionResult:
        duration: float | None = None
        if job.started_at and job.finished_at:
            duration = (job.finished_at - job.started_at).total_seconds()

        primary_error: ConversionError | None = job.errors[0] if job.errors else None

        return cls(
            job_id=job.id,
            status=job.status,
            output_artifacts=tuple(job.produced_artifacts),
            error=primary_error,
            warnings=tuple(job.warnings),
            duration_seconds=duration,
            metadata={
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "error_count": len(job.errors),
                "intermediate_count": len(job.intermediate_artifacts),
            },
        )
