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

### Backend nativo (sin gspread)

Hay dos transportes intercambiables: el adaptador de **gspread** y el **cliente nativo**
propio (REST directo sobre `google-auth`). El default es `backend="auto"`: usa gspread si
está instalado (es un extra opcional: `pip install "GSpreadManager[gspread]"`) y si no, el
nativo. La API es exactamente la misma — ambos backends implementan los mismos puertos y
pasan el mismo test de contrato:

```python
mgr = SheetManager(
    "Mi Hoja de Cálculo",
    json_google_file="credenciales.json",
    backend="native",     # cliente REST propio (gspread no se importa)
    http_timeout=30.0,    # timeout por petición en segundos (default 60; None lo desactiva)
)
```

Funciona con `json_google_file`, `credentials`, `service_account_info` o `use_adc=True`
(no con `client`, que es un cliente de gspread). Ver [benchmarks](benchmarks.md) para la
comparación de rendimiento. Contexto: gspread quedó sin mantenimiento activo (ADR 0001);
el nativo pasará a ser el default explícito en la 3.0.

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

# Cómo renderiza los valores la API
ws.read(render="formula")       # devuelve "=SUM(A1:A10)" en vez del resultado
ws.read(render="unformatted")   # números crudos (sin formato de moneda/fecha)
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

# Volcar un CSV en la hoja (ruta o file-like; limpia la hoja salvo clear=False)
ws.import_csv("datos.csv")
ws.import_csv(io.StringIO("a,b\n1,2"), delimiter=",")
```

## Gestión de hojas

```python
nueva = mgr.create_sheet("Reporte 2026", rows=500, cols=10)   # devuelve un WorksheetContext
mgr.delete_sheet("Borrador")
ws.clear("A1:C10")    # un rango
ws.clear()            # toda la hoja

mgr.list_worksheets()          # [{"sheetId": ..., "title": ..., "index": ...}, ...]
ws = mgr.worksheet_by_index(0) # por posición (0-based)
ws = mgr.worksheet_by_id(123)  # por sheetId

# Copiar una pestaña a otro documento (por su key de Drive)
ws.copy_to("1AbC...keyDestino")
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

## La hoja como tabla

Con encabezado en la fila 1, la pestaña se puede operar como una tabla con clave:

```python
ws = mgr.worksheet_or_create("Clientes")   # devuelve la pestaña, creándola si falta

# Upsert por columna clave: actualiza las filas existentes y agrega las nuevas.
ws.upsert([
    {"id": "2", "nombre": "Luisa"},          # dict: solo actualiza las columnas presentes
    {"id": "9", "nombre": "Nuevo", "estado": "pendiente"},
], key="id")
# -> {"updated": 1, "appended": 1}

# También con modelos tipados (dataclasses)
ws.upsert_models([Cliente(id=2, nombre="Luisa", estado="ok")], key="id")

# Update / delete condicional: dict de igualdades o un predicado sobre la fila
ws.update_where({"estado": "pendiente"}, {"estado": "en curso"})   # -> filas afectadas
ws.delete_where(lambda fila: fila["edad"] == "")                   # -> filas borradas
```

Las escrituras grandes (`append`, `batch_update`, `upsert`) se **parten automáticamente**
en varias peticiones según `SheetManager(batch_cell_limit=...)` (50.000 celdas por defecto;
cada chunk con su propio retry y permiso del rate limiter; `None` lo desactiva).

## Hojas grandes (streaming)

Para hojas de decenas de miles de filas, los iteradores leen **de a páginas** (lectura
perezosa: una petición por página, cada una con su retry y su permiso del rate limiter):

```python
for fila in ws.iter_rows(page_size=2000):          # lista por fila
    procesar(fila)

for registro in ws.iter_records(page_size=2000):   # dict por fila (encabezado en fila 1)
    procesar(registro["email"])

for cliente in ws.iter_as(Cliente, page_size=2000):  # modelos tipados por página
    procesar(cliente)
```

Para escrituras masivas, `append`/`batch_update`/`upsert` ya se parten solos
(`batch_cell_limit`). Para DataFrames conviene `read_dataframe()` (materializa todo) o
construir incrementalmente desde `iter_records`.

