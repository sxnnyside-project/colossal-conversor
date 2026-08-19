from __future__ import annotations

from pathlib import Path

from colossal.domain.format import FormatCategory
from colossal.runtime.catalog import FormatCatalog


def test_catalog_load_default() -> None:
    catalog = FormatCatalog.load_default()

    # Formats loaded
    png = catalog.get_format("png")
    assert png is not None
    assert png.label == "PNG Image"
    assert png.category == FormatCategory.IMAGE
    assert not png.lossy

    mp3 = catalog.get_format("mp3")
    assert mp3 is not None
    assert mp3.label == "MP3 Audio"
    assert mp3.category == FormatCategory.AUDIO
    assert mp3.lossy


def test_catalog_format_by_extension() -> None:
    catalog = FormatCatalog.load_default()

    fmt1 = catalog.get_format_by_extension(".docx")
    assert fmt1 is not None
    assert fmt1.id == "docx"

    fmt2 = catalog.get_format_by_extension(Path("/tmp/presentation.pptx"))
    assert fmt2 is not None
    assert fmt2.id == "pptx"


def test_catalog_capabilities_loaded() -> None:
    catalog = FormatCatalog.load_default()
    assert len(catalog.capabilities) > 0

    # Capability resolution
    cap_audio = catalog.find_capability("wav", "mp3")
    assert cap_audio is not None
    assert cap_audio.engine_id == "ffmpeg"
    assert "ffmpeg" in cap_audio.requirements

    # Available output formats
    wav_outputs = catalog.get_available_output_formats("wav")
    assert "mp3" in wav_outputs
    assert "flac" in wav_outputs
