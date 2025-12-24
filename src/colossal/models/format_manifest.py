from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FormatInfo:
    id: str
    label: str
    extensions: List[str]
    mime: str
    lossy: bool


@dataclass
class FormatCategory:
    id: str
    label: str
    formats: Dict[str, FormatInfo]