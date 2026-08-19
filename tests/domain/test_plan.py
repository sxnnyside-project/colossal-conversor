from __future__ import annotations

from pathlib import Path

from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.request import ConversionRequest
from colossal.domain.resolver import SimplePlanResolver


def test_plan_resolver_creates_plan(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "audio.flac",
        input_format_id="flac",
        output_format_id="mp3",
        destination_path=tmp_path / "audio.mp3",
    )
    plan = resolver.create_plan(req)
    assert plan.request == req
    assert plan.pipeline.initial_format_id == "flac"
    assert plan.pipeline.final_format_id == "mp3"
    assert plan.cardinality == ConversionCardinality.ONE_TO_ONE
