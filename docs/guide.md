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

## Filas y columnas

Posiciones 1-based; los rangos en `delete_*`/`hide_*` son inclusivos.

```python
ws.insert_rows(3, number=2)   # inserta 2 filas antes de la fila 3
ws.insert_cols(2)             # inserta 1 columna antes de la columna 2
ws.delete_rows(5, 8)          # elimina filas 5..8
ws.delete_cols(3)             # elimina la columna 3
ws.add_rows(100)             # agrega 100 filas al final
ws.resize_cols(1, 3, 120)     # ancho 120px para columnas 1..3
ws.hide_rows(2, 4)            # oculta filas 2..4
ws.unhide_rows(2, 4)
```

## Búsqueda

```python
celda = ws.find("Total")
if celda:
    print(celda.row, celda.col, celda.value)
```

## Notas, named ranges y protected ranges

```python
ws.update_note("B2", "revisar")
ws.get_note("B2")            # "revisar"
ws.clear_note("B2")

ws.define_named_range("Ventas", "A1:B100")
mgr.list_named_ranges()      # a nivel documento
mgr.delete_named_range(named_range_id)

ws.add_protected_range("A1:A10", description="solo lectura")
ws.list_protected_ranges()
ws.delete_protected_range(protected_range_id)
```

## Orden, filtro, merge y color de pestaña

```python
# Ordenar un rango por una o más columnas (1-based): (columna, "asc"|"desc")
ws.sort_range("A2:C100", (1, "asc"), (3, "desc"))

# Filtro básico sobre un rango (o toda la hoja si se omite)
ws.set_basic_filter("A1:C100")
ws.clear_basic_filter()

# Deshacer una combinación de celdas
ws.unmerge("A1:B2")

# Color de la pestaña
from gspreadmanager import Color
ws.set_tab_color(Color.from_hex("#D9EAD3"))
ws.clear_tab_color()
```

## Exportación

```python
from gspreadmanager import ExportFormat

pdf = mgr.export()                     # PDF por defecto; devuelve bytes
csv = mgr.export(ExportFormat.CSV)     # también TSV, EXCEL, ODS, HTML
with open("doc.pdf", "wb") as f:
    f.write(pdf)
```

## Integración con DataFrames (pandas o polars)

```python
df = ws.read_dataframe()
ws.write_dataframe(df)

# Opciones de lectura
df = ws.read_dataframe(
    drop_empty_rows=True,    # descarta filas totalmente vacías
    drop_empty_cols=True,    # descarta columnas totalmente vacías
    index_col="id",          # usa una columna como índice (solo pandas)
)

# Opciones de escritura
ws.write_dataframe(df, start_cell="B2", include_index=True, clear=False)
```

El motor de DataFrame es elegible al crear el gestor (por defecto **pandas**):

```python
mgr = SheetManager("MiDoc", "creds.json", dataframe_backend="polars")
df = mgr.worksheet("Hoja1").read_dataframe()   # devuelve un polars.DataFrame
```

Instalá el backend que uses: `pip install GSpreadManager[pandas]` o
`pip install GSpreadManager[polars]`. polars no tiene índice de filas, así que `index_col` /
`include_index` se ignoran con ese backend.

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

## Caché de lecturas

Para apps que releen mucho, activá una caché de lecturas con `cache=True`. Memoiza las
lecturas (`read`, `read_dataframe`, `read_as`, `read_range`, metadata) y **se invalida sola con
cada escritura propia**, así que nunca ves un valor obsoleto respecto de tus cambios:

```python
mgr = SheetManager("Mi Hoja", "creds.json", cache=True)
ws = mgr.worksheet("Hoja1")
ws.read()        # lee de la API
ws.read()        # sirve de la caché (sin llamada)
ws.append([["x"]])  # invalida la caché del documento
ws.read()        # vuelve a leer de la API
```

No detecta cambios hechos por **otros** procesos: si otra persona edita la hoja, forzá el
refresco con `mgr.clear_cache()`. Por eso la caché es opt-in (por defecto está apagada).

## Modelos de fila tipados (dataclasses)

Leé y escribí filas como objetos tipados, con coerción de tipos (int/float/bool/date) y
validación. El encabezado de la hoja mapea a los campos del modelo por nombre (o por
`field(metadata={"column": ...})`):

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

@dataclass
class Persona:
    nombre: str
    edad: int
    activo: bool
    email: Optional[str] = None       # columna opcional: "" -> None
    alta: date = field(metadata={"column": "Fecha de alta"})

ws = mgr.worksheet("Personas")
personas = ws.read_as(Persona)               # -> list[Persona], con tipos convertidos
ws.append_models([Persona("Ana", 30, True)]) # agrega filas al final
ws.write_models(personas)                     # reescribe la hoja desde A1 (con encabezado)
```

Los booleanos se parsean de `TRUE`/`FALSE`/`1`/`0`/`sí`/`no`; las fechas con
`fromisoformat`. Un valor que no encaja con el tipo del campo lanza `SchemaError`. Los campos
con valor por defecto toleran que falte su columna en la hoja.

## Testear sin red (backend en memoria)

`gspreadmanager.testing` trae un backend en memoria que implementa los mismos puertos que el
adaptador de gspread. Tu código usa `SheetManager` igual que en producción, pero sin tocar la
API de Google:

```python
from gspreadmanager.testing import InMemoryBackend

backend = InMemoryBackend()
backend.add_spreadsheet("MiDoc", {"Hoja1": [["nombre", "email"], ["Ana", "ana@x.com"]]})

mgr = backend.manager("MiDoc")          # un SheetManager cableado al fake
ws = mgr.worksheet("Hoja1")
ws.append([["Bob", "bob@x.com"]])
assert ws.read(output_format="dict")[-1] == {"nombre": "Bob", "email": "bob@x.com"}
```

Los valores hacen round-trip y las operaciones estructurales (insertar/eliminar filas, notas,
named/protected ranges) se aplican sobre la grilla. El formato, la validación y el orden/filtro
se **registran** en `spreadsheet.requests` para poder afirmarlos en los tests, pero no alteran la
grilla. Para inyectar el fake en tu propia construcción del gestor, pasá el cliente directamente:

```python
mgr = SheetManager("MiDoc", sheets_client=backend.client)
```
