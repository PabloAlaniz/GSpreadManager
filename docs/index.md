# GSpreadManager

Un wrapper de Python para facilitar la interacción con Google Sheets. Ofrece una interfaz
simple y *pythonic* para operaciones comunes: lectura, escritura, actualización, búsqueda y
gestión de hojas.

## Características

- 🔐 Autenticación con cuentas de servicio de Google
- 📖 Lectura flexible (listas, diccionarios, pandas DataFrame)
- ✏️ Escritura y actualización de celdas, filas y rangos
- 🗂️ Gestión de hojas: crear, eliminar y limpiar pestañas
- 🐼 Integración con pandas (`to_gsheet` / `from_gsheet`)
- ♻️ Reintentos automáticos con backoff ante límites de cuota
- 🧩 Context manager (`with ... as conn:`)
- 🐍 Type hints (PEP 561) y docstrings completas

## Instalación

```bash
pip install GSpreadManager

# Con soporte pandas (opcional)
pip install "GSpreadManager[pandas]"
```

## Ejemplo rápido

```python
from gspreadmanager import GoogleSheetConector

conector = GoogleSheetConector(
    doc_name="Mi Hoja de Cálculo",
    json_google_file="credenciales.json",
    sheet_name="Hoja1",
)

# Leer datos como lista de diccionarios
datos = conector.read_sheet_data(output_format="dict")

# Actualizar una celda
conector.update_cell(row_index=2, col_index=1, value="María")
```

Seguí con la [Guía de uso](guide.md) o la [Referencia de API](api.md).
