from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone

from .task_status import TaskStatus
from .conversion_error import ConversionError


@dataclass
class ConversionTask:
    input_path: Path
    output_path: Path
    input_format: str
    output_format: str
    options: Dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0

    error: Optional[ConversionError] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None


    def mark_running(self):
        self.status = TaskStatus.RUNNING

    def mark_done(self):
        self.status = TaskStatus.DONE
        self.progress = 1.0
        self.finished_at = datetime.now(timezone.utc)

    def mark_failed(self, error: ConversionError):
        self.status = TaskStatus.FAILED
        self.error = error
        self.finished_at = datetime.now(timezone.utc)

    def cancel(self):
        self.status = TaskStatus.CANCELLED
        self.finished_at = datetime.now(timezone.utc)
