from pathlib import Path
from colossal.core.format_loader import load_format_manifest

# Ruta relativa: resources/format_manifest.json junto a este archivo
manifest_path = Path(__file__).resolve().parent / "resources" / "format_manifest.json"

manifest = load_format_manifest(manifest_path)

png = manifest.get_format("png")

print(png.label)
print(png.lossy)
