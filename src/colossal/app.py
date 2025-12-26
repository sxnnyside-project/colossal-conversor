import contextlib
import sys
from pathlib import Path
import importlib
import traceback
import re
import ast

from PySide6.QtWidgets import QApplication

from colossal.ui.main_window import MainWindow
from colossal.core.engine import ConversionEngine
from colossal.core.registry import ConverterRegistry
from colossal.core.format_loader import load_format_manifest
from colossal.core.base_converter import BaseConverter

# builders
from colossal.builder import (
    audio_converter_builder,
    document_converter_builder,
    image_converter_builder,
    sheet_converter_builder,
    slide_converter_builder,
    video_converter_builder,
)


def _ensure_init_files(root: Path):
    """Create __init__.py in root and in any subdirectory that contains .py files so imports work predictably."""
    # root is the package directory '.../src/colossal'
    converters_dir = root / "converters"
    if not converters_dir.exists():
        return

    # ensure converters package itself has __init__.py
    init = converters_dir / "__init__.py"
    if not init.exists():
        init.write_text("# generated package init\n", encoding="utf-8")

    # for every subdir under converters, if it contains .py files, ensure __init__.py
    for sub in converters_dir.rglob("*"):
        # merge nested checks: is directory and contains .py files
        if sub.is_dir() and any(sub.glob("*.py")):
            init_file = sub / "__init__.py"
            if not init_file.exists():
                init_file.write_text("# generated package init\n", encoding="utf-8")


def _import_module_from_path(py: Path, package_root: Path):
    """Return imported module object for a file within the package, or None on import failure."""
    try:
        rel = py.relative_to(package_root)
    except ValueError:
        # not relative to package root
        return None

    module_name = "colossal." + ".".join(rel.with_suffix("").as_posix().split("/"))
    try:
        return importlib.import_module(module_name)
    except (ImportError, SyntaxError, RuntimeError, AttributeError, OSError):
        # Module couldn't be imported or raised during import (missing dependency, syntax, runtime, OS error)
        traceback.print_exc()
        return None


def _register_converters_from_module(module, registry: ConverterRegistry):
    """Register any BaseConverter subclasses defined in module into the registry."""
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        # Only consider classes
        if not isinstance(attr, type):
            continue
        # Skip the abstract base itself
        if attr is BaseConverter:
            continue
        # Ensure it's a subclass of BaseConverter
        try:
            if not issubclass(attr, BaseConverter):
                continue
        except TypeError:
            # Not a class that issubclass can handle
            continue

        # Try to instantiate and register; capture common instantiation errors
        try:
            instance = attr()
        except (TypeError, RuntimeError, OSError, ValueError):
            # Instantiation failed for known reasons; log and continue
            traceback.print_exc()
            continue

        if doc := getattr(attr, '__doc__', '') or '':
            # look for simple assignments like "input_formats = ['mp4', 'mov']"
            for key in ('input_formats', 'output_formats', 'category', 'options_schema'):
                if not hasattr(instance, key):
                    if m := re.search(
                        rf"^\s*{key}\s*=\s*(.+)$", doc, flags=re.MULTILINE
                    ):
                        rhs = m[1].strip()
                        try:
                            # safely evaluate python literal structures (lists, dicts, strings)
                            val = ast.literal_eval(rhs)
                        except Exception:
                            # fallback: keep as raw string
                            val = rhs.strip("'\" ")
                        with contextlib.suppress(Exception):
                            setattr(instance, key, val)
        registry.register(instance)


def _discover_and_register(converters_root: Path, registry: ConverterRegistry, package_root: Path):
    """Import modules under converters_root and register any BaseConverter subclasses found.

    Split into small helpers to reduce cognitive complexity.
    """
    if not converters_root.exists():
        return

    for py in converters_root.rglob("*.py"):
        # skip dunder and package inits
        if py.name.startswith("__"):
            continue

        module = _import_module_from_path(py, package_root)
        if module is None:
            # import failed or path not relative to package, skip
            continue

        _register_converters_from_module(module, registry)


def run_app():
    app = QApplication(sys.argv)

    registry = ConverterRegistry()

    # load manifest early (used both for engine and builders)
    manifest_path = Path(__file__).resolve().parent / "resources" / "format_manifest.json"

    manifest = load_format_manifest(manifest_path)

    # Generate converters by invoking builders via their CLI entry point `main()`
    # main() uses default MANIFEST_PATH and OUTPUT_DIR when argv is None
    for builder in (
        audio_converter_builder,
        document_converter_builder,
        image_converter_builder,
        sheet_converter_builder,
        slide_converter_builder,
        video_converter_builder,
    ):
        try:
            builder.main()
        except (SystemExit, KeyboardInterrupt):
            # Allow explicit exits/interrupts to propagate
            raise
        except (RuntimeError, OSError, ImportError, ValueError):
            # Known failure modes when running builders (log and continue)
            traceback.print_exc()

    # Ensure __init__.py files are present in converters packages so imports work reliably
    package_dir = Path(__file__).resolve().parent
    _ensure_init_files(package_dir)

    # discover generated converter modules and register converter instances
    converters_root = package_dir / "converters"
    _discover_and_register(converters_root, registry, package_dir)

    # create engine with registry and manifest
    engine = ConversionEngine(registry, manifest)

    window = MainWindow(engine, manifest)
    window.show()

    sys.exit(app.exec())
