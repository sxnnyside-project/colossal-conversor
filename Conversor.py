import os

import openpyxl
import pandas as pd

# Directorio Excel
# Usa '/' en vez de '\'
dir_excel = 'C:/Ruta/Absoluta/De/Origen'
# Directorio CSV
dir_csv = 'C:/Ruta/Absoluta/De/Destino'
archivo_excel = [archivo for archivo in os.listdir(dir_excel) if archivo.endswith(".xlsx")]
for archivo in archivo_excel:
    df = pd.read_excel(os.path.join(dir_excel,archivo))
    nombre_original = os.path.splitext(archivo)[0]
    archivo_csv = nombre_original + ".csv"
    df.to_csv(os.path.join(dir_csv,archivo_csv), index=False, encoding='utf-8-sig')
    print(archivo_csv)