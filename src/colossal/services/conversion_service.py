from __future__ import annotations

from pathlib import Path
from typing import Any

from colossal.domain.batch import ConversionBatch
from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.format import Format, FormatCategory
from colossal.domain.job import ConversionJob
from colossal.domain.request import ConversionRequest, DestinationIntent
from colossal.domain.resolver import SimplePlanResolver
from colossal.domain.result import ConversionResult
from colossal.i18n.translator import Translator
from colossal.runtime.catalog import FormatCatalog
from colossal.runtime.native_runner import NativeJobRunner
from colossal.utils.file_format import detect_file_format, detect_file_mime


class ConversionApplicationService:
    """Application service coordinating conversion planning, format discovery,
    job creation, native execution, and user-facing error translation.
    """

    def __init__(
        self,
        catalog: FormatCatalog | None = None,
        runner: NativeJobRunner | None = None,
        translator: Translator | None = None,
    ) -> None:
        self._catalog = catalog or FormatCatalog.load_default()
        self._runner = runner or NativeJobRunner()
        self._translator = translator or Translator()
        self._resolver = SimplePlanResolver(self._catalog.capabilities)

    @property
    def catalog(self) -> FormatCatalog:
        return self._catalog

    @property
    def runner(self) -> NativeJobRunner:
        return self._runner

    @property
    def translator(self) -> Translator:
        return self._translator

    def set_language(self, lang: str) -> None:
        self._translator.set_language(lang)

    def detect_format(self, path: Path) -> Format:
        """Detect the authoritative Format for a given file using binary magic inspection."""
        detected_id = detect_file_format(path)
        fmt = self._catalog.get_format(detected_id)
        if fmt is not None:
            return fmt

        # Fallback by extension
        ext = path.suffix.lstrip(".").lower()
        fmt_by_ext = self._catalog.get_format(ext)
        if fmt_by_ext is not None:
            return fmt_by_ext

        # Return generic unknown Format
        mime = detect_file_mime(path)
        return Format(
            id=detected_id if detected_id != "unknown" else (ext or "unknown"),
            category=FormatCategory.OTHER,
            label=detected_id.upper() if detected_id != "unknown" else "Unknown",
            extensions=(f".{ext}",) if ext else (),
            mime_types=(mime,),
        )

    def get_available_outputs(self, input_formats: list[str]) -> set[str]:
        """Compute the set of valid output formats supported for the given input format(s)."""
        if not input_formats:
            return set()

        sets: list[set[str]] = []
        for in_fmt in input_formats:
            outs = self._catalog.get_available_output_formats(in_fmt)
            sets.append(outs)

        if not sets:
            return set()

        common = set(sets[0])
        for s in sets[1:]:
            common &= s
        return common

    def get_capability_details(self, input_fmt: str, output_fmt: str) -> dict[str, Any]:
        """Retrieve capability metadata (fidelity, warnings, limitations, cardinality)
        for a format conversion pair.
        """
        for cap in self._catalog.capabilities:
            if cap.supports(input_fmt, output_fmt):
                is_multi = cap.cardinality in (
                    ConversionCardinality.ONE_TO_MANY,
                    ConversionCardinality.MANY_TO_MANY,
                )
                return {
                    "capability_id": cap.id,
                    "engine_id": cap.engine_id,
                    "fidelity": cap.fidelity,
                    "warnings": list(cap.warnings),
                    "limitations": list(cap.limitations),
                    "cardinality": cap.cardinality.value,
                    "is_multi_output": is_multi,
                    "requirements": list(cap.requirements),
                }
        return {
            "capability_id": None,
            "engine_id": None,
            "fidelity": "medium",
            "warnings": [],
            "limitations": [],
            "cardinality": "one_to_one",
            "is_multi_output": False,
            "requirements": [],
        }

    def create_single_job(
        self,
        input_path: Path,
        output_format_id: str,
        destination_path: Path | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConversionJob:
        """Create and plan a single ConversionJob."""
        input_fmt = self.detect_format(input_path).id
        details = self.get_capability_details(input_fmt, output_format_id)

        if destination_path is None:
            if details["is_multi_output"]:
                destination_path = input_path.parent / f"{input_path.stem}_{output_format_id}_pages"
            else:
                destination_path = input_path.with_suffix(f".{output_format_id}")

        intent = (
            DestinationIntent.DIRECTORY
            if (details["is_multi_output"] or destination_path.is_dir())
            else DestinationIntent.FILE
        )

        req = ConversionRequest.from_single_file(
            input_path=input_path,
            input_format_id=input_fmt,
            output_format_id=output_format_id,
            destination_path=destination_path,
            options=options or {},
            destination_intent=intent,
        )

        plan = self._resolver.create_plan(req)
        return ConversionJob(plan=plan)

    def create_batch(
        self,
        input_paths: list[Path],
        output_format_id: str,
        destination_directory: Path,
        options: dict[str, Any] | None = None,
    ) -> ConversionBatch:
        """Create a planned ConversionBatch for multiple input files."""
        jobs: list[ConversionJob] = []
        for p in input_paths:
            in_fmt = self.detect_format(p).id
            details = self.get_capability_details(in_fmt, output_format_id)

            if details["is_multi_output"]:
                dst = destination_directory / f"{p.stem}_{output_format_id}_pages"
                intent = DestinationIntent.DIRECTORY
            else:
                dst = destination_directory / p.with_suffix(f".{output_format_id}").name
                intent = DestinationIntent.FILE

            req = ConversionRequest.from_single_file(
                input_path=p,
                input_format_id=in_fmt,
                output_format_id=output_format_id,
                destination_path=dst,
                options=options or {},
                destination_intent=intent,
            )
            plan = self._resolver.create_plan(req)
            jobs.append(ConversionJob(plan=plan))

        return ConversionBatch(jobs=tuple(jobs))

    def execute_job(self, job: ConversionJob) -> ConversionResult:
        """Execute a planned ConversionJob using the native runner."""
        return self._runner.execute_job(job)

    def execute_batch(self, batch: ConversionBatch) -> list[ConversionResult]:
        """Execute a ConversionBatch using the native runner."""
        return self._runner.execute_batch(batch)

    def request_cancel_job(self, job: ConversionJob) -> None:
        """Cancel a job, including signalling a currently-running native execution."""
        job.request_cancel()
        self._runner.request_cancel(job.id)

    def request_cancel_batch(self, batch: ConversionBatch) -> None:
        """Cancel every job in a batch, including whichever one is currently executing."""
        for job in batch.jobs:
            self.request_cancel_job(job)

    def format_error_message(self, error: ConversionError | None) -> str:
        """Translate a structured domain ConversionError into a localized,
        helpful user diagnostic.
        """
        if error is None:
            return self._translator.t("error.unknown", details="Unknown error")

        t = self._translator.t

        if error.code == ConversionErrorCode.MISSING_DEPENDENCY:
            return t("error.missing_dep", details=error.message)
        if error.code == ConversionErrorCode.UNSUPPORTED_FORMAT:
            return t("error.unsupported_fmt", details=error.message)
        if error.code == ConversionErrorCode.CANCELLED:
            return t("error.cancelled")
        if error.code == ConversionErrorCode.TIMEOUT:
            return t("error.timeout")
        if error.code == ConversionErrorCode.OUTPUT_FAILURE:
            return t("error.output_fail", details=error.message)
        if error.code == ConversionErrorCode.PIPELINE_FAILURE:
            stage_idx = error.stage_index if error.stage_index is not None else 1
            return t("error.pipeline_fail", stage=stage_idx, details=error.message)

        return t("error.unknown", details=error.message)
