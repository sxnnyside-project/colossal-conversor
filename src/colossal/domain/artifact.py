from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ArtifactRole(str, Enum):
    INPUT = "input"
    INTERMEDIATE = "intermediate"
    OUTPUT = "output"
    AUXILIARY = "auxiliary"


@dataclass(frozen=True)
class ConversionArtifact:
    path: Path
    format_id: str
    role: ArtifactRole = ArtifactRole.OUTPUT
    size_bytes: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path).resolve())
        object.__setattr__(self, "format_id", self.format_id.lower().strip())

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def with_role(self, role: ArtifactRole) -> ConversionArtifact:
        return ConversionArtifact(
            path=self.path,
            format_id=self.format_id,
            role=role,
            size_bytes=self.size_bytes,
            metadata=dict(self.metadata),
        )

    def with_size(self, size_bytes: int) -> ConversionArtifact:
        return ConversionArtifact(
            path=self.path,
            format_id=self.format_id,
            role=self.role,
            size_bytes=size_bytes,
            metadata=dict(self.metadata),
        )
