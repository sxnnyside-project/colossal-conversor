from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from colossal.domain.capability import Capability
from colossal.domain.error import ConversionError, ConversionErrorCode


@dataclass(frozen=True)
class PipelineStage:
    stage_index: int
    name: str
    capability: Capability
    input_format_id: str
    output_format_id: str
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_format_id", self.input_format_id.lower().strip())
        object.__setattr__(self, "output_format_id", self.output_format_id.lower().strip())
        if not self.capability.supports(self.input_format_id, self.output_format_id):
            msg = (
                f"Capability '{self.capability.id}' cannot convert "
                f"{self.input_format_id} to {self.output_format_id}"
            )
            raise ConversionError(
                code=ConversionErrorCode.CAPABILITY_NOT_FOUND,
                message=msg,
                stage_index=self.stage_index,
            )


@dataclass(frozen=True)
class ConversionPipeline:
    stages: tuple[PipelineStage, ...]

    def __post_init__(self) -> None:
        if not self.stages:
            raise ConversionError(
                code=ConversionErrorCode.INVALID_REQUEST,
                message="ConversionPipeline must contain at least one stage",
            )
        self.validate()

    @property
    def stage_count(self) -> int:
        return len(self.stages)

    @property
    def is_multi_stage(self) -> bool:
        return len(self.stages) > 1

    @property
    def initial_format_id(self) -> str:
        return self.stages[0].input_format_id

    @property
    def final_format_id(self) -> str:
        return self.stages[-1].output_format_id

    def validate(self) -> None:
        # Verify stage indices are contiguous starting at 0
        for i, stage in enumerate(self.stages):
            if stage.stage_index != i:
                raise ConversionError(
                    code=ConversionErrorCode.PIPELINE_FAILURE,
                    message=f"Stage index mismatch: expected {i}, got {stage.stage_index}",
                    stage_index=i,
                )
            if i > 0:
                prev_stage = self.stages[i - 1]
                if prev_stage.output_format_id != stage.input_format_id:
                    msg = (
                        f"Pipeline format discontinuity: stage {i - 1} outputs "
                        f"'{prev_stage.output_format_id}' but stage {i} expects "
                        f"'{stage.input_format_id}'"
                    )
                    raise ConversionError(
                        code=ConversionErrorCode.PIPELINE_FAILURE,
                        message=msg,
                        stage_index=i,
                    )

    @classmethod
    def from_single_capability(
        cls,
        capability: Capability,
        input_format_id: str,
        output_format_id: str,
        options: dict[str, Any] | None = None,
    ) -> ConversionPipeline:
        stage = PipelineStage(
            stage_index=0,
            name=f"{input_format_id}_to_{output_format_id}",
            capability=capability,
            input_format_id=input_format_id,
            output_format_id=output_format_id,
            options=options or {},
        )
        return cls(stages=(stage,))
