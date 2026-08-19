from __future__ import annotations

import os
from pathlib import Path

import pytest

from colossal.domain.capability import Capability
from colossal.domain.error import ConversionErrorCode
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest
from colossal.runtime.catalog import FormatCatalog
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner
from colossal.services.conversion_service import ConversionApplicationService

if HAS_NATIVE:
    from colossal import colossal_native


@pytest.mark.skipif(not HAS_NATIVE, reason="colossal_native C++ extension not available")
def test_missing_dependency_surfaces_as_actionable_error(tmp_path: Path) -> None:
    """A tool that genuinely isn't installed must produce a structured
    MissingDependency error at the native layer that survives the trip
    through NativeJobRunner and is translated into an actionable, non-raw
    message at the application layer — not a generic/internal failure.
    """
    discovery = colossal_native.ToolDiscovery.instance()
    discovery.clear_cache()
    empty_dir = tmp_path / "empty_path"
    empty_dir.mkdir()
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(empty_dir)

    try:
        req = ConversionRequest.from_single_file(
            input_path=tmp_path / "doc.md",
            input_format_id="md",
            output_format_id="html",
            destination_path=tmp_path / "doc.html",
        )
        cap = Capability(
            id="cap_md_html",
            name="Markdown to HTML",
            input_formats=frozenset(["md"]),
            output_formats=frozenset(["html"]),
            engine_id="pandoc",
        )
        stage = PipelineStage(0, "convert", cap, "md", "html")
        plan = ConversionPlan(req, ConversionPipeline((stage,)))
        job = ConversionJob(plan=plan)

        runner = NativeJobRunner(thread_count=2)
        result = runner.execute_job(job)

        assert result.status == JobStatus.FAILED
        assert result.error is not None
        assert result.error.code == ConversionErrorCode.MISSING_DEPENDENCY
        # The native error must not be a generic/unrelated failure category.
        assert "pandoc" in result.error.message.lower()

        service = ConversionApplicationService(catalog=FormatCatalog.load_default(), runner=runner)
        service.set_language("en")
        user_message = service.format_error_message(result.error)

        # The user-facing message must be the translated, actionable string —
        # not a raw internal error like "No native engine registered..." or a
        # generic unexpected-failure message.
        assert "external tool" in user_message
        assert "No native engine registered" not in user_message
        assert "unexpected error" not in user_message.lower()

        runner.shutdown()
    finally:
        os.environ["PATH"] = old_path
        discovery.clear_cache()
