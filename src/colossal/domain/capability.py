from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from colossal.domain.cardinality import ConversionCardinality


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    input_formats: frozenset[str]
    output_formats: frozenset[str]
    engine_id: str
    cardinality: ConversionCardinality = ConversionCardinality.ONE_TO_ONE
    fidelity: str = "medium"
    warnings: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)
    requirements: tuple[str, ...] = field(default_factory=tuple)
    options_schema: dict[str, Any] = field(default_factory=dict)
    default_preset: str | None = None

    def __post_init__(self) -> None:
        # Normalize format sets to lowercase
        normalized_inputs = frozenset(f.lower().strip() for f in self.input_formats)
        normalized_outputs = frozenset(f.lower().strip() for f in self.output_formats)
        object.__setattr__(self, "input_formats", normalized_inputs)
        object.__setattr__(self, "output_formats", normalized_outputs)

    def supports(self, input_format: str, output_format: str) -> bool:
        inp = input_format.lower().strip()
        out = output_format.lower().strip()
        return inp in self.input_formats and out in self.output_formats
