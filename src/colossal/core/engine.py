from colossal.models.conversion_task import ConversionTask
from colossal.models.conversion_error import ConversionError

from colossal.core.registry import ConverterRegistry
from colossal.core.format_loader import FormatManifest

class ConversionEngine:
    def __init__(
        self,
        registry: ConverterRegistry,
        formats: FormatManifest
    ):
        self._registry = registry
        self._formats = formats

    def submit(self, task: ConversionTask) -> ConversionTask:
        # 1. Validar formatos
        if not self._formats.format_exists(task.input_format):
            task.mark_failed(
                ConversionError(
                    code="UNKNOWN_INPUT_FORMAT",
                    message=f"Unknown input format: {task.input_format}"
                )
            )
            return task

        if not self._formats.format_exists(task.output_format):
            task.mark_failed(
                ConversionError(
                    code="UNKNOWN_OUTPUT_FORMAT",
                    message=f"Unknown output format: {task.output_format}"
                )
            )
            return task

        # 2. Resolver converter
        converter = self._registry.find(
            task.input_format,
            task.output_format
        )

        if not converter:
            task.mark_failed(
                ConversionError(
                    code="UNSUPPORTED_CONVERSION",
                    message=f"No converter for {task.input_format} → {task.output_format}"
                )
            )
            return task

        # 3. Ejecutar
        try:
            task.mark_running()
            converter.convert(task)
            task.mark_done()
        except Exception as exc:
            task.mark_failed(
                ConversionError(
                    code="CONVERSION_FAILED",
                    message="Conversion failed",
                    details=str(exc)
                )
            )

        return task
