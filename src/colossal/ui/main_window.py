from pathlib import Path
import json
import contextlib

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QComboBox,
    QProgressBar,
    QTextEdit,
    QSizePolicy,
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QStyle
import threading
import traceback
from PySide6.QtWidgets import QMessageBox

from colossal.models.conversion_task import ConversionTask
from colossal.models.task_status import TaskStatus


class MainWindow(QMainWindow):
    def __init__(self, engine, manifest):
        super().__init__()

        self.engine = engine
        self.manifest = manifest
        self.task: ConversionTask | None = None
        self.input_path: Path | None = None
        # support single or multiple input files
        self.input_paths: list[Path] | None = None
        self.output_path: Path | None = None

        self.setWindowTitle("Colossal Conversor v4.0.0")

        # load theme qss if available (non-fatal)
        qss_path = Path(__file__).resolve().parent.parent / "resources" / "theme.qss"
        with contextlib.suppress(OSError, FileNotFoundError, UnicodeDecodeError):
            if qss_path.exists():
                self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

        # build conversion hints map from per-category manifests
        self._conversion_hints = self._load_conversion_hints()

        self._build_ui()
        self._populate_formats()

    # --- conversion hints helpers -------------------------------------------------
    def _load_manifest_file(self, jf: Path) -> dict | None:
        try:
            return json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _add_conversion_entry(self, hints: dict, conv: dict) -> None:
        tos = conv.get("to")
        tos_list = tos if isinstance(tos, list) else [tos]
        froms = conv.get("from")
        if froms in ("*", ["*"]):
            return
        froms_list = froms if isinstance(froms, list) else [froms]

        for f in froms_list:
            for t in tos_list:
                hints.setdefault(f, {})[t] = {
                    "fidelity": conv.get("fidelity"),
                    "warnings": conv.get("warnings") or [],
                    "limitations": conv.get("limitations") or [],
                    "default_preset": conv.get("default_preset"),
                    "output": (conv.get("output") or {}).get("type"),
                }

    def _load_conversion_hints(self) -> dict:
        """Load per-category manifests from resources/formats and return a mapping
        (input_format -> output_format -> hints_dict). This is split into helpers
        to keep cognitive complexity low.
        """
        hints: dict = {}
        formats_dir = Path(__file__).resolve().parent.parent / "resources" / "formats"
        if not formats_dir.exists():
            return hints

        for jf in formats_dir.glob("*.json"):
            data = self._load_manifest_file(jf)
            if not data:
                continue
            for conv in data.get("conversions", []):
                self._add_conversion_entry(hints, conv)

        return hints

    # --- UI building -------------------------------------------------------------
    def _build_ui(self):
        # Topbar + two-column layout
        self.setMinimumSize(900, 560)

        central = QWidget()
        central.setObjectName("card")
        main_v = QVBoxLayout()
        main_v.setContentsMargins(12, 12, 12, 12)

        # Topbar with app icon and title
        topbar = QHBoxLayout()
        app_icon_label = QLabel()
        app_icon_label.setObjectName("appIcon")
        with contextlib.suppress(Exception):
            icons_dir = Path(__file__).resolve().parent.parent / "resources" / "icons"
            icon_file = icons_dir / "Colossal Conversor.png"
            if icon_file.exists():
                pix = QPixmap(str(icon_file)).scaled(48, 48)
                app_icon_label.setPixmap(pix)

        title = QLabel("Colossal Conversor")
        title.setObjectName("title")
        font = QFont("Sans Serif", 18)
        font.setBold(True)
        title.setFont(font)
        topbar.addWidget(app_icon_label)
        topbar.addWidget(title)
        topbar.addStretch()
        main_v.addLayout(topbar)

        # Main content: left = formats grid, right = file card
        content_h = QHBoxLayout()
        content_h.setSpacing(16)

        # Left panel: formats grid inside a scrollable area
        from PySide6.QtWidgets import QScrollArea
        left_card = QWidget()
        left_card.setObjectName("card")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)

        lbl = QLabel("Opciones de conversión")
        lbl.setFont(QFont("Sans Serif", 12))
        left_layout.addWidget(lbl)

        # output combo (kept for compatibility and quick selection)
        self.output_combo = QComboBox()
        self.output_combo.currentIndexChanged.connect(self._on_output_changed)
        left_layout.addWidget(self.output_combo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_container = QWidget()
        self._formats_grid = grid_container
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout(grid_container)
        grid.setSpacing(8)
        grid.setContentsMargins(6, 6, 6, 6)
        grid_container.setLayout(grid)

        scroll.setWidget(grid_container)
        left_layout.addWidget(scroll)

        # Bottom controls in left panel
        bottom_row = QHBoxLayout()
        self.save_as_btn = QPushButton("Guardar como...")
        self.save_as_btn.setObjectName("saveBtn")
        self.save_as_btn.clicked.connect(self.choose_output_path)
        self.save_as_btn.setEnabled(False)
        self.convert_btn = QPushButton("Convertir")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        bottom_row.addWidget(self.save_as_btn)
        bottom_row.addWidget(self.convert_btn)
        left_layout.addLayout(bottom_row)

        left_card.setLayout(left_layout)
        left_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Right panel: file selector and badges
        right_card = QWidget()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(10, 10, 10, 10)

        # File select as icon button (use standard open icon for clarity)
        self.icon_btn = QPushButton()
        self.icon_btn.setFixedSize(88, 88)
        self.icon_btn.setObjectName("fileIconBtn")
        self.icon_btn.clicked.connect(self.select_file)
        # Prefer using a bundled SVG open icon; fall back to platform standard icon, then text
        try:
            icons_dir = Path(__file__).resolve().parent.parent / "resources" / "icons"
            open_svg = icons_dir / "open.svg"
            if open_svg.exists():
                from PySide6.QtGui import QIcon
                qicon = QIcon(str(open_svg))
                self.icon_btn.setIcon(qicon)
                self.icon_btn.setIconSize(pix := QPixmap(str(open_svg)).scaled(48, 48).size())
            else:
                std_icon = self.style().standardIcon(QStyle.SP_DialogOpenButton)
                if not std_icon.isNull():
                    self.icon_btn.setIcon(std_icon)
                    self.icon_btn.setIconSize(QPixmap(48, 48).size())
                else:
                    raise RuntimeError("no icon")
        except Exception:
            self.icon_btn.setText("Abrir")

        right_layout.addWidget(self.icon_btn, 0)

        # file labels
        self.input_label = QLabel("No input file selected")
        self.input_label.setWordWrap(True)
        right_layout.addWidget(self.input_label)

        self.input_format_label = QLabel("-")
        right_layout.addWidget(self.input_format_label)

        # badges area
        badges_h = QHBoxLayout()
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

        # hints text
        self.hints_text = QTextEdit()
        self.hints_text.setObjectName("hintsText")
        self.hints_text.setReadOnly(True)
        self.hints_text.setFixedHeight(140)
        right_layout.addWidget(self.hints_text)

        right_card.setLayout(right_layout)
        right_card.setFixedWidth(320)

        content_h.addWidget(left_card, 3)
        content_h.addWidget(right_card, 1)

        main_v.addLayout(content_h)

        # Global progress bar at the bottom
        self.progress = QProgressBar()
        self.progress.setValue(0)
        main_v.addWidget(self.progress)

        central.setLayout(main_v)
        self.setCentralWidget(central)

        # store grid reference and prepare format buttons mapping
        self._formats_grid_layout = grid
        self._format_buttons: dict[str, QPushButton] = {}

        # initially show placeholder; real buttons built when input selected
        self._refresh_format_buttons(None)

        # track current output type (e.g., 'file', 'single_file', 'multi_file') and whether save target is a dir
        self.output_type_current: str | None = None
        self.save_as_is_dir: bool = False
        self.selected_output_format: str | None = None

    def _build_format_buttons(self):
        # create a button for each target format label in manifest
        # layout as grid with 3 columns
        formats = []
        for cat in self.manifest.categories.values():
            for fmt in cat.formats.values():
                formats.append((fmt.id, fmt.label))

        cols = 3
        row = 0
        col = 0
        for fid, label in formats:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("fmt_id", fid)
            btn.clicked.connect(lambda checked, f=fid: self._on_format_button_clicked(f))
            self._formats_grid_layout.addWidget(btn, row, col)
            self._format_buttons[fid] = btn
            # if combo already has this item, ensure it's present later by populate_formats
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _clear_formats_grid(self):
        """Remove all widgets from the formats grid layout."""
        layout = self._formats_grid_layout
        # take items until empty
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _refresh_format_buttons(self, input_fmt: str | None):
        """Rebuild the left-panel format buttons grouped by category.
        If input_fmt is None, show a helper instruction.
        """
        self._clear_formats_grid()
        # clear mapping of buttons to avoid stale references
        self._format_buttons.clear()
        layout = self._formats_grid_layout

        # reset selected output format when rebuilding
        self.selected_output_format = None

        if not input_fmt:
            label = QLabel("Selecciona un archivo a la derecha para ver las opciones de conversión disponibles.")
            label.setWordWrap(True)
            layout.addWidget(label, 0, 0)
            return

    def _refresh_format_buttons_from_outputs(self, outputs: set[str]):
        """Rebuild format buttons grouped by category using an explicit set of available outputs."""
        self._clear_formats_grid()
        self._format_buttons.clear()
        layout = self._formats_grid_layout

        if not outputs:
            label = QLabel("No hay conversiones disponibles para los archivos seleccionados.")
            layout.addWidget(label, 0, 0)
            return

        # group outputs by category id preserving manifest order
        groups: dict[str, list[str]] = {}
        for out in outputs:
            cat = self.manifest.category_of(out) or "other"
            groups.setdefault(cat, []).append(out)

        row = 0
        cols = 3
        for cat_id, category in self.manifest.categories.items():
            outs = groups.get(cat_id)
            if not outs:
                continue
            cat_lbl = QLabel(category.label)
            cat_lbl.setFont(QFont("Sans Serif", 11))
            layout.addWidget(cat_lbl, row, 0, 1, cols)
            row += 1

            col = 0
            for out_id in outs:
                fmt = category.formats.get(out_id)
                label = fmt.label if fmt else out_id
                btn = QPushButton(label)
                btn.setCheckable(True)
                btn.setProperty("fmt_id", out_id)
                btn.clicked.connect(lambda checked, f=out_id: self._on_format_button_clicked(f))
                layout.addWidget(btn, row, col)
                self._format_buttons[out_id] = btn
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            if col != 0:
                row += 1

        # sync combo with available outputs
        self.output_combo.clear()
        added = set()
        for cat in self.manifest.categories.values():
            for fmt in cat.formats.values():
                if fmt.id in outputs and fmt.id not in added:
                    self.output_combo.addItem(fmt.label, fmt.id)
                    added.add(fmt.id)

    def _on_format_button_clicked(self, fmt_id: str):
        # uncheck others
        for fid, btn in self._format_buttons.items():
            if fid != fmt_id:
                btn.setChecked(False)
        # set selected format and update UI
        self.selected_output_format = fmt_id
        # update save_as suggested name
        if self.input_path:
            self.output_path = self.input_path.with_suffix(f".{fmt_id}")
            self.save_as_btn.setText(self.output_path.name)
        # update badges and hints
        self._update_hints(self.input_format_label.text(), fmt_id)
        self._update_badges(self.input_format_label.text(), fmt_id)
        # capture output type for this conversion
        hints = self._conversion_hints.get(self.input_format_label.text(), {}).get(fmt_id, {})
        self.output_type_current = hints.get('output') or None
        # sync combo selection if populated
        try:
            idx = next(i for i in range(self.output_combo.count()) if self.output_combo.itemData(i) == fmt_id)
            self.output_combo.setCurrentIndex(idx)
        except StopIteration:
            pass
        self._update_controls_state()
        # enable save button when a format is selected
        self.save_as_btn.setEnabled(bool(self.selected_output_format))

    def _update_badges(self, input_fmt: str, out_fmt: str | None):
        # update small badges showing fidelity, warnings and limitations
        if not input_fmt or not out_fmt:
            self.badge_fidelity.setText("")
            self.badge_warnings.setText("")
            self.badge_limitations.setText("")
            return
        hints = self._conversion_hints.get(input_fmt, {}).get(out_fmt, {})
        fidelity = hints.get("fidelity") or ""
        self.badge_fidelity.setText(fidelity)
        self.badge_warnings.setText(", ".join(hints.get("warnings") or []))
        self.badge_limitations.setText(", ".join(hints.get("limitations") or []))

        # set visibility
        self.badge_fidelity.setVisible(bool(self.badge_fidelity.text()))
        self.badge_warnings.setVisible(bool(self.badge_warnings.text()))
        self.badge_limitations.setVisible(bool(self.badge_limitations.text()))
        # style fidelity badge by value
        if fidelity:
            low = ["low", "lossy", "low"]
            med = ["medium", "medium"]
            if fidelity.lower() in ("high",):
                self.badge_fidelity.setStyleSheet("background: #43dee7; color: #fff; padding:4px 8px; border-radius:8px;")
            elif fidelity.lower() in ("medium",):
                self.badge_fidelity.setStyleSheet("background: #ffd54f; color: #1c6282; padding:4px 8px; border-radius:8px;")
            else:
                self.badge_fidelity.setStyleSheet("background: #ff8a65; color: #fff; padding:4px 8px; border-radius:8px;")
        else:
            self.badge_fidelity.setStyleSheet("")

    def _populate_formats(self):
        # Populate output combo with all known format ids (label + id)
        self.output_combo.clear()
        for cat in self.manifest.categories.values():
            for fmt in cat.formats.values():
                self.output_combo.addItem(fmt.label, fmt.id)

    # --- user interactions ------------------------------------------------------
    def select_file(self):
        # allow selecting multiple files
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivo(s)")
        if not files:
            return

        paths = [Path(p) for p in files]
        self.input_paths = paths
        # UI label
        if len(paths) == 1:
            self.input_path = paths[0]
            self.input_label.setText(self.input_path.name)
        else:
            self.input_path = None
            self.input_label.setText(f"{len(paths)} archivos seleccionados")

        # detect input formats and compute available outputs intersection
        input_exts = [p.suffix.lstrip('.').lower() for p in paths]
        common_fmt = None
        if all(e == input_exts[0] for e in input_exts):
            common_fmt = input_exts[0]
            self.input_format_label.setText(common_fmt)
        else:
            self.input_format_label.setText('-')

        # Build outputs set: intersection of available outputs for each input format (or union if unknown)
        outputs_sets = []
        for ext in set(input_exts):
            outs = set(self._conversion_hints.get(ext, {}).keys())
            outputs_sets.append(outs)

        if outputs_sets:
            # intersection across formats
            common_outputs = set(outputs_sets[0])
            for s in outputs_sets[1:]:
                common_outputs &= s
        else:
            common_outputs = set()

        # rebuild left panel based on available outputs set
        self._refresh_format_buttons_from_outputs(common_outputs)

        # set default output_path suggestion
        cur_out_fmt = getattr(self, 'selected_output_format', None) or self.output_combo.currentData()
        if cur_out_fmt and self.input_path:
            self.output_path = self.input_path.with_suffix(f".{cur_out_fmt}")
            self.save_as_btn.setText(self.output_path.name)
        else:
            self.output_path = None
            self.save_as_btn.setText("Guardar como...")

        # update hints for default selection (if single)
        if common_fmt and cur_out_fmt:
            self._update_hints(common_fmt, cur_out_fmt)

        self._update_controls_state()

        # enable Guardar como if there are outputs available
        self.save_as_btn.setEnabled(self.output_combo.count() > 0)

    def _populate_outputs_for_input(self, input_fmt: str):
        self.output_combo.blockSignals(True)
        self.output_combo.clear()

        # collect outputs where conversion exists for input_fmt
        hints_for_input = self._conversion_hints.get(input_fmt, {})
        outputs = set(hints_for_input) or {fmt.id for cat in self.manifest.categories.values() for fmt in cat.formats.values()}

        # Add sorted by label where possible
        added = set()
        for cat in self.manifest.categories.values():
            for fmt in cat.formats.values():
                if fmt.id in outputs and fmt.id not in added:
                    self.output_combo.addItem(fmt.label, fmt.id)
                    added.add(fmt.id)

        self.output_combo.blockSignals(False)

    def _on_output_changed(self, idx: int):
        out_fmt = self.output_combo.currentData()
        input_fmt = self.input_format_label.text()
        # update default output_path extension if input exists
        if self.input_path and out_fmt:
            self.output_path = self.input_path.with_suffix(f".{out_fmt}")
            self.save_as_btn.setText(self.output_path.name)
        self._update_hints(input_fmt, out_fmt)
        # capture output type for combo selection
        hints = self._conversion_hints.get(input_fmt, {}).get(out_fmt, {})
        self.output_type_current = hints.get('output') or None
        # update badges as well
        self._update_badges(input_fmt, out_fmt)
        self._update_controls_state()
        # enable save button when combo selection exists
        out_fmt = self.output_combo.currentData()
        self.save_as_btn.setEnabled(bool(out_fmt))

    def choose_output_path(self):
        # Determine whether the current converter expects multiple output files
        out_fmt = getattr(self, 'selected_output_format', None) or self.output_combo.currentData()
        if not out_fmt:
            QMessageBox.information(self, "Selecciona formato", "Por favor selecciona primero el formato de salida en la columna izquierda.")
            return
        # for multi-inputs use common input format if available
        input_fmt = self.input_format_label.text()
        hints = self._conversion_hints.get(input_fmt, {}).get(out_fmt, {}) if input_fmt and input_fmt != '-' else {}
        out_type = hints.get('output')

        if (self.input_paths and len(self.input_paths) > 1) or (out_type and 'multi' in out_type):
            # For multi outputs, ask for directory
            start_dir = str(self.output_path) if (self.output_path and self.output_path.is_dir()) else (str(self.input_path.parent) if self.input_path else '')
            dir_path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida", start_dir)
            if not dir_path:
                return
            self.output_path = Path(dir_path)
            self.save_as_is_dir = True
            # update button text to folder name
            self.save_as_btn.setText(f"{self.output_path.name}/")
        else:
            # single file output
            suggested = self.output_path or (self.input_path.with_suffix(f".{out_fmt}") if (self.input_path and out_fmt) else Path.cwd())
            path, _ = QFileDialog.getSaveFileName(self, "Guardar como", str(suggested))
            if not path:
                return
            self.output_path = Path(path)
            self.save_as_is_dir = False
            self.save_as_btn.setText(self.output_path.name)

        self._update_controls_state()

    def _show_conversion_result(self):
        # called after conversion completes to surface errors
        if not self.task:
            return
        if self.task.status == TaskStatus.DONE:
            QMessageBox.information(self, "Completado", f"Conversión completada: {self.output_path}")
        elif self.task.status == TaskStatus.FAILED:
            err = getattr(self.task, 'error', None)
            msg = err.message if err else 'Error desconocido durante la conversión.'
            QMessageBox.critical(self, "Error", msg)

    def _update_hints(self, input_fmt: str, out_fmt: str | None):
        if not input_fmt or not out_fmt:
            self.hints_text.setPlainText("")
            return

        hints = self._conversion_hints.get(input_fmt, {}).get(out_fmt, {})
        if not hints:
            self.hints_text.setPlainText("No hay información específica para esta conversión.")
            self.hints_text.setObjectName("hintsText")
            return

        lines = []
        if hints.get("fidelity"):
            lines.append(f"Fidelity: {hints['fidelity']}")
        if hints.get("warnings"):
            lines.append(f"Warnings: {', '.join(hints['warnings'])}")
        if hints.get("limitations"):
            lines.append(f"Limitations: {', '.join(hints['limitations'])}")
        if hints.get("default_preset"):
            lines.append(f"Preset: {hints['default_preset']}")

        self.hints_text.setPlainText("\n".join(lines))

        # set objectName so QSS applies warning variant when warnings/limitations exist
        if hints.get("warnings") or hints.get("limitations"):
            self.hints_text.setObjectName("hintsTextWarning")
        else:
            self.hints_text.setObjectName("hintsText")

    def _update_controls_state(self):
        # Enable the convert button only when we have both input and output path
        out_fmt = getattr(self, 'selected_output_format', None) or self.output_combo.currentData()
        enabled = bool(self.input_path and self.output_path and out_fmt)
        self.convert_btn.setEnabled(enabled)

    def start_conversion(self):
        if not self.input_path:
            # if multiple inputs selected, input_path may be None but input_paths set
            if not (self.input_paths and len(self.input_paths) > 0):
                return

        output_format = getattr(self, 'selected_output_format', None) or self.output_combo.currentData()
        input_format = self.input_format_label.text()

        if not self.output_path:
            # fallback
            self.output_path = self.input_path.with_suffix(f".{output_format}")

        # disable convert button while running to prevent double submits
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Converting...")

        # Prepare tasks: single or multiple
        tasks = []
        if self.input_paths and len(self.input_paths) > 1:
            # multi-file: require directory as output
            if not (self.output_path and self.output_path.is_dir()):
                QMessageBox.warning(self, "Salida inválida", "Para múltiples archivos selecciona una carpeta de salida (Guardar como...).")
                self.convert_btn.setEnabled(True)
                self.convert_btn.setText("Convertir")
                return
            for p in self.input_paths:
                out_name = p.with_suffix(f".{output_format}").name
                dst = self.output_path / out_name
                tasks.append(ConversionTask(input_path=p, output_path=dst, input_format=p.suffix.lstrip('.').lower(), output_format=output_format))
        else:
            # single
            inp = self.input_path or (self.input_paths[0] if (self.input_paths and len(self.input_paths) == 1) else None)
            tasks.append(ConversionTask(input_path=inp, output_path=self.output_path, input_format=input_format, output_format=output_format))

        # Run conversion(s) in background thread to avoid blocking the UI
        self._multi_tasks = tasks
        # if single task, keep a reference on self.task for UI progress/status checks
        if len(tasks) == 1:
            self.task = tasks[0]
        t = threading.Thread(target=self._run_conversion_thread, args=(tasks,), daemon=True)
        t.start()
        self._start_polling()

    def _run_conversion_thread(self, tasks):
        # tasks may be a single ConversionTask or a list of them
        try:
            if isinstance(tasks, list):
                for t in tasks:
                    self.engine.submit(t)
            else:
                self.engine.submit(tasks)
        except Exception as exc:
            traceback.print_exc()
        finally:
            # schedule a final UI update
            try:
                QTimer.singleShot(0, self._update_progress)
            except Exception:
                pass

    def _aggregate_progress(self) -> float:
        # compute average progress across tasks if multi
        tasks = getattr(self, '_multi_tasks', None)
        if not tasks:
            return 0.0
        total = 0.0
        count = 0
        for t in tasks:
            total += getattr(t, 'progress', 0.0)
            count += 1
        return (total / count) if count else 0.0

    def _start_polling(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(100)

    def _update_progress(self):
        # support aggregated progress when multiple tasks submitted
        multi = getattr(self, '_multi_tasks', None)
        if multi:
            val = int(self._aggregate_progress() * 100)
            self.progress.setValue(val)
            # consider conversion finished if all tasks are terminal
            statuses = [getattr(t, 'status', None) for t in multi]
            if all(s in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED) for s in statuses):
                self.timer.stop()
                self.convert_btn.setEnabled(True)
                self.convert_btn.setText("Convertir")
                # choose overall result: if any failed -> show failure
                if any(s == TaskStatus.FAILED for s in statuses):
                    QMessageBox.critical(self, "Error", "Algunas conversiones fallaron. Revisa el log.")
                else:
                    QMessageBox.information(self, "Completado", "Todas las conversiones finalizaron correctamente.")
                return

        # single-task flow
        if not getattr(self, 'task', None):
            return
        self.progress.setValue(int(self.task.progress * 100))

        if self.task.status in (
            TaskStatus.DONE,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            self.timer.stop()
            # re-enable convert button
            self.convert_btn.setEnabled(True)
            self.convert_btn.setText("Convertir")
            # show result dialog
            self._show_conversion_result()
