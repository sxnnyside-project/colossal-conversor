# Colossal Conversor — Guía de Usuario

<p align="center">
  <em>Todo lo necesario para instalar, usar y resolver problemas de Colossal Conversor en el día a día.</em>
</p>

<p align="center">
  <sub>Idiomas: <a href="../en/README.md">English</a> · <a href="../es/README.md">Español</a> · <a href="../fr/README.md">Français</a> · <a href="../ja/README.md">日本語</a> · <a href="../pt/README.md">Português</a> · <a href="../zh/README.md">中文</a></sub>
</p>

---

## 1. ¿Qué es Colossal Conversor?

Colossal Conversor es una aplicación de escritorio offline para convertir
archivos de audio, video, imagen, documentos, hojas de cálculo y
presentaciones. Todo se ejecuta localmente a través de un núcleo de
ejecución nativo en C++20 — no hay subida a la nube, ni cuenta, ni
dependencia de red para la conversión en sí. Consulta el [README](../../../README.md)
principal para la descripción técnica completa.

Esta guía cubre el uso real de la aplicación en el día a día: instalación,
tu primera conversión, trabajo con lotes y pipelines, y cómo recuperarte
cuando algo falla.

## 2. Plataformas Compatibles

Colossal Conversor está pensado para **macOS, Linux y Windows**. El
supervisor de procesos nativo tiene un backend dedicado por plataforma, de
modo que la creación de procesos, la captura de salida, la cancelación y la
limpieza se comportan igual en todas partes.

| Plataforma | Estado |
|---|---|
| macOS | Verificada — compilada, probada y usada en el desarrollo diario |
| Linux | Implementada (comparte el backend de macOS); aún no verificada en un runner Linux |
| Windows | Implementada contra las APIs de proceso de Windows; aún no verificada en un runner Windows |

"Implementada pero aún no verificada" significa que el código existe y
sigue los contratos correctos de la plataforma, pero nadie ha confirmado
todavía que una conversión real funcione en esa plataforma. Esto se
actualizará a medida que se verifique — consulta la sección de
compatibilidad de plataformas del README principal para el estado actual, y
[CONTRIBUTING.md](../../../CONTRIBUTING.md) si quieres ayudar a verificar Linux o Windows.

## 3. Instalación

Instalar Colossal Conversor es independiente de instalar las herramientas
externas que usa para algunas conversiones (ver la sección de Dependencias
Externas más abajo).

### macOS / Linux

```bash
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor
just install
just dev
```

### Windows

```powershell
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor
just install
just dev
```

