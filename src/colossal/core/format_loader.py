import json
from pathlib import Path
from typing import Dict

from colossal.models.format_manifest import FormatCategory, FormatInfo

class FormatManifest:
    def __init__(self, categories: Dict[str, FormatCategory]):
        self.categories = categories

    def get_format(self, format_id: str) -> FormatInfo | None:
        return next(
            (
                category.formats[format_id]
                for category in self.categories.values()
                if format_id in category.formats
            ),
            None,
        )

    def format_exists(self, format_id: str) -> bool:
        return self.get_format(format_id) is not None

    def category_of(self, format_id: str) -> str | None:
        return next(
            (
                cat_id
                for cat_id, category in self.categories.items()
                if format_id in category.formats
            ),
            None,
        )


def load_format_manifest(path: Path) -> FormatManifest:
    data = json.loads(path.read_text(encoding="utf-8"))

    categories: Dict[str, FormatCategory] = {}

    for cat_id, cat_data in data["categories"].items():
        formats: Dict[str, FormatInfo] = {
            fmt_id: FormatInfo(
                id=fmt_id,
                label=fmt_data["label"],
                extensions=fmt_data["extensions"],
                mime=fmt_data["mime"],
                lossy=fmt_data["lossy"],
            )
            for fmt_id, fmt_data in cat_data["formats"].items()
        }
        categories[cat_id] = FormatCategory(
            id=cat_id,
            label=cat_data["label"],
            formats=formats
        )

    return FormatManifest(categories)
