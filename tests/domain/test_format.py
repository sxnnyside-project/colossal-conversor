from __future__ import annotations

from pathlib import Path

from colossal.domain.format import Format, FormatCategory


def test_format_creation_and_normalization() -> None:
    fmt = Format(
        id="PNG",
        category=FormatCategory.IMAGE,
        label="PNG Image",
        extensions=("png", ".PNG"),
        mime_types=("image/png",),
        lossy=False,
    )
    assert fmt.id == "png"
    assert fmt.category == FormatCategory.IMAGE
    assert fmt.extensions == (".png", ".png")
    assert fmt.primary_extension == ".png"
    assert not fmt.lossy


def test_format_matches_extension() -> None:
    fmt = Format(
        id="mp3",
        category=FormatCategory.AUDIO,
        label="MP3 Audio",
        extensions=(".mp3",),
    )
    assert fmt.matches_extension("mp3")
    assert fmt.matches_extension(".mp3")
    assert fmt.matches_extension(".MP3")
    assert fmt.matches_extension(Path("song.mp3"))
    assert not fmt.matches_extension(Path("song.wav"))
    assert not fmt.matches_extension(".flac")


def test_format_category_enum() -> None:
    assert FormatCategory.AUDIO.value == "audio"
    assert FormatCategory.VIDEO.value == "video"
    assert FormatCategory.DOCUMENT.value == "document"
    assert FormatCategory.SHEET.value == "sheet"
    assert FormatCategory.SLIDE.value == "slide"
    assert FormatCategory.IMAGE.value == "image"
    assert FormatCategory.OTHER.value == "other"
