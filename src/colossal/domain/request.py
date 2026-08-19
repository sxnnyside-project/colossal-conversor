from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from colossal.domain.artifact import ArtifactRole, ConversionArtifact


class DestinationIntent(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    AUTOMATIC = "automatic"


@dataclass(frozen=True)
class ConversionRequest:
    input_artifacts: tuple[ConversionArtifact, ...]
    output_format_id: str
    destination_path: Path
    destination_intent: DestinationIntent = DestinationIntent.AUTOMATIC
    options: dict[str, Any] = field(default_factory=dict)
    requested_capability_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.input_artifacts:
            raise ValueError("ConversionRequest must contain at least one input artifact")
        object.__setattr__(self, "output_format_id", self.output_format_id.lower().strip())
        object.__setattr__(self, "destination_path", Path(self.destination_path).resolve())

    @property
    def is_multi_input(self) -> bool:
        return len(self.input_artifacts) > 1

    @property
    def primary_input(self) -> ConversionArtifact:
        return self.input_artifacts[0]

    @classmethod
    def from_single_file(
        cls,
        input_path: Path | str,
        input_format_id: str,
        output_format_id: str,
        destination_path: Path | str,
        destination_intent: DestinationIntent = DestinationIntent.AUTOMATIC,
        options: dict[str, Any] | None = None,
        requested_capability_id: str | None = None,
    ) -> ConversionRequest:
        artifact = ConversionArtifact(
            path=Path(input_path),
            format_id=input_format_id,
            role=ArtifactRole.INPUT,
        )
        return cls(
            input_artifacts=(artifact,),
            output_format_id=output_format_id,
            destination_path=Path(destination_path),
            destination_intent=destination_intent,
            options=options or {},
            requested_capability_id=requested_capability_id,
        )

    @classmethod
    def from_multiple_files(
        cls,
        input_files: list[tuple[Path | str, str]],
        output_format_id: str,
        destination_path: Path | str,
        destination_intent: DestinationIntent = DestinationIntent.DIRECTORY,
        options: dict[str, Any] | None = None,
        requested_capability_id: str | None = None,
    ) -> ConversionRequest:
        artifacts = tuple(
            ConversionArtifact(
                path=Path(path),
                format_id=fmt,
                role=ArtifactRole.INPUT,
            )
            for path, fmt in input_files
        )
        return cls(
            input_artifacts=artifacts,
            output_format_id=output_format_id,
            destination_path=Path(destination_path),
            destination_intent=destination_intent,
            options=options or {},
            requested_capability_id=requested_capability_id,
        )
