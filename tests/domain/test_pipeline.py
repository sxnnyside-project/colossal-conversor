from __future__ import annotations

import pytest

from colossal.domain.capability import Capability
from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.pipeline import ConversionPipeline, PipelineStage


def test_single_stage_pipeline() -> None:
    cap = Capability(
        id="cap_wav_mp3",
        name="WAV to MP3",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["mp3"]),
        engine_id="ffmpeg",
    )
    pipeline = ConversionPipeline.from_single_capability(cap, "wav", "mp3")
    assert not pipeline.is_multi_stage
    assert pipeline.stage_count == 1
    assert pipeline.initial_format_id == "wav"
    assert pipeline.final_format_id == "mp3"


def test_multi_stage_pipeline() -> None:
    cap1 = Capability(
        id="cap_pptx_pdf",
        name="PPTX to PDF",
        input_formats=frozenset(["pptx"]),
        output_formats=frozenset(["pdf"]),
        engine_id="soffice",
    )
    cap2 = Capability(
        id="cap_pdf_png",
        name="PDF to PNG",
        input_formats=frozenset(["pdf"]),
        output_formats=frozenset(["png"]),
        engine_id="pdftoppm",
        cardinality=ConversionCardinality.ONE_TO_MANY,
    )

    stage0 = PipelineStage(
        stage_index=0,
        name="render_pdf",
        capability=cap1,
        input_format_id="pptx",
        output_format_id="pdf",
    )
    stage1 = PipelineStage(
        stage_index=1,
        name="rasterize_pages",
        capability=cap2,
        input_format_id="pdf",
        output_format_id="png",
    )

    pipeline = ConversionPipeline(stages=(stage0, stage1))
    assert pipeline.is_multi_stage
    assert pipeline.stage_count == 2
    assert pipeline.initial_format_id == "pptx"
    assert pipeline.final_format_id == "png"


def test_pipeline_validation_format_discontinuity() -> None:
    cap1 = Capability(
        id="cap1",
        name="PPTX to PDF",
        input_formats=frozenset(["pptx"]),
        output_formats=frozenset(["pdf"]),
        engine_id="soffice",
    )
    cap2 = Capability(
        id="cap2",
        name="DOCX to TXT",
        input_formats=frozenset(["docx"]),
        output_formats=frozenset(["txt"]),
        engine_id="pandoc",
    )

    stage0 = PipelineStage(
        stage_index=0,
        name="s0",
        capability=cap1,
        input_format_id="pptx",
        output_format_id="pdf",
    )
    stage1 = PipelineStage(
        stage_index=1,
        name="s1",
        capability=cap2,
        input_format_id="docx",
        output_format_id="txt",
    )

    with pytest.raises(ConversionError) as exc_info:
        ConversionPipeline(stages=(stage0, stage1))
    assert exc_info.value.code == ConversionErrorCode.PIPELINE_FAILURE
