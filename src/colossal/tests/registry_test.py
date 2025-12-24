from pathlib import Path

from colossal.models.conversion_task import ConversionTask
from colossal.core.engine import ConversionEngine
from colossal.core.registry import ConverterRegistry
from colossal.converters.image_converter import ImageConverter

registry = ConverterRegistry()
registry.register(ImageConverter())

engine = ConversionEngine(registry)

task = ConversionTask(
    input_path=Path("input.png"),
    output_path=Path("output.jpg"),
    input_format="png",
    output_format="jpg",
    options={"quality": 85}
)

engine.submit(task)

print(task.status)
print(task.progress)
