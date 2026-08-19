import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from colossal.domain.capability import Capability
from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.format import Format, FormatCategory
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest, DestinationIntent


@pytest.fixture(autouse=True)
def _isolate_user_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from reading/writing the real user's
    ~/.config/colossal/settings.json (Translator.set_language persists there
    unconditionally, so without this every test run silently changes the
    developer's/CI machine's actual language preference).
    """
    import colossal.i18n.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_config_file_path", lambda: tmp_path / "settings.json")


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    return app


@pytest.fixture
def sample_audio_format() -> Format:
    return Format(
        id="mp3",
        category=FormatCategory.AUDIO,
        label="MP3 Audio",
        extensions=(".mp3",),
        mime_types=("audio/mpeg",),
        lossy=True,
    )


@pytest.fixture
def sample_capability() -> Capability:
    return Capability(
        id="ffmpeg_audio_transcode",
        name="FFmpeg Audio Transcoder",
        input_formats=frozenset(["wav", "flac", "ogg"]),
        output_formats=frozenset(["mp3", "aac"]),
        engine_id="ffmpeg",
        cardinality=ConversionCardinality.ONE_TO_ONE,
        fidelity="high",
        warnings=("lossy_compression",),
    )


@pytest.fixture
def sample_single_request(tmp_path: Path) -> ConversionRequest:
    inp = tmp_path / "input.wav"
    inp.write_bytes(b"RIFF dummy wav data")
    dst = tmp_path / "output.mp3"
    return ConversionRequest.from_single_file(
        input_path=inp,
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=dst,
        destination_intent=DestinationIntent.FILE,
    )


@pytest.fixture
def sample_plan(
    sample_single_request: ConversionRequest, sample_capability: Capability
) -> ConversionPlan:
    stage = PipelineStage(
        stage_index=0,
        name="audio_transcode",
        capability=sample_capability,
        input_format_id="wav",
        output_format_id="mp3",
    )
    pipeline = ConversionPipeline(stages=(stage,))
    return ConversionPlan(
        request=sample_single_request,
        pipeline=pipeline,
        cardinality=ConversionCardinality.ONE_TO_ONE,
    )
