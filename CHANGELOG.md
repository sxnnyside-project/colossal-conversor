# Changelog

## [4.0.0] – Unreleased
- UI/UX complete overhaul: new PySide6-based interface with Material-like theme (theme.qss) and improved layout.
- Added app icon and dedicated open-file SVG for better UX.
- Multi-file conversion support (select multiple inputs; directory output for multi-file conversions).
- Background execution of conversions (threaded) and aggregated progress display.
- Improvements to converter discovery/registration to parse metadata from generated classes/docstrings and module source.
- Hardened engine and BaseConverter.supports() to avoid AttributeError on partially-generated converters.
- Better error handling using ConversionError and user-facing dialogs.
- Minor bug fixes and refactors across registry, app initialization and UI wiring.
