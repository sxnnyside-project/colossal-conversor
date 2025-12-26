#!/usr/bin/env bash
# Script para ejecutar la app usando el virtualenv del proyecto (.venv)
# Úsalo como comando de entrada en una Run Configuration de PyCharm (tipo "Shell script")

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PROJ_ROOT/.venv"
if [ ! -d "$VENV" ]; then
  echo "ERROR: No se encontró el virtualenv '$VENV'." >&2
  echo "Crea el venv con: python3 -m venv .venv" >&2
  exit 2
fi

# Asegurar que la librería nativa de Homebrew (libcairo) sea visible en macOS
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"

# Activate venv if available
# (no queremos usar 'source' dentro de PyCharm si se llama directamente, pero mantenerlo para uso manual)
if [ -f "$VENV/bin/activate" ]; then
  # shellcheck source=/dev/null
  . "$VENV/bin/activate"
fi

# Ejecutar el módulo principal del proyecto
exec "$VENV/bin/python3" -m colossal.main

