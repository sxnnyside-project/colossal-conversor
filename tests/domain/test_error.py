from __future__ import annotations

from colossal.domain.error import ConversionError, ConversionErrorCode


def test_conversion_error_formatting() -> None:
    err = ConversionError(
        code=ConversionErrorCode.UNSUPPORTED_FORMAT,
        message="Format xyz is not supported",
        details="No registered engine handles this format",
        stage_index=1,
    )
    assert err.code == ConversionErrorCode.UNSUPPORTED_FORMAT
    assert err.stage_index == 1
    expected = (
        "[UNSUPPORTED_FORMAT] Format xyz is not supported (stage 1): "
        "No registered engine handles this format"
    )
    assert str(err) == expected
