from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from colossal.ui.main_window import MainWindow
from colossal.ui.theme import get_pixmap


def test_app_icon_loads_correctly(qapp: QApplication) -> None:
    pix = get_pixmap("app_icon", 24, 24)
    assert not pix.isNull(), "app_icon.svg failed to load as a valid QPixmap"
    assert pix.width() == 24
    assert pix.height() == 24


def test_main_window_has_no_redundant_output_combo(qapp: QApplication) -> None:
    window = MainWindow()
    assert not hasattr(window, "output_combo")
    assert hasattr(window, "_format_buttons")
    assert hasattr(window, "selected_output_format")


def test_format_button_selection_updates_state(qapp: QApplication, tmp_path: Path) -> None:
    window = MainWindow()
    dummy_wav = tmp_path / "sample.wav"
    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    dummy_wav.write_bytes(wav_header)

    window._handle_files_selected([dummy_wav])
    assert window.input_format_label.text() == "wav"

    # Click an output format button (e.g. mp3)
    assert "mp3" in window._format_buttons
    window._on_format_button_clicked("mp3")

    assert window.selected_output_format == "mp3"
    assert window.output_path == dummy_wav.with_suffix(".mp3")
    assert window.convert_btn.isEnabled()
