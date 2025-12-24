from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QComboBox,
    QProgressBar
)
from PySide6.QtCore import QTimer

from colossal.models.conversion_task import ConversionTask
from colossal.models.task_status import TaskStatus


class MainWindow(QMainWindow):
    def __init__(self, engine, manifest):
        super().__init__()

        self.engine = engine
        self.manifest = manifest
        self.task: ConversionTask | None = None
        self.input_path: Path | None = None

        self.setWindowTitle("Colossal Conversor v4.0.0")

        self._build_ui()
        self._populate_formats()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout()

        self.input_label = QLabel("No input file selected")
        self.select_btn = QPushButton("Select File")
        self.format_combo = QComboBox()
        self.convert_btn = QPushButton("Convert")
        self.progress = QProgressBar()

        self.select_btn.clicked.connect(self.select_file)
        self.convert_btn.clicked.connect(self.start_conversion)

        layout.addWidget(self.input_label)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.format_combo)
        layout.addWidget(self.convert_btn)
        layout.addWidget(self.progress)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def _populate_formats(self):
        self.format_combo.clear()

        for category in self.manifest.categories.values():
            for fmt in category.formats.values():
                self.format_combo.addItem(fmt.label, fmt.id)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select file"
        )

        if not file_path:
            return

        self.input_path = Path(file_path)
        self.input_label.setText(self.input_path.name)

    def start_conversion(self):
        if not self.input_path:
            return

        output_format = self.format_combo.currentData()
        input_format = self.input_path.suffix.lstrip(".")

        output_path = self.input_path.with_suffix(
            f".{output_format}"
        )

        self.task = ConversionTask(
            input_path=self.input_path,
            output_path=output_path,
            input_format=input_format,
            output_format=output_format
        )

        self.engine.submit(self.task)
        self._start_polling()

    def _start_polling(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(100)

    def _update_progress(self):
        if not self.task:
            return

        self.progress.setValue(
            int(self.task.progress * 100)
        )

        if self.task.status in (
            TaskStatus.DONE,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED
        ):
            self.timer.stop()