## Búsqueda

```python
celda = ws.find("Total")
if celda:
    print(celda.row, celda.col, celda.value)

# Buscar y reemplazar en toda la pestaña (findReplace de la API)
resumen = ws.find_replace("2025", "2026")                       # substring, sin case
ws.find_replace("borrador", "final", match_entire_cell=True)    # celda exacta
ws.find_replace(r"v\d+", "vFinal", search_by_regex=True)        # regex (RE2)
print(resumen.get("occurrencesChanged"))
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

## Charts, pivot tables y banding

Gráficos embebidos, tablas dinámicas y bandas de color, directo desde la API v4 (terreno
donde gspread no llega y pygsheets solo a medias):

```python
# Gráfico de columnas: domain = etiquetas (eje X), series = rangos de datos
chart_id = ws.add_chart("COLUMN", "A1:A13", ["B1:B13", "C1:C13"],
                        title="Ventas 2026", anchor_cell="E2")
ws.add_chart("PIE", "A2:A6", ["B2:B6"], anchor_cell="E20")   # torta (usa la 1ª serie)
ws.delete_chart(chart_id)

# Pivot table: rows/columns son offsets 0-based del rango fuente; values, (offset, función)
ws.add_pivot_table("A1:C100", "E1", rows=[0], values=[(2, "SUM")], columns=[1])

# Bandas alternadas por fila
banded_id = ws.set_banding(
    "A1:C100",
    first_color=Color.from_hex("#FFFFFF"),
    second_color=Color.from_hex("#F3F3F3"),
    header_color=Color.from_hex("#D9EAD3"),
)
ws.delete_banding(banded_id)
```

## Developer metadata

Pares clave/valor invisibles para el usuario final, anclados al documento o a una pestaña
(útiles para versionado, sincronización o marcar hojas generadas por tu app):

```python
mgr.set_developer_metadata("owner", "data-team")       # a nivel documento
ws.set_developer_metadata("schema_version", "3")       # a nivel pestaña
mgr.list_developer_metadata()                          # documento + todas las hojas
mgr.delete_developer_metadata("schema_version")        # por clave
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

# Propiedades del documento
mgr.update_title("Reporte 2026")
mgr.update_locale("es_AR")
mgr.update_timezone("America/Argentina/Buenos_Aires")
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
La librería expone una jerarquía propia de excepciones — ninguna excepción del backend
(gspread o el cliente nativo) escapa sin traducir:

```python
from gspreadmanager import (
    ApiError,                  # error genérico de la API (con .status_code)
    GSpreadManagerError,       # base de toda la jerarquía
    InsertError,
    PermissionDeniedError,     # HTTP 403
    QuotaExceededError,        # HTTP 429 (el retry ya lo reintentó)
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
)

try:
    ws = mgr.worksheet("Hoja inexistente")
except WorksheetNotFoundError as e:
    print(f"No existe la pestaña: {e}")

try:
    ws.insert([["A", "B"]])
except QuotaExceededError:
    print("Cuota agotada incluso después de los reintentos.")
except ApiError as e:
    print(f"Error de la API (HTTP {e.status_code}): {e}")
```

## Logging

La librería no configura handlers (usa un `NullHandler`); si querés ver qué hace por dentro
(requests, reintentos, esperas del rate limiter, hits de caché), activá el logger:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("gspreadmanager").setLevel(logging.DEBUG)
```

Los reintentos ante errores transitorios se loguean en nivel `WARNING`; el detalle de caché
y rate limiting, en `DEBUG`.

## Context manager

```python
with SheetManager("Mi Hoja", "creds.json") as mgr:
    df = mgr.worksheet("Hoja1").read_dataframe()
```

## Límite de tasa (rate limiting)

Para no chocar la cuota de la API de Google (que limita las peticiones por minuto), activá un
freno **proactivo** con `rate_limit` (operaciones por segundo). Es un *token bucket*: espera
*antes* de operar si te pasarías del ritmo, en vez de reaccionar a un 429 ya ocurrido (eso lo
cubre el retry):

```python
mgr = SheetManager("Mi Hoja", "creds.json", rate_limit=1)        # ~1 op/seg sostenida
mgr = SheetManager("Mi Hoja", "creds.json",
                   rate_limit=1, rate_limit_burst=10)            # permite ráfagas de 10
