from __future__ import annotations

from colossal.domain.capability import Capability
from colossal.domain.cardinality import ConversionCardinality


def test_capability_support_and_normalization() -> None:
    cap = Capability(
        id="ffmpeg_audio",
        name="FFmpeg Audio Transcoder",
        input_formats=frozenset(["WAV", "FLAC", "OGG"]),
        output_formats=frozenset(["MP3", "AAC"]),
        engine_id="ffmpeg",
        cardinality=ConversionCardinality.ONE_TO_ONE,
        fidelity="high",
        warnings=("lossy_compression",),
        limitations=(),
    )
    assert cap.supports("wav", "mp3")
    assert cap.supports("WAV", "MP3")
    assert cap.supports("flac", "aac")
    assert not cap.supports("wav", "flac")
    assert not cap.supports("mp4", "mp3")
    assert cap.fidelity == "high"
    assert "lossy_compression" in cap.warnings
