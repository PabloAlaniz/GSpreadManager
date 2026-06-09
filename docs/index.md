# GSpreadManager

Un wrapper de Python para facilitar la interacción con Google Sheets. Ofrece una interfaz
simple y *pythonic* para operaciones comunes: lectura, escritura, actualización, búsqueda y
gestión de hojas.

## Características

- 🔐 Autenticación con cuentas de servicio de Google
- 📖 Lectura flexible (listas, diccionarios, pandas DataFrame)
- ✏️ Escritura y actualización de celdas, filas y rangos
- 🗂️ Gestión de hojas: crear, eliminar y limpiar pestañas
- 🐼 Integración con pandas (`read_dataframe` / `write_dataframe`)
- ♻️ Reintentos automáticos con backoff ante límites de cuota
- 🧩 Context manager (`with ... as mgr:`)
- 🧱 Arquitectura por capas (dominio / aplicación / infraestructura) y type hints (PEP 561)

## Instalación

```bash
pip install GSpreadManager

# Con soporte pandas (opcional)
pip install "GSpreadManager[pandas]"
```

## Ejemplo rápido

```python
from gspreadmanager import SheetManager

mgr = SheetManager("Mi Hoja de Cálculo", json_google_file="credenciales.json")
ws = mgr.worksheet("Hoja1")  # handle inmutable a la pestaña

# Leer datos como lista de diccionarios
datos = ws.read(output_format="dict")

# Actualizar una celda
ws.update_cell(2, 1, "María")
```

Seguí con la [Guía de uso](guide.md) o la [Referencia de API](api.md).
