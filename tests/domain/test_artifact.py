from __future__ import annotations

from pathlib import Path

from colossal.domain.artifact import ArtifactRole, ConversionArtifact


def test_artifact_properties_and_mutation(tmp_path: Path) -> None:
    file_path = tmp_path / "output.mp3"
    file_path.write_bytes(b"dummy audio data")

    artifact = ConversionArtifact(
        path=file_path,
        format_id="MP3",
        role=ArtifactRole.OUTPUT,
        size_bytes=len(b"dummy audio data"),
    )
    assert artifact.format_id == "mp3"
    assert artifact.role == ArtifactRole.OUTPUT
    assert artifact.exists
    assert artifact.name == "output.mp3"

    intermediate = artifact.with_role(ArtifactRole.INTERMEDIATE)
    assert intermediate.role == ArtifactRole.INTERMEDIATE
    assert intermediate.path == artifact.path

    resized = artifact.with_size(1024)
    assert resized.size_bytes == 1024
