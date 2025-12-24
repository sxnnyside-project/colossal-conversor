from pathlib import Path

from colossal.core.engine import ConversionEngine
from colossal.core.registry import ConverterRegistry
from colossal.tests.fake_image import FakeImageConverter
from colossal.models.conversion_task import ConversionTask


registry = ConverterRegistry()
registry.register(FakeImageConverter())

engine = ConversionEngine(registry)

task = ConversionTask(
    input_path=Path("input.png"),
    output_path=Path("output.jpg"),
    input_format="png",
    output_format="jpg"
)

engine.submit(task)

print(task.status, task.progress)
