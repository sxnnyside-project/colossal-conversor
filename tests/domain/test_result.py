from __future__ import annotations

from pathlib import Path

from colossal.domain.artifact import ConversionArtifact
from colossal.domain.job import ConversionJob
from colossal.domain.request import ConversionRequest
from colossal.domain.resolver import SimplePlanResolver
from colossal.domain.result import ConversionResult


def test_conversion_result_from_job(tmp_path: Path) -> None:
    resolver = SimplePlanResolver()
    req = ConversionRequest.from_single_file(
        tmp_path / "in.wav", "wav", "mp3", tmp_path / "out.mp3"
    )
    job: ConversionJob = ConversionJob(plan=resolver.create_plan(req))
    job.start()
    art = ConversionArtifact(path=tmp_path / "out.mp3", format_id="mp3")
    job.complete(artifacts=[art])

    result = ConversionResult.from_job(job)
    assert result.is_success
    assert not result.is_failed
    assert not result.is_cancelled
    assert len(result.output_artifacts) == 1
    assert result.output_artifacts[0].format_id == "mp3"
    assert result.duration_seconds is not None
