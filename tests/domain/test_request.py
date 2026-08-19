from __future__ import annotations

from pathlib import Path

import pytest

from colossal.domain.request import ConversionRequest, DestinationIntent


def test_single_file_request(tmp_path: Path) -> None:
    inp = tmp_path / "input.wav"
    dst = tmp_path / "output.mp3"

    req = ConversionRequest.from_single_file(
        input_path=inp,
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=dst,
        destination_intent=DestinationIntent.FILE,
    )
    assert not req.is_multi_input
    assert req.primary_input.path == inp.resolve()
    assert req.output_format_id == "mp3"
    assert req.destination_path == dst.resolve()


def test_multi_file_request(tmp_path: Path) -> None:
    f1 = tmp_path / "doc1.docx"
    f2 = tmp_path / "doc2.docx"
    out_dir = tmp_path / "exports"

    req = ConversionRequest.from_multiple_files(
        input_files=[(f1, "docx"), (f2, "docx")],
        output_format_id="pdf",
        destination_path=out_dir,
    )
    assert req.is_multi_input
    assert len(req.input_artifacts) == 2
    assert req.destination_intent == DestinationIntent.DIRECTORY


def test_empty_request_raises_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one input artifact"):
        ConversionRequest(
            input_artifacts=(),
            output_format_id="mp3",
            destination_path=tmp_path / "out.mp3",
        )
