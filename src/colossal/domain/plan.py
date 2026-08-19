from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.pipeline import ConversionPipeline
from colossal.domain.request import ConversionRequest


@dataclass(frozen=True)
class ConversionPlan:
    request: ConversionRequest
    pipeline: ConversionPipeline
    cardinality: ConversionCardinality = ConversionCardinality.ONE_TO_ONE
    intermediate_directory: Path | None = None

    def __post_init__(self) -> None:
        if self.intermediate_directory is not None:
            object.__setattr__(
                self,
                "intermediate_directory",
                Path(self.intermediate_directory).resolve(),
            )
