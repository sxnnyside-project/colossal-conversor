# Colossal Conversor

Colossal Conversor es una aplicación en Python para convertir múltiples formatos de archivo usando una interfaz gráfica moderna (PySide6). Se diseñó con modularidad para soportar convertidores auto-generados, un motor de ejecución robusto y una experiencia de usuario clara.

![Colossal Conversor](Colossal%20Conversor.png)

## Características principales

- Interfaz gráfica moderna (PySide6) con tema Material-like (QSS) y badges informativos.
- Conversión de archivos por categorías: audio, documento, imagen, hoja (sheets), slide y video.
- Soporte para conversión de uno o varios archivos (multi-file): si la conversión produce múltiples archivos se pedirá carpeta de salida.
- Ejecución de conversiones en background (hilos) para no bloquear la UI, con barra de progreso agregada para tareas múltiples.
- Hints UX: muestra fidelity, warnings y limitations por conversión según los JSON de manifiesto.
- Generación e integración dinámica de convertidores (builders) y registro automático.
- Robustecimiento del motor: validación de formatos, resolución segura de convertidores y manejo de errores con ConversionError.

## Requisitos

- Python 3.10+ (compatibilidad con las construcciones de typing usadas)
- PySide6
- Herramientas de conversión externas según convertidor (por ejemplo `ffmpeg` para video)

En el repositorio hay scripts para instalar dependencias por tipo (scripts/install_*). Por ejemplo, para multimedia puedes revisar `scripts/install_video_dependecies.sh`.

## Instalación (rápida)

Recomendado: crear un entorno virtual y usar las dependencias del proyecto.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# Instala PySide6 y otras dependencias necesarias manualmente
pip install PySide6
# instala otras dependencias que tu flujo necesite (p.ej. ffmpeg es externo y debe existir en PATH)
```

Si usas `pyproject.toml`, puedes instalar el paquete en editable mode:

```bash
pip install -e .
```

## Uso

Hay dos formas recomendadas de ejecutar la aplicación desde el árbol del proyecto:

1) Ejecutar el runner del paquete (añade `src` al PYTHONPATH):

```bash
python -c "import sys; sys.path.insert(0,'src'); from colossal.app import run_app; run_app()"
```

2) Usar el script provisto (si lo prefieres):

```bash
./scripts/run_colossal.sh
```

En la UI:
- Selecciona uno o varios archivos con el botón de la derecha (botón tipo icon grande).
- Selecciona el formato de salida desde la columna izquierda (los formatos se muestran agrupados por categoría y filtrados según disponibilidad).
- Revisa los badges (fidelity/warnings/limitations) y las notas en el panel derecho.
- Usa "Guardar como..." para escoger archivo destino o carpeta (para conversiones multi-file se requiere carpeta).
- Pulsa "Convertir" para iniciar; la operación se ejecutará en background y verás el progreso.

## Conversores y manifest

Los formatos, categorías y pistas de fidelidad/advertencias están definidos en `src/colossal/resources/formats/*.json` y se cargan en la inicialización. Los convertidores generados por los builders se colocan en `src/colossal/converters` y se registran automáticamente en el inicio.


## Desarrollo y notas técnicas

- El motor de conversiones valida formatos y busca el convertidor adecuado en un registro (`ConverterRegistry`).
- Se aplicaron mejoras para manejar convertidores auto-generados que incluyen metadatos en docstrings (por ejemplo `input_formats`, `output_formats`) — el app parsea estas anotaciones cuando falta información en la instancia.
- `BaseConverter.supports()` fue hecho defensivo para evitar AttributeError en convertidores generados incompletos.
- Conversiones se ejecutan con `ConversionEngine.submit()` que marca estados del `ConversionTask` y captura errores en `ConversionError`.

## Contribuir

- Lee `CHANGELOG.md` para ver la historia de cambios.
- Abre issues o PRs para reportar bugs o mejorar UX.

## Licencia

Este proyecto se distribuye bajo la licencia MIT (ver `LICENSE`).
