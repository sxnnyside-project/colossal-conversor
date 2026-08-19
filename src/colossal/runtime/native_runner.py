from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from colossal.domain.artifact import ArtifactRole, ConversionArtifact
from colossal.domain.batch import ConversionBatch
from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.result import ConversionResult

try:
    from colossal import colossal_native

    HAS_NATIVE = colossal_native is not None
except (ImportError, AttributeError):
    colossal_native = None  # type: ignore[assignment]
    HAS_NATIVE = False


def _to_native_artifact_role(role: ArtifactRole) -> Any:
    if not HAS_NATIVE:
        return None
    mapping = {
        ArtifactRole.INPUT: colossal_native.ArtifactRole.Input,
        ArtifactRole.INTERMEDIATE: colossal_native.ArtifactRole.Intermediate,
        ArtifactRole.OUTPUT: colossal_native.ArtifactRole.Output,
        ArtifactRole.AUXILIARY: colossal_native.ArtifactRole.Auxiliary,
    }
    return mapping.get(role, colossal_native.ArtifactRole.Output)


def _to_domain_artifact_role(role: Any) -> ArtifactRole:
    if not HAS_NATIVE:
        return ArtifactRole.OUTPUT
    if role == colossal_native.ArtifactRole.Input:
        return ArtifactRole.INPUT
    if role == colossal_native.ArtifactRole.Intermediate:
        return ArtifactRole.INTERMEDIATE
    if role == colossal_native.ArtifactRole.Auxiliary:
        return ArtifactRole.AUXILIARY
    return ArtifactRole.OUTPUT


def _to_domain_job_status(status: Any) -> JobStatus:
    if not HAS_NATIVE:
        return JobStatus.PENDING
    mapping = {
        colossal_native.JobStatus.Pending: JobStatus.PENDING,
        colossal_native.JobStatus.Running: JobStatus.RUNNING,
        colossal_native.JobStatus.Cancelling: JobStatus.CANCELLING,
        colossal_native.JobStatus.Cancelled: JobStatus.CANCELLED,
        colossal_native.JobStatus.Completed: JobStatus.COMPLETED,
        colossal_native.JobStatus.Failed: JobStatus.FAILED,
        colossal_native.JobStatus.Partial: JobStatus.PARTIAL,
    }
    return mapping.get(status, JobStatus.FAILED)


def _to_domain_error_code(code: Any) -> ConversionErrorCode:
    if not HAS_NATIVE:
        return ConversionErrorCode.UNKNOWN
    mapping = {
        colossal_native.ErrorCode.InvalidRequest: ConversionErrorCode.INVALID_REQUEST,
        colossal_native.ErrorCode.UnsupportedFormat: ConversionErrorCode.UNSUPPORTED_FORMAT,
        colossal_native.ErrorCode.CapabilityNotFound: ConversionErrorCode.CAPABILITY_NOT_FOUND,
        colossal_native.ErrorCode.MissingDependency: ConversionErrorCode.MISSING_DEPENDENCY,
        colossal_native.ErrorCode.ExecutionFailed: ConversionErrorCode.EXECUTION_FAILED,
        colossal_native.ErrorCode.Cancelled: ConversionErrorCode.CANCELLED,
        colossal_native.ErrorCode.OutputFailure: ConversionErrorCode.OUTPUT_FAILURE,
        colossal_native.ErrorCode.PipelineFailure: ConversionErrorCode.PIPELINE_FAILURE,
        colossal_native.ErrorCode.Timeout: ConversionErrorCode.TIMEOUT,
        colossal_native.ErrorCode.Unknown: ConversionErrorCode.UNKNOWN,
    }
    return mapping.get(code, ConversionErrorCode.UNKNOWN)


