import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import markdown
import pandas as pd
from PIL import Image
from docx2pdf import convert


# Funciones de conversión
def excel_to_csv(source, destination):
    df = pd.read_excel(source)
    new_file = os.path.join(destination, os.path.splitext(os.path.basename(source))[0] + ".csv")
    df.to_csv(new_file, index=False, encoding='utf-8-sig')
    return new_file


def word_to_pdf(source, destination):
    convert(source, destination)
    return os.path.join(destination, os.path.basename(source).replace('.docx', '.pdf'))


def image_convert(source, destination, ext):
    img = Image.open(source)
    new_file = os.path.join(destination, os.path.splitext(os.path.basename(source))[0] + f".{ext}")
    img.save(new_file)
    return new_file


def txt_to_markdown(source, destination):
    with open(source, "r", encoding="utf-8") as file:
        content = file.read()
    new_file = os.path.join(destination, os.path.splitext(os.path.basename(source))[0] + ".md")
    with open(new_file, "w", encoding="utf-8") as file:
        file.write(markdown.markdown(content))
    return new_file

# Función para seleccionar la carpeta/archivo de origen
def select_source():
    if file_var.get():
        file_path = filedialog.askopenfilename()
        entry_source.delete(0, tk.END)
        entry_source.insert(0, file_path)
    else:
        folder_path = filedialog.askdirectory()
        entry_source.delete(0, tk.END)
        entry_source.insert(0, folder_path)

# Función para manejar la conversión
def start_conversion():
    source = entry_source.get()
    destination = entry_dest.get()
    conv_type = conversion_var.get()
    single_file = file_var.get()

    if not source or not destination:
        messagebox.showerror("Error", "Selecciona ambas carpetas.")
        return

    if single_file:
        files = [source]
    else:
        files = [os.path.join(source, f) for f in os.listdir(source)]

    for file in files:
        try:
            ext = os.path.splitext(file)[1].lower()
            if conv_type == "Excel to CSV" and ext in [".xlsx", ".xls"]:
                excel_to_csv(file, destination)
            elif conv_type == "Word to PDF" and ext == ".docx":
                word_to_pdf(file, destination)
            elif conv_type.startswith("Image to"):
                new_ext = conv_type.split(" ")[-1].lower()
                image_convert(file, destination, new_ext)
            elif conv_type == "TXT to Markdown" and ext == ".txt":
                txt_to_markdown(file, destination)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo convertir {file}: {e}")

    messagebox.showinfo("Completado", "Conversión finalizada.")

# Interfaz con Tkinter
root = tk.Tk()
root.title("Colossal Conversor")
root.iconbitmap("Colossal Conversor.ico")

frame = ttk.Frame(root, padding="10 10 10 10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Colossal Conversor", font=("Helvetica", 24)).grid(row=0, column=0, columnspan=3, pady=10)

ttk.Label(frame, text="Carpeta/Archivo de Origen:").grid(row=1, column=0, sticky=tk.W)
entry_source = ttk.Entry(frame, width=50)
entry_source.grid(row=1, column=1, padx=5)
ttk.Button(frame, text="Seleccionar", command=select_source).grid(row=1, column=2, padx=5)

ttk.Label(frame, text="Carpeta de Destino:").grid(row=2, column=0, sticky=tk.W)
entry_dest = ttk.Entry(frame, width=50)
entry_dest.grid(row=2, column=1, padx=5)
ttk.Button(frame, text="Seleccionar", command=lambda: entry_dest.insert(0, filedialog.askdirectory())).grid(row=2, column=2, padx=5)

ttk.Separator(frame, orient='horizontal').grid(row=3, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))

conversion_var = tk.StringVar(value="Excel to CSV")
ttk.Label(frame, text="Tipo de Conversión:").grid(row=4, column=0, sticky=tk.W)
options = ["Excel to CSV", "Word to PDF", "Image to JPG", "Image to PNG", "TXT to Markdown"]
option_menu = ttk.OptionMenu(frame, conversion_var, options[0], *options)
option_menu.grid(row=4, column=1, padx=5)
file_var = tk.BooleanVar()
ttk.Checkbutton(frame, text="Convertir solo un archivo", variable=file_var).grid(row=5, column=1, pady=5)

ttk.Button(frame, text="Convertir", command=start_conversion).grid(row=6, column=1, pady=10)

root.mainloop()