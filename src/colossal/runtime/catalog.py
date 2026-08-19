from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from colossal.domain.capability import Capability
from colossal.domain.cardinality import ConversionCardinality
from colossal.domain.format import Format, FormatCategory


class FormatCatalog:
    """Authoritative format and conversion capability registry for Colossal Conversor.
    Loads and normalizes format metadata and conversion rules into pure domain objects.
    """

    def __init__(self) -> None:
        self._formats: dict[str, Format] = {}
        self._capabilities: list[Capability] = []
        self._format_categories: dict[str, FormatCategory] = {}
        self._category_labels: dict[str, str] = {}
        self._category_formats: dict[str, list[str]] = {}

    @classmethod
    def load_default(cls) -> FormatCatalog:
        resources_dir = Path(__file__).resolve().parent.parent / "resources"
        manifest_path = resources_dir / "format_manifest.json"
        formats_dir = resources_dir / "formats"
        catalog = cls()
        catalog.load_from_paths(manifest_path, formats_dir)
        return catalog

    def load_from_paths(self, manifest_path: Path, formats_dir: Path | None = None) -> None:
        self._load_manifest(manifest_path)
        if formats_dir and formats_dir.exists():
            self._load_formats_dir(formats_dir)

    def _load_manifest(self, manifest_path: Path) -> None:
        if not manifest_path.exists():
            return
        data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        categories: dict[str, Any] = data.get("categories", {})

        for cat_key, cat_data in categories.items():
            try:
                category_enum = FormatCategory(cat_key.lower())
            except ValueError:
                category_enum = FormatCategory.OTHER

            self._category_labels[cat_key] = cat_data.get("label", cat_key.capitalize())
            cat_formats = self._category_formats.setdefault(cat_key, [])

            for fmt_id, fmt_info in cat_data.get("formats", {}).items():
                norm_id = self.normalize_format_id(fmt_id)
                exts = tuple(fmt_info.get("extensions", [f".{norm_id}"]))
                mime = fmt_info.get("mime")
                mimes = (mime,) if mime else ()
                lossy = bool(fmt_info.get("lossy", False))
                label = fmt_info.get("label", norm_id.upper())

                fmt = Format(
                    id=norm_id,
                    category=category_enum,
                    label=label,
                    extensions=exts,
                    mime_types=mimes,
                    lossy=lossy,
                    display_metadata=fmt_info,
                )
                self._formats[norm_id] = fmt
                self._format_categories[norm_id] = category_enum
                if norm_id not in cat_formats:
                    cat_formats.append(norm_id)

    CANONICAL_ENGINE_MAP: dict[str, str] = {
        "office": "soffice",
        "soffice": "soffice",
        "libreoffice": "soffice",
        "markdown": "pandoc",
        "pandoc": "pandoc",
        "pdf": "soffice",
        "pdf_toolchain": "poppler",
        "poppler": "poppler",
        "pdftoppm": "poppler",
        "default": "magick",
        "magick": "magick",
        "imagemagick": "magick",
        "native_image": "native_image",
        "native_audio": "native_audio",
        "transcoder": "ffmpeg",
        "ffmpeg": "ffmpeg",
        "tabular": "soffice",
        "pdf_table": "soffice",
        "svg": "magick",
        "gif": "magick",
        "heic": "magick",
    }

    def _load_formats_dir(self, formats_dir: Path) -> None:
        for json_file in sorted(formats_dir.glob("*.json")):
            try:
                data: dict[str, Any] = json.loads(json_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            category_name = data.get("category", json_file.stem)
            category_formats = [self.normalize_format_id(f) for f in data.get("formats", [])]
            engines_map: dict[str, str] = data.get("engines", {})
            file_default = data.get("engine") or engines_map.get("default") or "native_image"
            conversions = data.get("conversions", [])

            for conv in conversions:
                from_spec = conv.get("from")
                to_spec = conv.get("to")

                if from_spec in ("*", ["*"]):
                    input_fmts = list(category_formats)
                elif isinstance(from_spec, list):
                    input_fmts = [self.normalize_format_id(f) for f in from_spec]
                elif isinstance(from_spec, str):
                    input_fmts = [self.normalize_format_id(from_spec)]
                else:
                    input_fmts = []

                if isinstance(to_spec, list):
                    output_fmts = [self.normalize_format_id(t) for t in to_spec]
                elif isinstance(to_spec, str):
                    output_fmts = [self.normalize_format_id(to_spec)]
                else:
                    output_fmts = []

                # Resolve engine to canonical ID
                conv_engine_key = conv.get("engine")
                if conv_engine_key and conv_engine_key in engines_map:
                    raw_engine = engines_map[conv_engine_key]
                elif conv_engine_key:
                    raw_engine = conv_engine_key
                else:
                    raw_engine = file_default

                engine_id = self.CANONICAL_ENGINE_MAP.get(
                    raw_engine.lower().strip(), raw_engine.lower().strip()
                )

                # Determine requirements
                requirements: list[str] = []
                if engine_id in ("ffmpeg", "soffice", "pdftoppm", "poppler", "magick", "pandoc"):
                    requirements.append(engine_id)

                cardinality = ConversionCardinality.ONE_TO_ONE
                out_spec = conv.get("output", {})
                if out_spec.get("type") in ("multi_file", "multi_page"):
                    cardinality = ConversionCardinality.ONE_TO_MANY

                cap = Capability(
                    id=conv.get("name") or f"{engine_id}_{category_name}_{to_spec}",
                    name=conv.get("name")
                    or f"{engine_id.capitalize()} {category_name.capitalize()} Converter",
                    input_formats=frozenset(input_fmts),
                    output_formats=frozenset(output_fmts),
                    engine_id=engine_id,
                    cardinality=cardinality,
                    fidelity=conv.get("fidelity") or "medium",
                    warnings=tuple(conv.get("warnings") or []),
                    limitations=tuple(conv.get("limitations") or []),
                    requirements=tuple(requirements),
                    options_schema=conv.get("options_schema") or {},
                    default_preset=conv.get("default_preset"),
                )
                self._capabilities.append(cap)

    @staticmethod
    def normalize_format_id(fmt_id: str) -> str:
        clean = fmt_id.lower().lstrip(".").strip()
        if clean == "jpg":
            return "jpeg"
        return clean

    def get_format(self, format_id: str) -> Format | None:
        norm = self.normalize_format_id(format_id)
        return self._formats.get(norm)

    def get_format_by_extension(self, ext_or_path: str | Path) -> Format | None:
        if isinstance(ext_or_path, Path):
            ext = ext_or_path.suffix.lower()
        else:
            ext = ext_or_path.lower()
            if not ext.startswith("."):
                ext = f".{ext}"

        for fmt in self._formats.values():
            if fmt.matches_extension(ext):
                return fmt
        return None

    def find_capability(self, input_format_id: str, output_format_id: str) -> Capability | None:
        inp = self.normalize_format_id(input_format_id)
        out = self.normalize_format_id(output_format_id)
        for cap in self._capabilities:
            if cap.supports(inp, out):
                return cap
        return None

    def get_available_output_formats(self, input_format_id: str) -> set[str]:
        inp = self.normalize_format_id(input_format_id)
        outputs: set[str] = set()
        for cap in self._capabilities:
            if inp in cap.input_formats:
                outputs.update(cap.output_formats)
        return outputs

    @property
    def formats(self) -> dict[str, Format]:
        return dict(self._formats)

    @property
    def capabilities(self) -> list[Capability]:
        return list(self._capabilities)

    @property
    def category_labels(self) -> dict[str, str]:
        return dict(self._category_labels)

    @property
    def category_formats(self) -> dict[str, list[str]]:
        return dict(self._category_formats)

    def category_of(self, format_id: str) -> str | None:
        norm = self.normalize_format_id(format_id)
        fmt = self._formats.get(norm)
        return fmt.category.value if fmt else None
