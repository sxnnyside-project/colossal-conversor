from __future__ import annotations

from pathlib import Path

import pytest

from colossal.runtime.native_runner import HAS_NATIVE

if HAS_NATIVE:
    from colossal import colossal_native


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_types_and_enums() -> None:
    assert colossal_native.JobStatus.Pending is not None
    assert colossal_native.JobStatus.Running is not None
    assert colossal_native.JobStatus.Completed is not None
    assert colossal_native.JobStatus.Failed is not None
    assert colossal_native.JobStatus.Cancelled is not None

    assert colossal_native.Cardinality.OneToOne is not None
    assert colossal_native.Cardinality.OneToMany is not None

    assert colossal_native.ArtifactRole.Input is not None
    assert colossal_native.ArtifactRole.Output is not None

    assert colossal_native.ErrorCode.ExecutionFailed is not None


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_job_state_machine(tmp_path: Path) -> None:
    req = colossal_native.Request()
    req.id = "test_job_1"
    req.output_format_id = "mp3"
    req.destination_path = tmp_path / "out.mp3"

    art = colossal_native.Artifact(
        tmp_path / "in.wav", "wav", colossal_native.ArtifactRole.Input, 1024
    )
    req.input_artifacts = [art]

    pipeline = colossal_native.Pipeline()
    stage = colossal_native.PipelineStage()
    stage.stage_index = 0
    stage.name = "audio_transcode"
    stage.input_format_id = "wav"
    stage.output_format_id = "mp3"

    cap = colossal_native.Capability()
    cap.id = "ffmpeg_audio"
    cap.name = "FFmpeg Audio"
    cap.engine_id = "ffmpeg"
    cap.input_formats = {"wav"}
    cap.output_formats = {"mp3"}
    stage.capability = cap

    pipeline.stages = [stage]
    pipeline.validate()

    job = colossal_native.Job("test_job_1", req, pipeline)
    s0: colossal_native.JobStatus = job.status
    assert s0 == colossal_native.JobStatus.Pending
    assert job.progress == 0.0

    job.start()
    s1: colossal_native.JobStatus = job.status
    assert s1 == colossal_native.JobStatus.Running

    job.update_progress(0.75)
    assert job.progress == 0.75

    out_art = colossal_native.Artifact(
        tmp_path / "out.mp3", "mp3", colossal_native.ArtifactRole.Output, 2048
    )
    job.complete([out_art])
    s2: colossal_native.JobStatus = job.status
    assert s2 == colossal_native.JobStatus.Completed
    assert job.progress == 1.0
    assert len(job.produced_artifacts) == 1
