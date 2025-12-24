import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from colossal.ui.main_window import MainWindow
from colossal.core.engine import ConversionEngine
from colossal.core.registry import ConverterRegistry
from colossal.converters.image_converter import PNGConverter
from colossal.core.format_loader import load_format_manifest

def run_app():
    app = QApplication(sys.argv)

    registry = ConverterRegistry()
    registry.register(PNGConverter())

    engine = ConversionEngine(registry)

    manifest_path = Path(__file__).resolve().parent / "resources" / "format_manifest.json"

    manifest = load_format_manifest(manifest_path)

    window = MainWindow(engine, manifest)
    window.show()

    sys.exit(app.exec())