class NativeJobRunner:
    """High-performance runtime service executing ConversionJobs and ConversionBatches
    through the C++20 Colossal Native Core.
    """

    def __init__(self, thread_count: int = 4, temp_dir: Path | str | None = None) -> None:
        if not HAS_NATIVE:
            raise RuntimeError("colossal_native C++ extension module is not available")
        self._temp_dir = Path(temp_dir) if temp_dir else Path()
        self._native_runtime = colossal_native.NativeRuntime(thread_count, self._temp_dir)
        self._active_jobs: dict[str, Any] = {}
        self._active_jobs_lock = threading.Lock()

    def has_engine(self, engine_id: str) -> bool:
        """Check if an engine ID is registered in the C++ NativeRuntime."""
        if not HAS_NATIVE or not hasattr(self._native_runtime, "has_engine"):
            return False
        return bool(self._native_runtime.has_engine(engine_id))

    def execute_job(self, job: ConversionJob) -> ConversionResult:
        """Execute a Python domain ConversionJob on the C++ native core."""
        if job.status == JobStatus.CANCELLED:
            return ConversionResult.from_job(job)
        if job.status == JobStatus.PENDING:
            job.start()

        plan = job.plan
        request = plan.request
        pipeline = plan.pipeline

        # Build native request
        native_req = colossal_native.Request()
        native_req.id = request.id
        native_req.output_format_id = request.output_format_id
        native_req.destination_path = request.destination_path
        native_req.options = {str(k): str(v) for k, v in request.options.items()}

        native_in_artifacts = []
        for art in request.input_artifacts:
            n_art = colossal_native.Artifact(
                art.path,
                art.format_id,
                _to_native_artifact_role(art.role),
                art.size_bytes,
            )
            native_in_artifacts.append(n_art)
        native_req.input_artifacts = native_in_artifacts

        # Build native pipeline
        native_pipeline = colossal_native.Pipeline()
        native_stages = []
        for stage in pipeline.stages:
            n_stage = colossal_native.PipelineStage()
            n_stage.stage_index = stage.stage_index
            n_stage.name = stage.name
            n_stage.input_format_id = stage.input_format_id
            n_stage.output_format_id = stage.output_format_id
            n_stage.options = {str(k): str(v) for k, v in stage.options.items()}

            n_cap = colossal_native.Capability()
            n_cap.id = stage.capability.id
            n_cap.name = stage.capability.name
            n_cap.engine_id = stage.capability.engine_id
            n_cap.input_formats = set(stage.capability.input_formats)
            n_cap.output_formats = set(stage.capability.output_formats)
            n_cap.requirements = list(stage.capability.requirements)
            n_cap.fidelity = stage.capability.fidelity

            n_stage.capability = n_cap
            native_stages.append(n_stage)

        native_pipeline.stages = native_stages

        # Instantiate native Job
        native_job = colossal_native.Job(job.id, native_req, native_pipeline)

        # Wire cancellation
        if job.status == JobStatus.CANCELLING:
            native_job.request_cancel()

        # Register the native job so request_cancel() can reach it from
        # another thread while execute_job() below is blocking.
        with self._active_jobs_lock:
            self._active_jobs[job.id] = native_job
        try:
            # Execute on C++ native core (GIL is automatically released during execution)
            native_res = self._native_runtime.execute_job(native_job)
        finally:
            with self._active_jobs_lock:
                self._active_jobs.pop(job.id, None)

        # Synchronize status back to Python job
        domain_status = _to_domain_job_status(native_res.status)
        produced: list[ConversionArtifact] = []
        for n_out in native_res.output_artifacts:
            produced.append(
                ConversionArtifact(
                    path=n_out.path,
                    format_id=n_out.format_id,
                    role=_to_domain_artifact_role(n_out.role),
                    size_bytes=n_out.size_bytes,
                )
            )

        for n_inter in native_job.intermediate_artifacts:
            job.add_intermediate_artifact(
                ConversionArtifact(
                    path=n_inter.path,
                    format_id=n_inter.format_id,
                    role=_to_domain_artifact_role(n_inter.role),
                    size_bytes=n_inter.size_bytes,
                )
            )

        if domain_status == JobStatus.COMPLETED:
            if not job.status.is_terminal:
                job.complete(produced)
        elif domain_status == JobStatus.CANCELLED:
            job.mark_cancelled()
        elif domain_status == JobStatus.FAILED:
            err_code = (
                _to_domain_error_code(native_res.error.code)
                if native_res.error
                else ConversionErrorCode.EXECUTION_FAILED
            )
            err_msg = native_res.error.message if native_res.error else "Native conversion failed"
            err_details = native_res.error.details if native_res.error else None
            stage_idx = native_res.error.stage_index if native_res.error else None
            domain_err = ConversionError(
                code=err_code,
                message=err_msg,
                details=err_details,
                stage_index=stage_idx,
            )
            if not job.status.is_terminal:
                job.fail(domain_err)

        return ConversionResult.from_job(job)

    def request_cancel(self, job_id: str) -> bool:
        """Signal the in-flight native Job for job_id to stop. Returns False
        if no native execution for that job is currently running.
        """
        with self._active_jobs_lock:
            native_job = self._active_jobs.get(job_id)
        if native_job is None:
            return False
        native_job.request_cancel()
        return True

    def execute_batch(self, batch: ConversionBatch) -> list[ConversionResult]:
        """Execute a batch of ConversionJobs sequentially on the native core."""
        results: list[ConversionResult] = []
        for job in batch.jobs:
            if batch.status == JobStatus.CANCELLED or job.status == JobStatus.CANCELLED:
                results.append(ConversionResult.from_job(job))
                continue
            res = self.execute_job(job)
            results.append(res)
        return results

    def shutdown(self) -> None:
        if HAS_NATIVE and self._native_runtime:
            self._native_runtime.shutdown()
