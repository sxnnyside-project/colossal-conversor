import time

from colossal.core.base_converter import BaseConverter
from colossal.models.conversion_task import ConversionTask


class FakeImageConverter(BaseConverter):
    id = "fake-image"
    name = "Fake Image Converter"

    input_formats = ["png"]
    output_formats = ["jpg"]

    def convert(self, task: ConversionTask) -> None:
        for step in range(1, 6):
            time.sleep(0.1)
            task.progress = step / 5
