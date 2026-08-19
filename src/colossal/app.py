from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from colossal.services.conversion_service import ConversionApplicationService
from colossal.ui.main_window import MainWindow


def run_app() -> None:
    app = QApplication(sys.argv)

    service = ConversionApplicationService()
    window = MainWindow(service=service)
    window.show()

    sys.exit(app.exec())
