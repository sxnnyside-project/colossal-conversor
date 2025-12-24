from abc import ABC, abstractmethod
from typing import Iterable, Optional, Dict, Any

from colossal.models.conversion_task import ConversionTask


class BaseConverter(ABC):
    id: str
    name: str

    input_formats: Iterable[str]
    output_formats: Iterable[str]

    options_schema: Optional[Dict[str, Any]] = None

    def supports(self, input_fmt: str, output_fmt: str) -> bool:
        return (
            input_fmt in self.input_formats
            and output_fmt in self.output_formats
        )

    @abstractmethod
    def convert(self, task: ConversionTask) -> None:
        """
        Executes the conversion.
        Must update task.progress manually.
        Raises exceptions on failure.
        """
        raise NotImplementedError
