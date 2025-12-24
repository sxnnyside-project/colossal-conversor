from typing import List, Optional

from colossal.core.base_converter import BaseConverter

class ConverterRegistry:
    def __init__(self):
        self._converters: List[BaseConverter] = []

    def register(self, converter: BaseConverter) -> None:
        self._converters.append(converter)

    def find(
        self,
        input_format: str,
        output_format: str
    ) -> Optional[BaseConverter]:
        for converter in self._converters:
            if converter.supports(input_format, output_format):
                return converter
        return None
