from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from colossal.domain.artifact import ConversionArtifact
from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.plan import ConversionPlan


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

    @property
    def is_terminal(self) -> bool:
        return self in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.PARTIAL,
        )

    @property
    def is_active(self) -> bool:
        return self in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.CANCELLING)


# Valid state transitions lookup table
_VALID_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.RUNNING: {
        JobStatus.CANCELLING,
        JobStatus.CANCELLED,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.PARTIAL,
    },
    JobStatus.CANCELLING: {
        JobStatus.CANCELLED,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.PARTIAL,
    },
    JobStatus.CANCELLED: set(),
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.PARTIAL: set(),
}


@dataclass
class ConversionJob:
    """Two threads mutate a ConversionJob in practice: the worker thread that
    runs the conversion (start/complete/fail/mark_cancelled) and the caller
    thread that may request cancellation at any time. `_lock` (an RLock, so
    a locked method may call another locked method on the same job) makes
    every status transition and artifact/error mutation atomic so the two
    threads can never observe or commit an inconsistent intermediate state.
    """

    plan: ConversionPlan
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    produced_artifacts: list[ConversionArtifact] = field(default_factory=list)
    intermediate_artifacts: list[ConversionArtifact] = field(default_factory=list)
    errors: list[ConversionError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def _transition_to(self, target: JobStatus) -> None:
        valid = _VALID_TRANSITIONS.get(self.status, set())
        if target not in valid:
            raise ConversionError(
                code=ConversionErrorCode.INVALID_REQUEST,
                message=f"Invalid job state transition from {self.status.value} to {target.value}",
            )
        self.status = target

    def start(self) -> None:
        with self._lock:
            self._transition_to(JobStatus.RUNNING)
            self.started_at = datetime.now(timezone.utc)

    def update_progress(self, value: float) -> None:
        with self._lock:
            if self.status not in (JobStatus.RUNNING, JobStatus.CANCELLING):
                raise ConversionError(
                    code=ConversionErrorCode.INVALID_REQUEST,
                    message=f"Cannot update progress when job is in '{self.status.value}' state",
                )
            self.progress = max(0.0, min(1.0, float(value)))

    def request_cancel(self) -> None:
        with self._lock:
            if self.status == JobStatus.PENDING:
                self._transition_to(JobStatus.CANCELLED)
                self.finished_at = datetime.now(timezone.utc)
            elif self.status == JobStatus.RUNNING:
                self._transition_to(JobStatus.CANCELLING)
            elif self.status == JobStatus.CANCELLING:
                # Already cancelling
                pass
            elif self.status.is_terminal:
                # Already finished
                pass

    def mark_cancelled(self) -> None:
        with self._lock:
            if self.status in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.CANCELLING):
                self._transition_to(JobStatus.CANCELLED)
                self.finished_at = datetime.now(timezone.utc)

    def complete(self, artifacts: Sequence[ConversionArtifact] | None = None) -> None:
        with self._lock:
            if artifacts:
                for art in artifacts:
                    self.add_produced_artifact(art)
            self._transition_to(JobStatus.COMPLETED)
            self.progress = 1.0
            self.finished_at = datetime.now(timezone.utc)

    def fail(self, error: ConversionError) -> None:
        with self._lock:
            self.errors.append(error)
            self._transition_to(JobStatus.FAILED)
            self.finished_at = datetime.now(timezone.utc)

    def mark_partial(
        self,
        artifacts: Sequence[ConversionArtifact],
        error: ConversionError | None = None,
    ) -> None:
        with self._lock:
            for art in artifacts:
                self.add_produced_artifact(art)
            if error:
                self.errors.append(error)
            self._transition_to(JobStatus.PARTIAL)
            self.finished_at = datetime.now(timezone.utc)

    def add_produced_artifact(self, artifact: ConversionArtifact) -> None:
        with self._lock:
            self.produced_artifacts.append(artifact)

    def add_intermediate_artifact(self, artifact: ConversionArtifact) -> None:
        with self._lock:
            self.intermediate_artifacts.append(artifact)

    def add_warning(self, warning: str) -> None:
        with self._lock:
            self.warnings.append(warning)
