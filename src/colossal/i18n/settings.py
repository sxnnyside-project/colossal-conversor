from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from colossal.i18n.locales import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


def get_config_file_path() -> Path:
    config_dir = Path.home() / ".config" / "colossal"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_user_language() -> str:
    config_file = get_config_file_path()
    if config_file.exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            data: dict[str, Any] = json.loads(config_file.read_text(encoding="utf-8"))
            lang = data.get("language")
            if isinstance(lang, str) and lang in SUPPORTED_LANGUAGES:
                return lang
    return DEFAULT_LANGUAGE


def save_user_language(lang: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        return
    config_file = get_config_file_path()
    data: dict[str, Any] = {}
    if config_file.exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            data = json.loads(config_file.read_text(encoding="utf-8"))
    data["language"] = lang
    with contextlib.suppress(OSError):
        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
