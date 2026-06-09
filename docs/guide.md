# Guía de uso

El punto de entrada es `SheetManager` (un documento). `mgr.worksheet(nombre)` devuelve un
`WorksheetContext`: un handle **inmutable** a una pestaña. No hay "hoja activa" global; cada
handle es independiente.

## Conexión

```python
from gspreadmanager import SheetManager

mgr = SheetManager(
    "Mi Hoja de Cálculo",
    json_google_file="credenciales.json",
    max_retries=3,        # reintentos ante 429/500/503
    retry_backoff=1.0,    # backoff exponencial base (segundos)
)

ws = mgr.worksheet("Hoja1")   # handle a la pestaña (la primera si se omite el nombre)
```

También se puede abrir por **key** (id de Drive) o por **URL**:

```python
mgr = SheetManager.open_by_key("1AbC...xyz", json_google_file="credenciales.json")
mgr = SheetManager.open_by_url("https://docs.google.com/spreadsheets/d/1AbC...xyz/edit",
                               json_google_file="credenciales.json")
```

## Lectura

```python
# Lista de listas
datos = ws.read(output_format="list")

# Lista de diccionarios (primera fila = encabezados)
datos = ws.read(output_format="dict")

# pandas DataFrame (requiere el extra [pandas])
df = ws.read(output_format="pandas")   # o ws.read_dataframe()

# Rango específico por índices de fila/columna
rango = ws.read_range(1, 10, "A", "D")

# Con inferencia de tipos ("3" -> 3, "1.5" -> 1.5; preserva "007")
ws.read(output_format="dict", numericise=True)
```

## Escritura y actualización

```python
ws.append([["Ana", "ana@example.com"]])
ws.update_cell(3, 2, "Nuevo Valor")
ws.update_row(5, ["X", "Y", "Z"], start_column=3)
ws.insert([["A", "B"]], fila=10)        # inserta en una fila concreta (o al final)

ws.batch_update([
    {"range": "Hoja1!A1:B1", "values": [["Mes", "Total"]]},
])
```

## Gestión de hojas

```python
nueva = mgr.create_sheet("Reporte 2026", rows=500, cols=10)   # devuelve un WorksheetContext
mgr.delete_sheet("Borrador")
ws.clear("A1:C10")    # un rango
ws.clear()            # toda la hoja
```

## Búsqueda

```python
celda = ws.find("Total")
if celda:
    print(celda.row, celda.col, celda.value)
```

## Integración con pandas

```python
df = ws.read_dataframe()
ws.write_dataframe(df)
```

## Formato de celdas

Modelo tipado propio (sin dependencias externas):

```python
from gspreadmanager import CellFormat, TextFormat, Color

# Encabezado en negrita con fondo verde claro (atajo, primera fila)
ws.format_header()

# Formato arbitrario sobre un rango
fmt = CellFormat(
    text_format=TextFormat(bold=True, foreground_color=Color.from_hex("#FFFFFF")),
    background_color=Color.from_hex("#0B5394"),
    horizontal_alignment="CENTER",
)
ws.format_range("A1:D1", fmt)

# Atajos
ws.set_background("A2:A100", Color.from_hex("#FFF2CC"))
ws.set_text_format("B2:B100", bold=True, font_size=11)
ws.set_number_format("C2:C100", "#,##0.00", number_type="CURRENCY")

# Estructura
ws.freeze(rows=1)        # congelar encabezado
ws.merge("A1:D1")        # combinar celdas
```

## Validación de datos

```python
ws.add_dropdown("E2:E100", ["Pendiente", "En curso", "Hecho"])
ws.add_checkbox("F2:F100")
```

## Formato condicional

```python
from gspreadmanager import CellFormat, Color

# Pintar de rojo los valores negativos
rojo = CellFormat(background_color=Color.from_hex("#F4CCCC"))
ws.add_conditional_format("C2:C100", "NUMBER_LESS", [0], rojo)
```

## Operaciones a nivel documento

```python
# Crear, copiar, listar y borrar documentos (vía Drive)
nuevo = mgr.create_spreadsheet("Reporte mensual")
copia = mgr.copy_spreadsheet(nuevo.id, title="Reporte (copia)")
docs = mgr.list_spreadsheets(title="Reporte")
mgr.delete_spreadsheet(copia.id)
```

## Compartir y permisos

```python
mgr.share("alguien@example.com", role="writer")         # editor
mgr.share("", perm_type="anyone", role="reader")         # cualquiera con el enlace
permisos = mgr.list_permissions()
mgr.remove_permission("alguien@example.com")
```

## Manejo de errores

Las operaciones reintentan automáticamente ante errores transitorios (HTTP 429/500/503).
La librería expone excepciones propias:

```python
from gspreadmanager import InsertError

try:
    ws.insert([["A", "B"]])
except InsertError as e:
    print(f"No se pudo insertar: {e}")
```

## Context manager

```python
with SheetManager("Mi Hoja", "creds.json") as mgr:
    df = mgr.worksheet("Hoja1").read_dataframe()
```
