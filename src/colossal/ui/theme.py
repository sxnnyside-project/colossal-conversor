from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QIcon, QPixmap

# --- Semantic Color Tokens (Windows 95 Classic Blue Hierarchy) ---
WIN_GRAY_BG = "#d4d0c8"
WIN_LIGHT_BORDER = "#ffffff"
WIN_DARK_BORDER = "#808080"
WIN_BLACK_BORDER = "#000000"
WIN_SUNKEN_BG = "#ffffff"

NAVY_HEADER_START = "#000080"
NAVY_HEADER_END = "#1084d0"
ACCENT_BLUE_BTN = "#004080"
ACCENT_BLUE_HOVER = "#1066cc"

TEXT_PRIMARY = "#000000"
TEXT_HEADER = "#ffffff"
TEXT_MUTED = "#444444"
TEXT_DISABLED = "#888888"

STATUS_SUCCESS_BG = "#e8f5e9"
STATUS_SUCCESS_FG = "#006600"
STATUS_SUCCESS_BORDER = "#4caf50"

STATUS_WARN_BG = "#fffde7"
STATUS_WARN_FG = "#804000"
STATUS_WARN_BORDER = "#ffb300"

STATUS_ERROR_BG = "#ffebee"
STATUS_ERROR_FG = "#990000"
STATUS_ERROR_BORDER = "#e53935"

STATUS_INFO_BG = "#e3f2fd"
STATUS_INFO_FG = "#004080"
STATUS_INFO_BORDER = "#2196f3"


def get_icons_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "icons"


def get_icon(name: str) -> QIcon:
    """Retrieve a bundled SVG or PNG icon by name."""
    icons_dir = get_icons_dir()
    svg_path = icons_dir / f"{name}.svg"
    if svg_path.exists():
        return QIcon(str(svg_path))
    png_path = icons_dir / f"{name}.png"
    if png_path.exists():
        return QIcon(str(png_path))
    return QIcon()


def get_pixmap(name: str, width: int = 24, height: int = 24) -> QPixmap:
    """Retrieve a pixmap scaled to dimensions."""
    icon = get_icon(name)
    if not icon.isNull():
        return icon.pixmap(width, height)
    return QPixmap()


def get_system_font(size: int = 9, bold: bool = False) -> QFont:
    """Return a clean system desktop font compatible with Latin and CJK character sets."""
    font = QFont("Segoe UI", size)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setBold(bold)
    return font
