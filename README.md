# Colossal Conversor

Colossal Conversor es una aplicación basada en Python que te permite convertir varios formatos de archivos usando una interfaz gráfica de usuario (GUI) construida con Tkinter.

![Colossal Conversor](Colossal%20Conversor.png)

## Características

- Convertir archivos de Excel a CSV
- Convertir documentos de Word a PDF
- Convertir imágenes a diferentes formatos (JPG, PNG)
- Convertir archivos TXT a Markdown

## Requisitos

- Python 3.x
- Tkinter
- pandas
- Pillow
- docx2pdf
- markdown

## Instalación

1. Clona el repositorio:
    ```sh
    git clone https://github.com/yourusername/colossal-conversor.git
    cd colossal-conversor
    ```

2. Instala los paquetes requeridos:
    ```sh
    pip install pandas pillow docx2pdf markdown
    ```

## Uso

1. Ejecuta la aplicación:
    ```sh
    python Conversor.py
    ```

2. Usa la GUI para seleccionar el archivo o carpeta de origen y la carpeta de destino.

3. Elige el tipo de conversión del menú desplegable.

4. Haz clic en el botón \`Convertir\` para iniciar el proceso de conversión.

## Funciones de Conversión

- `excel_to_csv(source, destination)`: Convierte un archivo de Excel a CSV.
- `word_to_pdf(source, destination)`: Convierte un documento de Word a PDF.
- `image_convert(source, destination, ext)`: Convierte una imagen al formato especificado (JPG, PNG).
- `txt_to_markdown(source, destination)`: Convierte un archivo TXT a Markdown.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT.

## Actualizaciones

- 3.0.0
    - Versión inicial
  
Se ha implementado la funcionalidad básica de la aplicación con interfaces gráficas de usuario (GUI) para cada tipo de conversión.

Este archivo se creo originalmente como README.txt y se convirtió a Markdown usando la aplicación Colossal Conversor.