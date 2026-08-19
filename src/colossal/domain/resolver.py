from __future__ import annotations

from colossal.domain.capability import Capability
from colossal.domain.error import ConversionError, ErrorCode
from colossal.domain.pipeline import ConversionPipeline, PipelineStage
from colossal.domain.plan import ConversionPlan
from colossal.domain.request import ConversionRequest


class SimplePlanResolver:
    """Resolves a ConversionRequest into a ConversionPlan."""

    def __init__(self, capabilities: list[Capability] | None = None) -> None:
        if capabilities is None:
            try:
                from colossal.runtime.catalog import FormatCatalog

                self._capabilities: list[Capability] = FormatCatalog.load_default().capabilities
            except Exception:
                self._capabilities = []
        else:
            self._capabilities = list(capabilities)

    def register_capability(self, capability: Capability) -> None:
        self._capabilities.append(capability)

    def find_capability(self, input_format_id: str, output_format_id: str) -> Capability | None:
        inp = input_format_id.lower().lstrip(".").strip()
        if inp == "jpg":
            inp = "jpeg"
        out = output_format_id.lower().lstrip(".").strip()
        if out == "jpg":
            out = "jpeg"

        for cap in self._capabilities:
            if cap.supports(inp, out):
                return cap
        return None

    def create_plan(self, request: ConversionRequest) -> ConversionPlan:
        primary_input = request.primary_input
        inp_fmt = primary_input.format_id
        out_fmt = request.output_format_id

        capability = self.find_capability(inp_fmt, out_fmt)
        if capability is None:
            raise ConversionError(
                code=ErrorCode.CAPABILITY_NOT_FOUND,
                message=f"No conversion capability registered from '{inp_fmt}' to '{out_fmt}'",
            )

        stage = PipelineStage(
            stage_index=0,
            name=f"stage_0_{inp_fmt}_to_{out_fmt}",
            capability=capability,
            input_format_id=inp_fmt,
            output_format_id=out_fmt,
            options=dict(request.options),
        )
        pipeline = ConversionPipeline(stages=(stage,))

        return ConversionPlan(
            request=request,
            pipeline=pipeline,
            cardinality=capability.cardinality,
        )
