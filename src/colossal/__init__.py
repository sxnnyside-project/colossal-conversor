from __future__ import annotations

try:
    from colossal import colossal_native
except ImportError:
    colossal_native = None  # type: ignore[assignment]

__all__ = ["colossal_native"]
