from __future__ import annotations

from pathlib import Path

import pytest

from colossal.domain.error import ConversionError, ConversionErrorCode
from colossal.domain.request import ConversionRequest
from colossal.domain.resolver import SimplePlanResolver
from colossal.runtime.catalog import FormatCatalog
from colossal.runtime.native_runner import HAS_NATIVE, NativeJobRunner


def test_no_generic_engine_in_catalog() -> None:
    catalog = FormatCatalog.load_default()
    assert len(catalog.capabilities) > 0

    valid_engines = {
        "native_image",
        "native_audio",
        "ffmpeg",
        "soffice",
        "libreoffice",
        "poppler",
        "pdftoppm",
        "magick",
        "imagemagick",
        "pandoc",
    }

    for cap in catalog.capabilities:
        assert cap.engine_id != "generic", (
            f"Capability '{cap.id}' has forbidden 'generic' engine_id"
        )
        assert cap.engine_id in valid_engines, (
            f"Capability '{cap.id}' uses unregistered engine '{cap.engine_id}'"
        )


@pytest.mark.skipif(not HAS_NATIVE, reason="Native C++ extension not available")
def test_all_catalog_capabilities_resolve_to_registered_native_engine() -> None:
    catalog = FormatCatalog.load_default()
    runner = NativeJobRunner()

    for cap in catalog.capabilities:
        msg = f"Engine '{cap.engine_id}' ({cap.id}) not in C++ NativeRuntime"
        assert runner.has_engine(cap.engine_id), msg


def test_unregistered_conversion_raises_capability_not_found(tmp_path: Path) -> None:
    resolver = SimplePlanResolver(capabilities=[])
    req = ConversionRequest.from_single_file(
        input_path=tmp_path / "unknown.xyz",
        input_format_id="xyz",
        output_format_id="abc",
        destination_path=tmp_path / "unknown.abc",
    )

    with pytest.raises(ConversionError) as exc_info:
        resolver.create_plan(req)

    assert exc_info.value.code == ConversionErrorCode.CAPABILITY_NOT_FOUND
