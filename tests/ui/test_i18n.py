from __future__ import annotations

import json
from pathlib import Path

import pytest

from colossal.i18n.locales import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from colossal.i18n.settings import load_user_language, save_user_language
from colossal.i18n.translator import Translator
from colossal.services.conversion_service import ConversionApplicationService


def test_supported_languages_list() -> None:
    assert "en" in SUPPORTED_LANGUAGES
    assert "es" in SUPPORTED_LANGUAGES
    assert "fr" in SUPPORTED_LANGUAGES
    assert "ja" in SUPPORTED_LANGUAGES
    assert "pt" in SUPPORTED_LANGUAGES
    assert "zh" in SUPPORTED_LANGUAGES
    assert len(SUPPORTED_LANGUAGES) >= 6


def test_translations_dictionary_completeness() -> None:
    translations_dir = (
        Path(__file__).resolve().parent.parent.parent / "src" / "colossal" / "i18n" / "translations"
    )
    en_file = translations_dir / "en.json"
    assert en_file.exists()
    en_dict: dict[str, str] = json.loads(en_file.read_text(encoding="utf-8"))
    en_keys = set(en_dict.keys())

    for lang in SUPPORTED_LANGUAGES:
        lang_file = translations_dir / f"{lang}.json"
        assert lang_file.exists(), f"Missing translation file for {lang}"
        lang_dict: dict[str, str] = json.loads(lang_file.read_text(encoding="utf-8"))
        missing_keys = en_keys - set(lang_dict.keys())
        assert not missing_keys, f"Language {lang} is missing keys: {missing_keys}"


def test_translator_basic_and_fallback() -> None:
    translator = Translator(initial_lang="es")
    assert translator.current_language == "es"
    assert translator.t("button.convert") == "Convertir"

    translator.set_language("en")
    assert translator.current_language == "en"
    assert translator.t("button.convert") == "Convert"

    translator.set_language("ja")
    assert translator.t("button.convert") == "変換開始"

    translator.set_language("zh")
    assert translator.t("button.convert") == "开始转换"


def test_translator_pluralization_and_interpolation() -> None:
    translator = Translator(initial_lang="en")
    single = translator.t_plural("status.files_selected_single", "status.files_selected_plural", 1)
    plural = translator.t_plural("status.files_selected_single", "status.files_selected_plural", 5)
    assert single == "1 file selected"
    assert plural == "5 files selected"

    folder_msg = translator.t("status.folder_selected", name="Photos", count=12)
    assert "Photos" in folder_msg
    assert "12" in folder_msg


def test_settings_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import colossal.i18n.settings as s_mod

    cfg_file = tmp_path / "settings.json"
    monkeypatch.setattr(s_mod, "get_config_file_path", lambda: cfg_file)

    assert load_user_language() == DEFAULT_LANGUAGE
    save_user_language("ja")
    assert load_user_language() == "ja"


def test_application_service_localized_error() -> None:
    service = ConversionApplicationService()
    service.set_language("es")
    from colossal.domain.error import ConversionError, ConversionErrorCode

    err = ConversionError(code=ConversionErrorCode.CANCELLED, message="User cancel")
    msg_es = service.format_error_message(err)
    assert "cancelada" in msg_es

    service.set_language("ja")
    msg_ja = service.format_error_message(err)
    assert "キャンセル" in msg_ja


def test_theme_tokens_and_icons() -> None:
    from colossal.ui.theme import (
        NAVY_HEADER_START,
        WIN_GRAY_BG,
        get_icon,
        get_system_font,
    )

    assert WIN_GRAY_BG == "#d4d0c8"
    assert NAVY_HEADER_START == "#000080"

    font = get_system_font(10, bold=True)
    assert font.pointSize() == 10
    assert font.bold() is True

    icon = get_icon("convert")
    assert not icon.isNull()
