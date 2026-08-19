from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from colossal.i18n.locales import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from colossal.i18n.settings import load_user_language, save_user_language


class Translator:
    """Provides thread-safe, dictionary-based internationalization for Colossal Conversor."""

    def __init__(self, initial_lang: str | None = None) -> None:
        self._current_lang = initial_lang or load_user_language()
        if self._current_lang not in SUPPORTED_LANGUAGES:
            self._current_lang = DEFAULT_LANGUAGE

        self._translations: dict[str, dict[str, str]] = {}
        self._load_all_translations()

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang: str) -> None:
        if lang in SUPPORTED_LANGUAGES:
            self._current_lang = lang
            save_user_language(lang)

    def _load_all_translations(self) -> None:
        translations_dir = Path(__file__).resolve().parent / "translations"
        for code in SUPPORTED_LANGUAGES:
            file_path = translations_dir / f"{code}.json"
            if file_path.exists():
                try:
                    data: dict[str, str] = json.loads(file_path.read_text(encoding="utf-8"))
                    self._translations[code] = data
                except (OSError, json.JSONDecodeError):
                    self._translations[code] = {}
            else:
                self._translations[code] = {}

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate a key for the active language with English fallback."""
        dict_active = self._translations.get(self._current_lang, {})
        text = dict_active.get(key)
        if text is None:
            # Fallback to English
            dict_en = self._translations.get(DEFAULT_LANGUAGE, {})
            text = dict_en.get(key, key)

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    def t_plural(self, key_single: str, key_plural: str, count: int, **kwargs: Any) -> str:
        """Translate a singular/plural message based on count."""
        key = key_single if count == 1 else key_plural
        return self.t(key, count=count, **kwargs)
