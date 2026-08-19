from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FormatCategory(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    SHEET = "sheet"
    SLIDE = "slide"
    IMAGE = "image"
    OTHER = "other"


@dataclass(frozen=True)
class Format:
    id: str
    category: FormatCategory
    label: str
    extensions: tuple[str, ...] = field(default_factory=tuple)
    mime_types: tuple[str, ...] = field(default_factory=tuple)
    lossy: bool = False
    display_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize extensions to ensure leading dot and lower case
        normalized_exts = tuple(
            ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in self.extensions
        )
        object.__setattr__(self, "extensions", normalized_exts)
        object.__setattr__(self, "id", self.id.lower().strip())

    @property
    def primary_extension(self) -> str:
        return self.extensions[0] if self.extensions else f".{self.id}"

    def matches_extension(self, extension_or_path: str | Path) -> bool:
        if isinstance(extension_or_path, Path):
            ext = extension_or_path.suffix.lower()
        else:
            ext = extension_or_path.lower()
            if not ext.startswith("."):
                ext = f".{ext}"
        return ext in self.extensions or ext == f".{self.id}"
