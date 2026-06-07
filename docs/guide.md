# Guía de uso

## Conexión

```python
from gspreadmanager import GoogleSheetConector

conector = GoogleSheetConector(
    doc_name="Mi Hoja de Cálculo",
    json_google_file="credenciales.json",
    sheet_name="Hoja1",          # opcional: primera hoja por defecto
    max_retries=3,               # reintentos ante 429/500/503
    retry_backoff=1.0,           # backoff exponencial base (segundos)
)
```

## Lectura

```python
# Lista de listas
datos = conector.read_sheet_data(output_format="list")

# Lista de diccionarios (primera fila = encabezados)
datos = conector.read_sheet_data(output_format="dict")

# pandas DataFrame (requiere el extra [pandas])
df = conector.read_sheet_data(output_format="pandas")

# Rango específico
rango = conector.spreadsheet_read_range("Hoja1", 1, 10, "A", "D")
```

## Escritura y actualización

```python
conector.spreadsheet_append([["Ana", "ana@example.com"]])
conector.update_cell(row_index=3, col_index=2, value="Nuevo Valor")
conector.update_row(row_index=5, data=["X", "Y", "Z"], start_column=3)

conector.batch_update([
    {"range": "Hoja1!A1:B1", "values": [["Mes", "Total"]]},
])
```

## Gestión de hojas

```python
conector.create_sheet("Reporte 2026", rows=500, cols=10)
conector.delete_sheet("Borrador")
conector.clear_range("A1:C10")        # un rango
conector.clear_range()                # toda la hoja
```

## Búsqueda

```python
celda = conector.find_cell("Total")
if celda:
    print(celda.row, celda.col, celda.value)
```

## Integración con pandas

```python
df = conector.from_gsheet()
conector.to_gsheet(df, tab_name="Resultados")
```

## Formato de celdas

Modelo tipado propio (sin dependencias externas):

```python
from gspreadmanager import CellFormat, TextFormat, Color, NumberFormat

# Encabezado en negrita con fondo verde claro
conector.format_header()  # primera fila, atajo

# Formato arbitrario sobre un rango
fmt = CellFormat(
    text_format=TextFormat(bold=True, foreground_color=Color.from_hex("#FFFFFF")),
    background_color=Color.from_hex("#0B5394"),
    horizontal_alignment="CENTER",
)
conector.format_range("A1:D1", fmt)

# Atajos
conector.set_background("A2:A100", Color.from_hex("#FFF2CC"))
conector.set_text_format("B2:B100", bold=True, font_size=11)
conector.set_number_format("C2:C100", "#,##0.00", number_type="CURRENCY")

# Estructura
conector.freeze(rows=1)            # congelar encabezado
conector.merge("A1:D1")            # combinar celdas
```

## Validación de datos

```python
conector.add_dropdown("E2:E100", ["Pendiente", "En curso", "Hecho"])
conector.add_checkbox("F2:F100")
```

## Formato condicional

```python
from gspreadmanager import CellFormat, Color

# Pintar de rojo los valores negativos
rojo = CellFormat(background_color=Color.from_hex("#F4CCCC"))
conector.add_conditional_format("C2:C100", "NUMBER_LESS", [0], rojo)
```

## Manejo de errores

Las operaciones reintentan automáticamente ante errores transitorios (HTTP 429/500/503).
La librería expone excepciones propias:

```python
from gspreadmanager import GSpreadManagerError, InsertError

try:
    conector.spreadsheet_insert("Mi Hoja", "Hoja1", [["A", "B"]])
except InsertError as e:
    print(f"No se pudo insertar: {e}")
```

## Context manager

```python
with GoogleSheetConector("Mi Hoja", "creds.json") as conector:
    df = conector.from_gsheet()
```

!!! warning "Cambio en v0.3.0"
    Los métodos `update_cell`, `update_row`, `spreadsheet_read_range` y
    `get_row_with_empty_in_column` ya no reciben `sheet` como primer parámetro; usan la hoja
    activa del conector. `sheet` sigue aceptándose como argumento opcional final, pero emite
    `DeprecationWarning`.
