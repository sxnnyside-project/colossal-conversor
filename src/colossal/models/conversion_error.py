from dataclasses import dataclass
from typing import Optional


@dataclass
class ConversionError:
    code: str
    message: str
    details: Optional[str] = None
    fatal: bool = True