```

El bucket arranca lleno (admite una ráfaga inicial de `rate_limit_burst`, por defecto
`max(1, rate_limit)`) y se recarga a `rate_limit` por segundo. El cupo se consume por
operación del facade (no por llamada HTTP), y se combina con el retry y la caché.

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

La invalidación es **selectiva**: una escritura puntual (`update_cell`, `batch_update`)
solo invalida lo que se superpone con el rango escrito; escribir en una pestaña no toca lo
cacheado de las demás. Además:

```python
mgr = SheetManager(
    "Mi Hoja", "creds.json",
    cache_ttl=30,            # las entradas expiran a los 30s (acota el staleness)
    cache_max_entries=500,   # límite de entradas con desalojo LRU
)   # pasar cualquiera de los dos activa la caché sola
```

No detecta cambios hechos por **otros** procesos: si otra persona edita la hoja, forzá el
refresco con `mgr.clear_cache()` (o usá `cache_ttl` para acotar la ventana). Por eso la
caché es opt-in (por defecto está apagada).

## Modelos de fila tipados (dataclasses o Pydantic)

Leé y escribí filas como objetos tipados, con coerción de tipos (int/float/bool/date/
Decimal/Enum/Literal) y validación. El encabezado de la hoja mapea a los campos del modelo
por nombre (o por `field(metadata={"column": ...})`):

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
`fromisoformat`; también `Decimal`, `Enum` (por valor o nombre) y `Literal`. Un valor que no
encaja con el tipo del campo lanza `SchemaError`. Los campos con valor por defecto toleran
que falte su columna en la hoja.

### Modelos Pydantic v2

Con el extra `pip install "GSpreadManager[pydantic]"`, los mismos métodos aceptan modelos
Pydantic (la validación y coerción la hace Pydantic; los errores llegan como `SchemaError`).
El nombre de columna es el `alias` del campo, o su nombre:

```python
from pydantic import BaseModel, Field

class Cliente(BaseModel):
    id: int
    nombre: str = Field(alias="nombre completo")
    activo: bool = True            # celda vacía -> default

clientes = ws.read_as(Cliente)
ws.append_models([Cliente.model_validate({"id": 9, "nombre completo": "Eva"})])
ws.upsert_models(clientes, key="id")
for c in ws.iter_as(Cliente, page_size=1000): ...
```

### Validar o crear el esquema (`ensure_schema`)

Antes de operar, asegurate de que el encabezado de la hoja coincide con el modelo:

```python
ws.ensure_schema(Cliente)
# Hoja vacía -> escribe el encabezado del modelo y devuelve {"created": True, ...}
# Coincide   -> {"created": False, "missing": [], "extra": [...toleradas...]}

try:
    ws.ensure_schema(Cliente, strict=True)   # strict: las columnas extra también fallan
except SchemaError as e:
    print(e.missing_columns, e.extra_columns)  # reporte de drift
```

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

## Línea de comandos (CLI)

Al instalar el paquete queda disponible el comando `gspreadmanager` para las operaciones más
comunes desde la terminal:

```bash
# Leer una hoja (CSV por defecto; también --format tsv|json)
gspreadmanager read "Mi Doc" Hoja1 --json-file creds.json

# Añadir una fila
gspreadmanager append "Mi Doc" Hoja1 Ana ana@example.com --json-file creds.json

# Exportar el documento (pdf por defecto) a un archivo
gspreadmanager export "Mi Doc" --format xlsx -o reporte.xlsx --json-file creds.json

# Compartir
gspreadmanager share "Mi Doc" alguien@example.com --role writer --json-file creds.json
```

El documento se indica por **nombre**, por **key** (`--key`) o por **URL** (se detecta sola).
La autenticación se pasa con `--json-file <creds.json>` o `--use-adc` (Application Default
Credentials).
