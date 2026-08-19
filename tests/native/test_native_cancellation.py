from __future__ import annotations

import os
import stat
import threading
import time
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.domain.result import ConversionResult
from colossal.runtime.catalog import FormatCatalog
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner
from colossal.services.conversion_service import ConversionApplicationService

if HAS_NATIVE:
    from colossal import colossal_native

SLOW_SCRIPT = """#!/usr/bin/env python3
import pathlib, os, time
pathlib.Path({pidfile!r}).write_text(str(os.getpid()))
time.sleep(30)
pathlib.Path({donefile!r}).write_text("done")
"""


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_cancel_terminates_running_subprocess(tmp_path: Path) -> None:
    """Cancelling a job while its subprocess is actually running must kill the
    subprocess (and its process group), not merely flip job state.
    """
    pidfile = tmp_path / "pid.txt"
    donefile = tmp_path / "done.txt"
    script_path = tmp_path / "fake_ffmpeg"
    script_path.write_text(SLOW_SCRIPT.format(pidfile=str(pidfile), donefile=str(donefile)))
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    discovery = colossal_native.ToolDiscovery.instance()
    discovery.clear_cache()
    discovery.register_custom_path("ffmpeg", script_path)

    try:
        req = ConversionRequest.from_single_file(
            input_path=tmp_path / "song.wav",
            input_format_id="wav",
            output_format_id="mp3",
            destination_path=tmp_path / "song.mp3",
        )
        cap = Capability(
            id="cap_wav_mp3",
            name="WAV to MP3",
            input_formats=frozenset(["wav"]),
            output_formats=frozenset(["mp3"]),
            engine_id="ffmpeg",
        )
        stage = PipelineStage(0, "transcode", cap, "wav", "mp3")
        plan = ConversionPlan(req, ConversionPipeline((stage,)))
        job = ConversionJob(plan=plan)

        runner = NativeJobRunner(thread_count=2)
        result_holder: dict[str, ConversionResult] = {}

        def run() -> None:
            result_holder["result"] = runner.execute_job(job)

        t = threading.Thread(target=run)
        t.start()

        # Wait for the subprocess to actually start and record its PID.
        deadline = time.monotonic() + 5.0
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert pidfile.exists(), "fake ffmpeg subprocess never started"
        child_pid = int(pidfile.read_text().strip())
        assert _pid_alive(child_pid)

        # Cancel while it is genuinely mid-execution (it sleeps for 30s).
        cancelled = runner.request_cancel(job.id)
        assert cancelled, "request_cancel found no in-flight native job"

        t.join(timeout=5.0)
        assert not t.is_alive(), "execute_job did not return after cancellation"

        # The subprocess must actually be dead, not left running.
        deadline = time.monotonic() + 2.0
        while _pid_alive(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not _pid_alive(child_pid), "cancelled subprocess is still running"

        # It must not have been allowed to run to completion.
        assert not donefile.exists()

        result = result_holder["result"]
        assert result.status == JobStatus.CANCELLED
        assert job.status == JobStatus.CANCELLED
        assert result.output_artifacts == ()

        runner.shutdown()
    finally:
        discovery.clear_cache()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_service_cancel_job_terminates_running_subprocess(tmp_path: Path) -> None:
    """The real UI-facing path (ConversionApplicationService.request_cancel_job)
    must also stop a genuinely in-flight native subprocess.
    """
    pidfile = tmp_path / "pid.txt"
    donefile = tmp_path / "done.txt"
    script_path = tmp_path / "fake_ffmpeg"
    script_path.write_text(SLOW_SCRIPT.format(pidfile=str(pidfile), donefile=str(donefile)))
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    discovery = colossal_native.ToolDiscovery.instance()
    discovery.clear_cache()
    discovery.register_custom_path("ffmpeg", script_path)

    try:
        service = ConversionApplicationService(
            catalog=FormatCatalog.load_default(), runner=NativeJobRunner(thread_count=2)
        )
        input_path = tmp_path / "song.wav"
        input_path.touch()
        job = service.create_single_job(input_path=input_path, output_format_id="mp3")

        result_holder: dict[str, ConversionResult] = {}

        def run() -> None:
            result_holder["result"] = service.execute_job(job)

        t = threading.Thread(target=run)
        t.start()

        deadline = time.monotonic() + 5.0
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert pidfile.exists(), "fake ffmpeg subprocess never started"
        child_pid = int(pidfile.read_text().strip())

        service.request_cancel_job(job)

        t.join(timeout=5.0)
        assert not t.is_alive()

        deadline = time.monotonic() + 2.0
        while _pid_alive(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not _pid_alive(child_pid), "cancelled subprocess is still running"
        assert not donefile.exists()

        result = result_holder["result"]
        assert result.status == JobStatus.CANCELLED
        assert job.status == JobStatus.CANCELLED

        service.runner.shutdown()
    finally:
        discovery.clear_cache()
