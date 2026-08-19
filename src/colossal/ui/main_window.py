from __future__ import annotations

import contextlib
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import (
    QDesktopServices,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QKeySequence,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from colossal.domain.batch import ConversionBatch
from colossal.domain.job import ConversionJob, JobStatus
from colossal.domain.result import ConversionResult
from colossal.i18n.locales import SUPPORTED_LANGUAGES
from colossal.runtime.catalog import FormatCatalog
from colossal.runtime.native_runner import NativeJobRunner
from colossal.services.conversion_service import ConversionApplicationService
from colossal.ui.theme import get_icon, get_pixmap, get_system_font


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: ConversionApplicationService | None = None,
        catalog: FormatCatalog | None = None,
        runner: NativeJobRunner | None = None,
    ) -> None:
        super().__init__()

        self.service = service or ConversionApplicationService(catalog=catalog, runner=runner)
        self.catalog = self.service.catalog
        self.translator = self.service.translator

        self.current_job: ConversionJob | None = None
        self.current_batch: ConversionBatch | None = None
        self.last_results: list[ConversionResult] = []

        self.input_path: Path | None = None
        self.input_paths: list[Path] | None = None
        self.selected_folder_name: str | None = None
        self.output_path: Path | None = None
        self.selected_output_format: str | None = None
        self._detected_formats: list[str] = []

        self.setWindowTitle(f"{self.translator.t('app.title')} {self.translator.t('app.version')}")
        self.setFont(get_system_font(9))

        # Enable native Drag and Drop
        self.setAcceptDrops(True)

        # Load theme qss if available
        qss_path = Path(__file__).resolve().parent.parent / "resources" / "theme.qss"
        arrow_svg = (
            Path(__file__).resolve().parent.parent / "resources" / "icons" / "arrow_down.svg"
        )
        with contextlib.suppress(OSError, FileNotFoundError, UnicodeDecodeError):
            if qss_path.exists():
                qss_content = qss_path.read_text(encoding="utf-8")
                qss_content = qss_content.replace("__ARROW_DOWN_PATH__", arrow_svg.as_posix())
                self.setStyleSheet(qss_content)

        self._build_ui()
        self._setup_shortcuts()
        self._populate_formats()
        self.retranslate_ui()

    # --- Keyboard Shortcuts ------------------------------------------------------
    def _setup_shortcuts(self) -> None:
        # Ctrl+O / Cmd+O to open file
        shortcut_open = QShortcut(QKeySequence.StandardKey.Open, self)
        shortcut_open.activated.connect(self.select_file)

        # Escape to cancel
        shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        shortcut_esc.activated.connect(self._handle_escape)

    def _handle_escape(self) -> None:
        if self.cancel_btn.isEnabled():
            self.cancel_conversion()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.convert_btn.isEnabled():
            self.start_conversion()
            return
        super().keyPressEvent(event)

    # --- Drag & Drop -------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return

        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if not paths:
            return

        # Check if a single folder was dropped
        if len(paths) == 1 and paths[0].is_dir():
            self._handle_folder_selected(paths[0])
        else:
            # Flatten any directories dropped among files
            collected_files: list[Path] = []
            for p in paths:
                if p.is_file():
                    collected_files.append(p)
                elif p.is_dir():
                    collected_files.extend([f for f in p.rglob("*") if f.is_file()])
            if collected_files:
                self._handle_files_selected(collected_files)

        event.acceptProposedAction()

    # --- UI building -------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setMinimumSize(960, 620)

        central = QWidget()
        central.setObjectName("card")
        main_v = QVBoxLayout()
        main_v.setContentsMargins(10, 10, 10, 10)
        main_v.setSpacing(10)

        # Topbar Banner with Windows 95 Classic Blue Header
        header_widget = QWidget()
        header_widget.setObjectName("headerBar")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)

        app_icon_label = QLabel()
        app_icon_label.setObjectName("appIcon")
        app_icon_label.setFixedSize(28, 28)
        pix = get_pixmap("app_icon", 24, 24)
        if not pix.isNull():
            app_icon_label.setPixmap(pix)

        self.title_label = QLabel("Colossal Conversor")
        self.title_label.setObjectName("title")

        self.version_label = QLabel("v4.0.0")
        self.version_label.setObjectName("versionBadge")

        header_layout.addWidget(app_icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.version_label)
        header_layout.addStretch()

        self.lang_label = QLabel("Language:")
        self.lang_label.setObjectName("langLabel")
        self.lang_combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES.items():
            self.lang_combo.addItem(f"{name} ({code})", code)

        idx = self.lang_combo.findData(self.translator.current_language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)

        header_layout.addWidget(self.lang_label)
        header_layout.addWidget(self.lang_combo)
        main_v.addWidget(header_widget)

        # Main content: left = formats grid, right = file card
        content_h = QHBoxLayout()
        content_h.setSpacing(10)

        # Left panel: formats grid inside a scrollable area
        left_card = QWidget()
        left_card.setObjectName("card")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        self.options_header_label = QLabel("Conversion Options")
        self.options_header_label.setFont(get_system_font(10, bold=True))
        left_layout.addWidget(self.options_header_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_container = QWidget()
        self._formats_grid = grid_container
        grid = QGridLayout(grid_container)
        grid.setSpacing(6)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        grid_container.setLayout(grid)

        scroll.setWidget(grid_container)
        left_layout.addWidget(scroll)

        # Bottom controls in left panel
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.setObjectName("saveBtn")
        self.save_as_btn.setIcon(get_icon("save"))
        self.save_as_btn.clicked.connect(self.choose_output_path)
        self.save_as_btn.setEnabled(False)

        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setObjectName("convertBtn")
        self.convert_btn.setIcon(get_icon("convert"))
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setIcon(get_icon("cancel"))
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setEnabled(False)

        bottom_row.addWidget(self.save_as_btn)
        bottom_row.addWidget(self.convert_btn)
        bottom_row.addWidget(self.cancel_btn)
        left_layout.addLayout(bottom_row)

        left_card.setLayout(left_layout)
        left_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Right panel: intake buttons, drop zone, badges, hints, and artifact actions
        right_card = QWidget()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        # Intake Buttons Row
        intake_row = QHBoxLayout()
        self.select_files_btn = QPushButton("Select File(s)")
        self.select_files_btn.setIcon(get_icon("file_add"))
        self.select_files_btn.clicked.connect(self.select_file)

        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.setIcon(get_icon("folder_add"))
        self.select_folder_btn.clicked.connect(self.select_folder)

        intake_row.addWidget(self.select_files_btn)
        intake_row.addWidget(self.select_folder_btn)
        right_layout.addLayout(intake_row)

        # Sunken Drop Zone Container
        drop_box = QWidget()
        drop_box.setObjectName("sunkenBox")
        drop_layout = QVBoxLayout(drop_box)
        drop_layout.setContentsMargins(8, 8, 8, 8)
        drop_layout.setSpacing(6)

        # Drop Zone Icon / Button
        self.icon_btn = QPushButton()
        self.icon_btn.setFixedSize(54, 54)
        self.icon_btn.setObjectName("fileIconBtn")
        self.icon_btn.setIcon(get_icon("folder"))
        self.icon_btn.setIconSize(QPixmap(36, 36).size())
        self.icon_btn.clicked.connect(self.select_file)
        drop_layout.addWidget(self.icon_btn, 0, Qt.AlignmentFlag.AlignCenter)

        # File labels inside sunken box
        self.input_label = QLabel("No input file selected")
        self.input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_label.setWordWrap(True)
        self.input_label.setStyleSheet("color: #000000; font-weight: bold;")
        drop_layout.addWidget(self.input_label)

        self.input_format_label = QLabel("-")
        self.input_format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_format_label.setStyleSheet("font-weight: bold; color: #000080;")
        drop_layout.addWidget(self.input_format_label)

        right_layout.addWidget(drop_box)

        # Badges area
        badges_h = QHBoxLayout()
        badges_h.setSpacing(6)
        self.badge_fidelity = QLabel("")
        self.badge_fidelity.setObjectName("badge")
        self.badge_warnings = QLabel("")
        self.badge_warnings.setObjectName("warning")
        self.badge_limitations = QLabel("")
        self.badge_limitations.setObjectName("limitation")
        badges_h.addWidget(self.badge_fidelity)
        badges_h.addWidget(self.badge_warnings)
        badges_h.addWidget(self.badge_limitations)
        badges_h.addStretch()
        right_layout.addLayout(badges_h)

        # Hints / Status text
        self.hints_text = QTextEdit()
        self.hints_text.setObjectName("hintsText")
        self.hints_text.setReadOnly(True)
        self.hints_text.setFixedHeight(110)
        right_layout.addWidget(self.hints_text)

        # Produced artifacts actions
        self.open_output_btn = QPushButton("Open Converted File")
        self.open_output_btn.setIcon(get_icon("file"))
        self.open_output_btn.clicked.connect(self._open_produced_output)
        self.open_output_btn.setVisible(False)

        self.reveal_output_btn = QPushButton("Show in Folder")
        self.reveal_output_btn.setIcon(get_icon("reveal"))
        self.reveal_output_btn.clicked.connect(self._reveal_produced_output)
        self.reveal_output_btn.setVisible(False)

        right_layout.addWidget(self.open_output_btn)
        right_layout.addWidget(self.reveal_output_btn)
        right_layout.addStretch()

        right_card.setLayout(right_layout)
        right_card.setFixedWidth(360)

        content_h.addWidget(left_card, 3)
        content_h.addWidget(right_card, 1)
        main_v.addLayout(content_h)

        # Global progress bar & status at the bottom
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #000000; font-size: 11px; font-weight: bold;")
        main_v.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        main_v.addWidget(self.progress)

        central.setLayout(main_v)
        self.setCentralWidget(central)

        self._formats_grid_layout = grid
        self._format_buttons: dict[str, QPushButton] = {}

    def _on_language_changed(self, idx: int) -> None:
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self.service.set_language(lang_code)
            self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Dynamically update all user-facing strings according to the active language."""
        t = self.translator.t
        self.setWindowTitle(f"{t('app.title')} {t('app.version')}")
        self.title_label.setText(t("app.title"))
        self.lang_label.setText(t("language.selector"))
        self.options_header_label.setText(t("section.options"))
        self.select_files_btn.setText(t("button.select_files"))
        self.select_folder_btn.setText(t("button.select_folder"))
        self.save_as_btn.setText(t("button.save_as"))
        self.convert_btn.setText(t("button.convert"))
        self.cancel_btn.setText(t("button.cancel"))
        self.open_output_btn.setText(t("button.open_file"))
        self.reveal_output_btn.setText(t("button.reveal_folder"))

        if not self.input_path and not self.input_paths:
            self.input_label.setText(t("status.no_input"))
            self._refresh_format_buttons(None)
        else:
            # Category headers and any "no conversions available" message in
            # the format grid are language-dependent text set imperatively
            # when the input was selected; regenerate them in the new
            # language rather than leaving them stuck in the old one.
            prev_selected_format = self.selected_output_format
            common_outputs = self.service.get_available_outputs(self._detected_formats)
            self._refresh_format_buttons_from_outputs(common_outputs)
            if prev_selected_format in self._format_buttons:
                # Restores checked state, output_path, and the destination
                # filename shown on the Save As button — all of which the
                # grid rebuild above just reset.
                self._on_format_button_clicked(prev_selected_format)

        if self.selected_folder_name and self.input_paths:
            self.input_label.setText(
                t(
                    "status.folder_selected",
                    name=self.selected_folder_name,
                    count=len(self.input_paths),
                )
            )
        elif self.input_paths and len(self.input_paths) > 1:
            self.input_label.setText(
                self.translator.t_plural(
                    "status.files_selected_single",
                    "status.files_selected_plural",
                    len(self.input_paths),
                )
            )
        elif self.input_path:
            self.input_label.setText(self.input_path.name)

        # Refresh hints
        cur_out_fmt = self.selected_output_format
        in_fmt = self.input_format_label.text()
        if cur_out_fmt and in_fmt and in_fmt != "-":
            self._update_hints_and_badges(in_fmt, cur_out_fmt)

        # A terminal completed/cancelled/failed status set by a prior
        # conversion is not reactive on its own; re-derive it in the new
        # language rather than leaving it stuck in whatever language it was
        # originally shown in.
        if self.current_batch and self.current_batch.is_terminal:
            self.status_label.setText(self._terminal_status_text(self.current_batch.status))
        elif self.current_job and self.current_job.status.is_terminal:
            self.status_label.setText(self._terminal_status_text(self.current_job.status))

    def _clear_formats_grid(self) -> None:
        layout = self._formats_grid_layout
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _refresh_format_buttons(self, input_fmt: str | None) -> None:
        self._clear_formats_grid()
        self._format_buttons.clear()
        layout = self._formats_grid_layout
        self.selected_output_format = None

        if not input_fmt:
            label = QLabel(self.translator.t("status.select_prompt"))
            label.setWordWrap(True)
            layout.addWidget(label, 0, 0)
            label.show()

    def _refresh_format_buttons_from_outputs(self, outputs: set[str]) -> None:
        self._clear_formats_grid()
        self._format_buttons.clear()
        layout = self._formats_grid_layout

        if not outputs:
            label = QLabel(self.translator.t("status.no_conversions"))
            layout.addWidget(label, 0, 0)
            label.show()
            return

        groups: dict[str, list[str]] = {}
        for out in outputs:
            cat = self.catalog.category_of(out) or "other"
            groups.setdefault(cat, []).append(out)

        row = 0
        cols = 3
        for cat_id, cat_label in self.catalog.category_labels.items():
            outs = groups.get(cat_id)
            if not outs:
                continue
            localized_cat = self.translator.t(f"category.{cat_id}")
            if localized_cat.startswith("category."):
                localized_cat = cat_label
            cat_lbl = QLabel(localized_cat)
            cat_lbl.setFont(get_system_font(9, bold=True))
            layout.addWidget(cat_lbl, row, 0, 1, cols)
            cat_lbl.show()
            row += 1

            col = 0
            for out_id in outs:
                fmt = self.catalog.get_format(out_id)
                label_text = fmt.label if fmt else out_id
                btn = QPushButton(label_text)
                btn.setCheckable(True)
                btn.setProperty("fmt_id", out_id)
                btn.clicked.connect(lambda checked, f=out_id: self._on_format_button_clicked(f))
                layout.addWidget(btn, row, col)
                btn.show()
                self._format_buttons[out_id] = btn
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            if col != 0:
                row += 1

        self._formats_grid.adjustSize()

        if self.selected_output_format not in outputs:
            if len(outputs) == 1:
                single_fmt = next(iter(outputs))
                self._on_format_button_clicked(single_fmt)
            else:
                self.selected_output_format = None

    def _on_format_button_clicked(self, fmt_id: str) -> None:
        for fid, btn in self._format_buttons.items():
            btn.setChecked(fid == fmt_id)
        self.selected_output_format = fmt_id

        in_fmt = self.input_format_label.text()
        details = self.service.get_capability_details(in_fmt, fmt_id)

        if self.input_path:
            if details["is_multi_output"]:
                self.output_path = self.input_path.parent / f"{self.input_path.stem}_{fmt_id}_pages"
                self.save_as_btn.setText(f"{self.output_path.name}/")
            else:
                self.output_path = self.input_path.with_suffix(f".{fmt_id}")
                self.save_as_btn.setText(self.output_path.name)

        self._update_hints_and_badges(in_fmt, fmt_id)
        self._update_controls_state()
        self.save_as_btn.setEnabled(bool(self.selected_output_format))

    def _update_hints_and_badges(self, input_fmt: str, out_fmt: str | None) -> None:
        if not input_fmt or not out_fmt or input_fmt == "-":
            self.badge_fidelity.setText("")
            self.badge_warnings.setText("")
            self.badge_limitations.setText("")
            self.hints_text.setPlainText("")
            return

        details = self.service.get_capability_details(input_fmt, out_fmt)
        t = self.translator.t

        raw_fidelity = details.get("fidelity") or "medium"
        fidelity_label = t(f"badge.fidelity_{raw_fidelity.lower()}")
        if fidelity_label.startswith("badge.fidelity_"):
            fidelity_label = raw_fidelity.capitalize()

        self.badge_fidelity.setText(f"{t('badge.fidelity')}: {fidelity_label}")
        self.badge_warnings.setText(", ".join(details.get("warnings") or []))
        self.badge_limitations.setText(", ".join(details.get("limitations") or []))

        self.badge_fidelity.setVisible(bool(self.badge_fidelity.text()))
        self.badge_warnings.setVisible(bool(self.badge_warnings.text()))
        self.badge_limitations.setVisible(bool(self.badge_limitations.text()))

        lines: list[str] = []
        lines.append(f"{t('badge.fidelity')}: {fidelity_label}")
        if details.get("is_multi_output"):
            lines.append(t("note.multi_output"))
        if details.get("warnings"):
            lines.append(f"{t('badge.warnings')}: {', '.join(details['warnings'])}")
        if details.get("limitations"):
            lines.append(f"{t('badge.limitations')}: {', '.join(details['limitations'])}")

        self.hints_text.setPlainText("\n".join(lines))

    def _populate_formats(self) -> None:
        pass

    # --- Input Handlers ---------------------------------------------------------
    def select_file(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, self.translator.t("dialog.select_files_title")
        )
        if not files:
            return
        self._handle_files_selected([Path(p) for p in files])

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.translator.t("dialog.select_folder_title")
        )
        if not folder:
            return
        self._handle_folder_selected(Path(folder))

    def _handle_folder_selected(self, folder: Path) -> None:
        files = [f for f in folder.rglob("*") if f.is_file() and not f.name.startswith(".")]
        if not files:
            QMessageBox.information(
                self,
                self.translator.t("dialog.select_folder_title"),
                self.translator.t("status.no_conversions"),
            )
            return
        self.selected_folder_name = folder.name
        self._handle_files_selected(files)

    def _handle_files_selected(self, paths: list[Path]) -> None:
        self.input_paths = paths
        self.open_output_btn.setVisible(False)
        self.reveal_output_btn.setVisible(False)
        t = self.translator.t

        detected_formats: list[str] = []
        for p in paths:
            fmt = self.service.detect_format(p)
            detected_formats.append(fmt.id)
        self._detected_formats = detected_formats

        if len(paths) == 1:
            self.input_path = paths[0]
            self.selected_folder_name = None
            self.input_label.setText(self.input_path.name)
            self.input_format_label.setText(detected_formats[0])
        else:
            self.input_path = None
            if self.selected_folder_name:
                self.input_label.setText(
                    t("status.folder_selected", name=self.selected_folder_name, count=len(paths))
                )
            else:
                self.input_label.setText(
                    self.translator.t_plural(
                        "status.files_selected_single",
                        "status.files_selected_plural",
                        len(paths),
                    )
                )

            if all(f == detected_formats[0] for f in detected_formats):
                self.input_format_label.setText(detected_formats[0])
            else:
                self.input_format_label.setText(t("status.various_formats"))

        common_outputs = self.service.get_available_outputs(detected_formats)
        self._refresh_format_buttons_from_outputs(common_outputs)

        cur_out_fmt = self.selected_output_format
        if cur_out_fmt and self.input_path:
            details = self.service.get_capability_details(detected_formats[0], cur_out_fmt)
            if details["is_multi_output"]:
                self.output_path = (
                    self.input_path.parent / f"{self.input_path.stem}_{cur_out_fmt}_pages"
                )
                self.save_as_btn.setText(f"{self.output_path.name}/")
            else:
                self.output_path = self.input_path.with_suffix(f".{cur_out_fmt}")
                self.save_as_btn.setText(self.output_path.name)
        else:
            self.output_path = None
            self.save_as_btn.setText(t("button.save_as"))

        if cur_out_fmt and len(detected_formats) == 1:
            self._update_hints_and_badges(detected_formats[0], cur_out_fmt)

        self._update_controls_state()
        self.save_as_btn.setEnabled(bool(self.selected_output_format))

    def choose_output_path(self) -> None:
        out_fmt = self.selected_output_format
        t = self.translator.t
        if not out_fmt:
            QMessageBox.information(
                self,
                t("dialog.save_as_title"),
                t("dialog.select_output_first"),
            )
            return

        input_fmt = self.input_format_label.text()
        details = self.service.get_capability_details(input_fmt, out_fmt)

        is_batch = bool(self.input_paths and len(self.input_paths) > 1)
        is_multi_output = details["is_multi_output"]

        if is_batch or is_multi_output:
            start_dir = (
                str(self.output_path)
                if (self.output_path and self.output_path.is_dir())
                else (str(self.input_path.parent) if self.input_path else "")
            )
            dir_path = QFileDialog.getExistingDirectory(
                self, t("dialog.select_folder_title"), start_dir
            )
            if not dir_path:
                return
            self.output_path = Path(dir_path)
            self.save_as_btn.setText(f"{self.output_path.name}/")
        else:
            suggested = self.output_path or (
                self.input_path.with_suffix(f".{out_fmt}")
                if (self.input_path and out_fmt)
                else Path.cwd()
            )
            path, _ = QFileDialog.getSaveFileName(self, t("dialog.save_as_title"), str(suggested))
            if not path:
                return
            self.output_path = Path(path)
            self.save_as_btn.setText(self.output_path.name)

        self._update_controls_state()

    def _open_produced_output(self) -> None:
        if not self.last_results:
            return
        art = self.last_results[0].primary_output
        if art and art.exists:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(art.path)))

    def _reveal_produced_output(self) -> None:
        if not self.last_results:
            return
        art = self.last_results[0].primary_output
        if art:
            target_dir = art.path.parent if art.path.is_file() else art.path
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    def _show_conversion_result(self) -> None:
        t = self.translator.t
        if self.current_batch:
            if self.current_batch.status == JobStatus.COMPLETED:
                total_arts = sum(len(res.output_artifacts) for res in self.last_results)
                msg = t("dialog.completed_msg_batch", count=total_arts)
                QMessageBox.information(self, t("dialog.completed_title"), msg)
                self.open_output_btn.setVisible(False)
                self.reveal_output_btn.setVisible(True)
            elif self.current_batch.status == JobStatus.CANCELLED:
                QMessageBox.warning(self, t("dialog.cancel_title"), t("dialog.cancel_msg"))
            else:
                QMessageBox.critical(self, t("dialog.error_title"), t("status.failed"))
            return

        if not self.current_job:
            return

        if self.current_job.status == JobStatus.COMPLETED:
            produced_count = len(self.current_job.produced_artifacts)
            msg = t("dialog.completed_msg_single", count=produced_count)
            QMessageBox.information(self, t("dialog.completed_title"), msg)
            self.open_output_btn.setVisible(True)
            self.reveal_output_btn.setVisible(True)
        elif self.current_job.status == JobStatus.CANCELLED:
            QMessageBox.warning(self, t("dialog.cancel_title"), t("dialog.cancel_msg"))
            self.open_output_btn.setVisible(False)
            self.reveal_output_btn.setVisible(False)
        elif self.current_job.status in (JobStatus.FAILED, JobStatus.PARTIAL):
            err = self.current_job.errors[0] if self.current_job.errors else None
            msg = self.service.format_error_message(err)

            # Actionable error dialog with expandable technical details
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle(t("dialog.error_title"))
            box.setText(msg)
            if err and err.details:
                box.setDetailedText(err.details)
            box.exec()

            self.open_output_btn.setVisible(False)
            self.reveal_output_btn.setVisible(False)

    def _update_controls_state(self) -> None:
        out_fmt = self.selected_output_format
        enabled = bool((self.input_path or self.input_paths) and self.output_path and out_fmt)
        self.convert_btn.setEnabled(enabled)

    def cancel_conversion(self) -> None:
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(self.translator.t("status.cancelling"))
        if self.current_batch:
            self.service.request_cancel_batch(self.current_batch)
        elif self.current_job:
            self.service.request_cancel_job(self.current_job)

    def start_conversion(self) -> None:
        if not self.input_path and not (self.input_paths and len(self.input_paths) > 0):
            return

        output_format: str | None = self.selected_output_format
        if not output_format:
            return

        t = self.translator.t

        if not self.output_path:
            if self.input_path:
                self.output_path = self.input_path.with_suffix(f".{output_format}")
            else:
                return

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_label.setText(t("status.starting"))
        self.open_output_btn.setVisible(False)
        self.reveal_output_btn.setVisible(False)

        try:
            if self.input_paths and len(self.input_paths) > 1:
                if not self.output_path.is_dir():
                    QMessageBox.warning(
                        self,
                        t("dialog.error_title"),
                        t("dialog.invalid_out_dir"),
                    )
                    self.convert_btn.setEnabled(True)
                    self.cancel_btn.setEnabled(False)
                    return

                self.current_batch = self.service.create_batch(
                    input_paths=self.input_paths,
                    output_format_id=output_format,
                    destination_directory=self.output_path,
                )
                self.current_job = None
            else:
                inp = self.input_path or self.input_paths[0]  # type: ignore[index]
                self.current_job = self.service.create_single_job(
                    input_path=inp,
                    output_format_id=output_format,
                    destination_path=self.output_path,
                )
                self.current_batch = None

        except Exception as exc:
            QMessageBox.critical(
                self, t("dialog.error_title"), f"{t('error.unknown', details=str(exc))}"
            )
            self.convert_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            return

        t_thread = threading.Thread(target=self._run_conversion_thread, daemon=True)
        t_thread.start()
        self._start_polling()

    def _run_conversion_thread(self) -> None:
        try:
            if self.current_batch:
                self.last_results = self.service.execute_batch(self.current_batch)
            elif self.current_job:
                res = self.service.execute_job(self.current_job)
                self.last_results = [res]
        except Exception as exc:
            print(f"Unhandled error during conversion: {exc}")
        finally:
            with contextlib.suppress(Exception):
                QTimer.singleShot(0, self._update_progress)

    def _start_polling(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(100)

    def _terminal_status_text(self, status: JobStatus) -> str:
        t = self.translator.t
        if status == JobStatus.COMPLETED:
            return t("status.completed")
        if status == JobStatus.CANCELLED:
            return t("status.cancelled")
        return t("status.failed")

    def _update_progress(self) -> None:
        t = self.translator.t
        if self.current_batch:
            val = int(self.current_batch.aggregate_progress * 100)
            self.progress.setValue(val)
            done = self.current_batch.completed_count
            tot = self.current_batch.total_count
            self.status_label.setText(t("status.converting_batch", done=done, total=tot))
            if self.current_batch.is_terminal:
                self.timer.stop()
                self.convert_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.status_label.setText(self._terminal_status_text(self.current_batch.status))
                self._show_conversion_result()
                return

        if self.current_job:
            val = int(self.current_job.progress * 100)
            self.progress.setValue(val)
            if self.current_job.plan.pipeline.is_multi_stage:
                tot_stages = self.current_job.plan.pipeline.stage_count
                cur_stage = max(1, min(tot_stages, int(self.current_job.progress * tot_stages) + 1))
                self.status_label.setText(
                    t("status.converting_pipeline", stage=cur_stage, total=tot_stages)
                )
            else:
                self.status_label.setText(t("status.converting_single", progress=val))

            if self.current_job.status.is_terminal:
                self.timer.stop()
                self.convert_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.status_label.setText(self._terminal_status_text(self.current_job.status))
                self._show_conversion_result()
