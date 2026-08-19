from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConversionErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_FORMAT = "unsupported_format"
    CAPABILITY_NOT_FOUND = "capability_not_found"
    MISSING_DEPENDENCY = "missing_dependency"
    EXECUTION_FAILED = "execution_failed"
    CANCELLED = "cancelled"
    OUTPUT_FAILURE = "output_failure"
    PIPELINE_FAILURE = "pipeline_failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


ErrorCode = ConversionErrorCode


@dataclass
class ConversionError(Exception):
    code: ConversionErrorCode
    message: str
    details: str | None = None
    stage_index: int | None = None
    fatal: bool = True
    recoverable: bool = False

    def __str__(self) -> str:
        base = f"[{self.code.value.upper()}] {self.message}"
        if self.stage_index is not None:
            base = f"{base} (stage {self.stage_index})"
        if self.details:
            base = f"{base}: {self.details}"
        return base
