from __future__ import annotations

import stat
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.domain.result import ConversionResult
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner

if HAS_NATIVE:
    from colossal import colossal_native

# The mock "ffmpeg" script blocks on a "go<n>" marker BEFORE writing each
# stderr line whose go_n is not None, so the test controls exactly which
# lines have been written (and therefore observed by the progress parser)
# at any point — no race with the subprocess writing ahead. A "kill" marker
# lets the test abort the script immediately if an assertion fails, so a
# failure can never leave the subprocess (and the non-daemon runner thread)
# permanently blocked.
SCRIPTED_FFMPEG = """#!{python}
import sys, pathlib, time

godir = pathlib.Path({godir!r})
dst = pathlib.Path({dst!r})

def wait_go(n):
    marker = godir / f"go{{n}}"
    kill = godir / "kill"
    while not marker.exists():
        if kill.exists():
            sys.exit(1)
        time.sleep(0.01)

for line, go_n in {lines!r}:
    if go_n is not None:
        wait_go(go_n)
    sys.stderr.write(line + "\\n")
    sys.stderr.flush()

dst.write_bytes(b"fake mp3 data")
sys.exit(0)
"""


def _make_job(tmp_path: Path) -> tuple[ConversionJob, Path]:
    dst = tmp_path / "song.mp3"
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "song.wav",
        input_format_id="wav",
        output_format_id="mp3",
        destination_path=dst,
    )
    cap = Capability(
        id="cap_wav_mp3_progress",
        name="WAV to MP3",
        input_formats=frozenset(["wav"]),
        output_formats=frozenset(["mp3"]),
        engine_id="ffmpeg",
    )
    stage = PipelineStage(0, "transcode", cap, "wav", "mp3")
    plan = ConversionPlan(req, ConversionPipeline((stage,)))
    return ConversionJob(plan=plan), dst


def _write_scripted_ffmpeg(
    script_path: Path, godir: Path, dst: Path, lines: list[tuple[str, int | None]]
) -> None:
    script_path.write_text(
        SCRIPTED_FFMPEG.format(python=sys.executable, godir=str(godir), dst=str(dst), lines=lines)
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)


def _wait_for(
    predicate: Callable[[], bool], timeout: float = 5.0, message: str = "condition not met"
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError(message)


class _ScriptedRun:
    """Runs a scripted-ffmpeg job on a daemon thread and guarantees the
    subprocess is released (via the "kill" marker) on __exit__ even if an
    assertion fails partway through, so a broken test can never hang the
    whole suite waiting for an orphaned blocked subprocess.
    """

    def __init__(self, tmp_path: Path, lines: list[tuple[str, int | None]]):
        self.tmp_path = tmp_path
        self.godir = tmp_path / "go"
        self.godir.mkdir()
        self.job, self.dst = _make_job(tmp_path)
        script_path = tmp_path / "fake_ffmpeg"
        _write_scripted_ffmpeg(script_path, self.godir, self.dst, lines)
        self.discovery = colossal_native.ToolDiscovery.instance()
        self.discovery.clear_cache()
        self.discovery.register_custom_path("ffmpeg", script_path)
        self.runner = NativeJobRunner(thread_count=2)
        self.result_holder: dict[str, ConversionResult] = {}
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self.result_holder["result"] = self.runner.execute_job(self.job)

    def start(self) -> None:
        self.thread.start()
        _wait_for(
            lambda: self.runner._active_jobs.get(self.job.id) is not None,
            message="native job never registered as active",
        )

    def progress(self) -> float:
        native_job = self.runner._active_jobs.get(self.job.id)
        return float(native_job.progress) if native_job is not None else self.job.progress

    def release(self, n: int) -> None:
        (self.godir / f"go{n}").touch()

    def wait_progress_at_least(self, value: float, timeout: float = 5.0) -> float:
        _wait_for(
            lambda: self.progress() >= value,
            timeout=timeout,
            message=f"progress never reached {value} (last seen {self.progress()})",
        )
        return self.progress()

    def finish(self, timeout: float = 5.0) -> ConversionResult:
        self.thread.join(timeout=timeout)
        if self.thread.is_alive():
            (self.godir / "kill").touch()
            self.thread.join(timeout=2.0)
            raise AssertionError("scripted ffmpeg job did not finish in time")
        return self.result_holder["result"]

    def __enter__(self) -> _ScriptedRun:
        return self

    def __exit__(self, *exc_info: object) -> None:
        (self.godir / "kill").touch()
        self.thread.join(timeout=2.0)
        self.runner.shutdown()
        self.discovery.clear_cache()


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_progress_reflects_real_duration_and_time(tmp_path: Path) -> None:
    """Duration + time= lines must produce real, monotonically increasing,
    roughly-correct fractional progress — not a fixed fabricated number.
    """
    with _ScriptedRun(
        tmp_path,
        [
            ("Duration: 00:00:10.00, start: 0.000000, bitrate: 128 kb/s", None),
            ("time=00:00:02.50 bitrate=100kbits/s speed=1x", 1),
            ("time=00:00:05.00 bitrate=100kbits/s speed=1x", 2),
            ("time=00:00:10.00 bitrate=100kbits/s speed=1x", 3),
        ],
    ) as run:
        run.start()
        time.sleep(0.1)
        assert run.progress() == 0.0  # Duration alone must not move progress

        run.release(1)  # gates writing "time=00:00:02.50"
        progress_25 = run.wait_progress_at_least(0.2)
        assert 0.2 <= progress_25 < 0.3

        run.release(2)  # gates writing "time=00:00:05.00"
        progress_50 = run.wait_progress_at_least(0.45)
        assert 0.45 <= progress_50 < 0.55
        assert progress_50 > progress_25

        run.release(3)  # gates writing "time=00:00:10.00"
        result = run.finish()

        assert result.status == JobStatus.COMPLETED
        assert run.job.progress == 1.0


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_missing_duration_does_not_fabricate_progress(tmp_path: Path) -> None:
    """Without a parsed Duration, time= lines must not move progress at all
    (no fallback fabricated percentage), matching the "honest indeterminate
    state" requirement.
    """
    with _ScriptedRun(
        tmp_path,
        [
            ("time=00:00:02.50 bitrate=100kbits/s speed=1x", None),
            ("frame=  120 fps= 30 q=-1.0 Lsize=  1234kB", 1),
        ],
    ) as run:
        run.start()
        time.sleep(0.2)  # give the parent time to read+ignore the time= line
        assert run.progress() == 0.0

        run.release(1)
        result = run.finish()
        assert result.status == JobStatus.COMPLETED


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_time_exceeding_duration_clamps_without_crashing(tmp_path: Path) -> None:
    """A time= value larger than the parsed Duration (can happen with VBR
    padding/rounding in real ffmpeg output) must clamp to 100%, not exceed
    1.0 or raise.
    """
    with _ScriptedRun(
        tmp_path,
        [
            ("Duration: 00:00:10.00, start: 0.000000, bitrate: 128 kb/s", None),
            ("time=00:00:20.00 bitrate=100kbits/s speed=1x", 1),
        ],
    ) as run:
        run.start()
        run.release(1)
        progress = run.wait_progress_at_least(1.0)
        assert progress == 1.0

        result = run.finish()
        assert result.status == JobStatus.COMPLETED
        assert run.job.progress == 1.0
