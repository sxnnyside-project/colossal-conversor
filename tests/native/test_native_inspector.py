from __future__ import annotations

from pathlib import Path

import pytest

from colossal.runtime.native_runner import HAS_NATIVE
from colossal.utils.file_format import detect_file_format, detect_file_mime

if HAS_NATIVE:
    from colossal import colossal_native


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_format_detector_magic_bytes(tmp_path: Path) -> None:
    # PNG fixture
    png_file = tmp_path / "sample.bin"
    png_file.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x64\x00\x00\x00\x32\x08\x06\x00\x00\x00"
    )
    assert colossal_native.FormatDetector.detect_format(png_file) == "png"
    assert colossal_native.FormatDetector.detect_mime(png_file) == "image/png"
    assert detect_file_format(png_file) == "png"
    assert detect_file_mime(png_file) == "image/png"

    # JPEG fixture
    jpg_file = tmp_path / "sample_jpg.bin"
    jpg_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")
    assert colossal_native.FormatDetector.detect_format(jpg_file) == "jpeg"
    assert colossal_native.FormatDetector.detect_mime(jpg_file) == "image/jpeg"

    # PDF fixture
    pdf_file = tmp_path / "sample_pdf.bin"
    pdf_file.write_bytes(b"%PDF-1.4 /Count 5 %%EOF")
    assert colossal_native.FormatDetector.detect_format(pdf_file) == "pdf"
    assert colossal_native.FormatDetector.detect_mime(pdf_file) == "application/pdf"

    # WAV fixture
    wav_file = tmp_path / "sample_wav.bin"
    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00"
        b"\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00"
    )
    wav_file.write_bytes(wav_header)
    assert colossal_native.FormatDetector.detect_format(wav_file) == "wav"
    assert colossal_native.FormatDetector.detect_mime(wav_file) == "audio/wav"


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_media_inspector_metadata(tmp_path: Path) -> None:
    # 100x50 PNG
    png_file = tmp_path / "sample100x50.png"
    png_file.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x64\x00\x00\x00\x32\x08\x06\x00\x00\x00"
    )

    meta = colossal_native.MediaInspector.inspect(png_file)
    assert meta.format_id == "png"
    assert meta.width == 100
    assert meta.height == 50
    assert meta.file_size_bytes == len(png_file.read_bytes())

    # WAV 44100Hz Stereo
    wav_file = tmp_path / "stereo44k.wav"
    wav_header = bytearray(44)
    wav_header[0:4] = b"RIFF"
    wav_header[8:12] = b"WAVE"
    wav_header[22:24] = (2).to_bytes(2, "little")  # 2 channels
    wav_header[24:28] = (44100).to_bytes(4, "little")  # 44100 sample rate
    wav_header[28:32] = (176400).to_bytes(4, "little")  # 176400 bytes/sec
    wav_header[34:36] = (16).to_bytes(2, "little")  # 16-bit
    wav_header[36:40] = b"data"
    wav_data = b"\x00" * (176400 * 2)  # 2 seconds of audio
    wav_file.write_bytes(bytes(wav_header) + wav_data)

    audio_meta = colossal_native.MediaInspector.inspect(wav_file)
    assert audio_meta.format_id == "wav"
    assert audio_meta.channels == 2
    assert audio_meta.sample_rate == 44100
    assert audio_meta.duration_seconds is not None
    assert round(audio_meta.duration_seconds) == 2