`just install` sincroniza las dependencias de Python y compila la extensión
nativa. `just dev` lanza la aplicación. Si no tienes `just`, consulta sus
[instrucciones de instalación](https://github.com/casey/just#installation) —
o ejecuta el equivalente `uv sync --all-groups` seguido de la compilación
nativa con CMake descrita en el README principal.

## 4. Dependencias Externas

Algunas categorías de conversión llaman a una herramienta externa; otras se
ejecutan completamente en el proceso y no necesitan nada adicional.

| Herramienta | Necesaria para |
|---|---|
| FFmpeg | Conversiones de audio y video |
| LibreOffice | Conversiones de documentos, hojas de cálculo y presentaciones |
| Poppler (`pdftoppm`) | Renderizado de páginas de documento a imagen |
| Pandoc | Conversiones markdown ↔ documento |
| ImageMagick | Conversiones de imagen distintas de BMP/PPM/TGA (que se ejecutan de forma nativa, sin herramienta) |

Para comprobar qué está ya disponible:

```bash
just verify-tools
```

Para instalar lo que falte:

- **macOS**: `bash tools/macos_install_deps.sh` (Homebrew)
- **Linux**: `bash tools/linux_install_deps.sh` (apt, dnf o pacman — detectado automáticamente)
- **Windows**: ejecuta `tools/windows_install_deps.ps1` en PowerShell (winget, o Chocolatey si ya está instalado)

Instalar estas herramientas **no** garantiza por sí solo que toda
conversión funcione — hace disponible el motor correspondiente. La
aplicación detecta cada herramienta en tiempo de ejecución y solo ofrece
conversiones que realmente puede ejecutar.

## 5. Primera Conversión

1. Abre la aplicación (`just dev`).
2. Haz clic en **Select File(s)** o arrastra un archivo al área de entrada.
3. Colossal Conversor detecta el formato del archivo y muestra solo los
   formatos de destino que realmente puede producir, agrupados por
   categoría.
4. Haz clic en un formato de destino.
5. Haz clic en **Save As...** para elegir (o confirmar) el destino, si
   quieres algo distinto del predeterminado.
6. Haz clic en **Convert** (o pulsa <kbd>Enter</kbd>).

Al terminar, un cuadro de diálogo informa cuántos archivos se produjeron,
con botones para abrir el resultado o mostrarlo en tu gestor de archivos.

## 6. Múltiples Archivos

Haz clic en **Select File(s)** y elige más de un archivo, o arrastra varios
a la vez. Colossal Conversor muestra solo los formatos de salida comunes a
todas las entradas seleccionadas. Elige una **carpeta** de destino (no un
único archivo) mediante **Save As...**, y luego **Convert** — cada entrada
produce su propia salida en esa carpeta.

## 7. Conversiones de Salida Múltiple

Algunas conversiones producen más de un archivo a partir de una sola
entrada — por ejemplo, renderizar cada página de un PDF como una imagen
independiente. Esto se detecta automáticamente según el par de formatos
elegido; el destino que elijas se convierte en una carpeta que contiene
todas las páginas producidas, y el cuadro de diálogo final informa el
número real de archivos generados.

## 8. Pipelines

Algunas conversiones no pueden ocurrir en un solo paso y se dividen
automáticamente en etapas internas — por ejemplo, una presentación
convertida a imagen pasa primero por un PDF intermedio. No necesitas
configurar nada: elige tu entrada y formato de destino como siempre, y la
barra de progreso muestra qué etapa se está ejecutando. Los archivos
intermedios se limpian automáticamente al terminar el pipeline (o si falla
o se cancela).

## 9. Elegir un Formato de Salida

La cuadrícula de formatos solo muestra destinos que Colossal Conversor
puede producir realmente a partir de tu entrada actual — no anuncia
conversiones que no puede ejecutar. Al seleccionar un formato aparece una
nota de fidelidad (por ejemplo "alta", "media", "diseño") que describe
cuánto conserva la salida respecto al original — útil al convertir entre
formatos con capacidades distintas (por ejemplo, un documento con estilos a
texto plano).

## 10. Selección de Destino

**Save As...** te permite elegir dónde va la salida. Para una conversión de
salida única, elige una ruta de archivo; para un lote o una conversión de
salida múltiple, elige una carpeta. Si no eliges explícitamente, la
aplicación propone un destino razonable junto al archivo de entrada.

## 11. Cancelación

Haz clic en **Cancel** mientras una conversión está en curso para
detenerla. Esto termina realmente el proceso subyacente (no solo el estado
de la interfaz) — ninguna salida parcial se reporta como resultado exitoso,
y la barra de estado muestra "Conversion cancelled", distinto tanto de un
éxito como de un fallo. Puedes iniciar una nueva conversión inmediatamente
después.

## 12. Errores y Recuperación

Si una conversión falla, un cuadro de diálogo explica qué pasó en lenguaje
claro, con un botón **Show Details...** para la salida técnica subyacente
(solo se muestra si lo pides). La aplicación no se cierra ni se bloquea
ante una conversión fallida — cierra el diálogo e inténtalo de nuevo,
ajustando la entrada, el formato de destino o el destino según sea
necesario.

## 13. Dependencias Faltantes

Si una conversión necesita una herramienta que no está instalada, el
mensaje de error lo indica explícitamente y nombra la herramienta — no se
confundirá con un fallo genérico. Ejecuta `just verify-tools` para ver el
panorama completo, y consulta la sección de Dependencias Externas más
arriba para instalar lo que falte.

## 14. Formatos Compatibles

La cuadrícula de formatos dentro de la aplicación es la lista autoritativa
y en vivo — se genera desde el mismo catálogo que usa el motor de
conversión, así que nunca puede anunciar algo que la versión actual no
puede hacer realmente. En términos generales, Colossal Conversor admite:

- **Audio**: formatos comunes como MP3, WAV, FLAC, AAC, OGG y otros.
- **Video**: formatos comunes como MP4, MKV, MOV, AVI, WebM y otros.
- **Imagen**: formatos comunes como PNG, JPEG, WebP, BMP, TIFF, GIF y otros.
- **Documento**: DOC/DOCX, ODT, RTF, TXT, PDF, Markdown, HTML, EPUB.
- **Hoja de Cálculo**: XLS/XLSX, ODS, CSV, TSV.
- **Presentación**: PPTX/PPT, ODP.

Selecciona un archivo de entrada en la aplicación para ver la lista exacta
y actual de destinos para ese archivo en concreto.

## 15. Solución de Problemas

**Una conversión que esperaba que funcionara no aparece.** La lista de
formatos de destino se genera a partir del formato detectado de tu entrada
específica — verifica que la entrada se detectó correctamente (se muestra
junto al nombre del archivo) y que la conversión que quieres está realmente
disponible para ese par de formatos.

**Error de "dependencia faltante".** Ejecuta `just verify-tools` e instala
la herramienta indicada (ver Dependencias Externas / Dependencias Faltantes
más arriba).

**La conversión falla inmediatamente.** Revisa **Show Details...** en el
cuadro de diálogo de error. Causas comunes: un archivo de entrada corrupto
o ilegible, o un formato que la entrada detectada en realidad no cumple
(por ejemplo, un archivo renombrado con la extensión equivocada).

**Cancel no parece hacer nada visualmente.** En conversiones muy cortas, la
operación puede terminar antes de que Cancel surta efecto — esto es
esperado, no un error; el resultado será un éxito o fallo normal, no una
interfaz atascada.

**La ruta de destino no es válida.** Asegúrate de que la carpeta existe y
tienes permiso de escritura sobre ella; para una salida de archivo único,
asegúrate de que la carpeta contenedora existe.

**¿Sigues atascado?** Abre un issue — ver [SUPPORT.md](../../../SUPPORT.md).

---

<p align="center">
  <sub>Parte de la documentación de <a href="../../../README.md">Colossal Conversor</a> — A Sxnnyside Project Release</sub>
</p>
