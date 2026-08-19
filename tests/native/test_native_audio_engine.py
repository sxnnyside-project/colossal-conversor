from __future__ import annotations

from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner


def _create_wav_file(
    channels: int = 2, sample_rate: int = 44100, samples_per_channel: int = 100
) -> bytes:
    data_size = samples_per_channel * channels * 2
    file_size = 36 + data_size
    byte_rate = sample_rate * channels * 2
    block_align = channels * 2

    header = bytearray(44)
    header[0:4] = b"RIFF"
    header[4:8] = file_size.to_bytes(4, "little")
    header[8:16] = b"WAVEfmt "
    header[16:20] = (16).to_bytes(4, "little")
    header[20:22] = (1).to_bytes(2, "little")  # PCM
    header[22:24] = channels.to_bytes(2, "little")
    header[24:28] = sample_rate.to_bytes(4, "little")
    header[28:32] = byte_rate.to_bytes(4, "little")
    header[32:34] = block_align.to_bytes(2, "little")
    header[34:36] = (16).to_bytes(2, "little")
    header[36:40] = b"data"
    header[40:44] = data_size.to_bytes(4, "little")

    data = b"\x00\x10" * (samples_per_channel * channels)
    return bytes(header + data)


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_native_audio_engine_in_process_wav(tmp_path: Path) -> None:
    in_wav = tmp_path / "stereo.wav"
    in_wav.write_bytes(_create_wav_file(channels=2, sample_rate=44100, samples_per_channel=50))
    out_wav = tmp_path / "mono.wav"

    req = ConversionRequest.from_single_file(
        in_wav, "wav", "wav", out_wav, options={"channels": "1"}
    )
    cap = Capability(
        id="cap_native_audio_wav",
        name="Native Audio WAV processor",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["wav"]),
        engine_id="native_audio",
        requirements=(),  # Zero external tool requirements!
    )
    stage = PipelineStage(0, "downmix_wav", cap, "wav", "wav", options={"channels": "1"})
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    job = ConversionJob(plan=plan)

    runner = NativeJobRunner(thread_count=2, temp_dir=tmp_path)
    res = runner.execute_job(job)

    assert res.is_success
    assert job.status == JobStatus.COMPLETED
    assert out_wav.exists()
    header = out_wav.read_bytes()[:44]
    channels = int.from_bytes(header[22:24], "little")
    assert channels == 1
    runner.shutdown()
