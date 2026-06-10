# GSpreadManager

[![PyPI version](https://badge.fury.io/py/GSpreadManager.svg)](https://badge.fury.io/py/GSpreadManager)
[![Tests](https://github.com/PabloAlaniz/GSpreadManager/actions/workflows/ci.yml/badge.svg)](https://github.com/PabloAlaniz/GSpreadManager/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GSpreadManager es un wrapper de Python para Google Sheets con una interfaz simple y *pythonic*
para lectura, escritura, formato, validación y gestión de hojas y documentos.

📚 **Documentación completa:** <https://pabloalaniz.github.io/GSpreadManager/>

> **API 2.0:** el punto de entrada es `SheetManager`. `mgr.worksheet("Hoja1")` devuelve un
> handle **inmutable** a una pestaña; no hay "hoja activa" global ni efectos colaterales.
> (La clase `GoogleSheetConector` de la 1.x fue eliminada — ver [CHANGELOG](CHANGELOG.md).)

## ✨ Características

- 🔐 **Autenticación flexible**: service account (archivo o dict), credenciales de `google-auth`, cliente ya autorizado o ADC
- 📖 **Lectura flexible**: listas, diccionarios, `pandas`/`polars` o **modelos de fila tipados** (`@dataclass`)
- ✏️ **Escritura y actualización**: celdas, filas, rangos, append, insert y lotes
- 📐 **Estructura de la hoja**: insertar/eliminar/redimensionar/ocultar filas y columnas, **orden y filtro**, merge/unmerge, color de pestaña
- 🗂️ **Gestión de hojas y documentos** (Drive): crear, copiar, listar, borrar, **compartir/permisos** y **exportar** (PDF/CSV/XLSX/...)
- 🏷️ **Metadata**: notas de celda, **named ranges** y **protected ranges**
- 🎨 **Formato propio** (sin dependencias): colores, fuentes, números, freeze, validación y formato condicional
- 🐼 **DataFrames pluggable**: `pandas` **o** `polars`, con lectura avanzada (`drop_empty_*`, `index_col`) y escritura anclada
- ⚡ **Robustez de cuota**: reintentos con backoff (429/500/503) + **rate limiting proactivo** (token bucket) + **caché de lecturas**
- 🧪 **Testeable sin red**: backend en memoria (`gspreadmanager.testing`) que implementa los mismos puertos
- ⌨️ **CLI**: `gspreadmanager read/append/export/share`
- 🔌 **Backend nativo opcional** (`backend="native"`): cliente REST propio sobre `google-auth`, sin gspread en el medio
- 🧱 **Arquitectura hexagonal** (dominio / aplicación / infraestructura / puertos) con type hints (PEP 561)
- 📦 **Dependencias mínimas**: solo `gspread` y `google-auth` (`pandas`/`polars` opcionales)

## 🚀 Instalación

```bash
pip install GSpreadManager                # núcleo (cliente nativo, solo google-auth)

# Extras opcionales
pip install "GSpreadManager[gspread]"     # backend de gspread (default si está instalado)
pip install "GSpreadManager[pandas]"      # DataFrames con pandas
pip install "GSpreadManager[polars]"      # DataFrames con polars
```

> Desde la v2.2 `gspread` es **opcional**: sin él, `SheetManager` usa automáticamente el
> cliente nativo (REST sobre `google-auth`), con la misma API. Podés forzar el transporte
> con `backend="gspread"` o `backend="native"`.

### Configuración en Google Cloud

1. En [Google Cloud Console](https://console.cloud.google.com/), creá un proyecto y una **cuenta de servicio**; descargá su clave JSON.
2. Habilitá **Google Sheets API** y **Google Drive API**.
3. Compartí tu hoja con el email de la cuenta de servicio, con permiso de **Editor**.

## ⚡ Quick start

```python
from gspreadmanager import SheetManager

mgr = SheetManager("Mi Hoja de Cálculo", json_google_file="credentials.json")
ws = mgr.worksheet("Hoja1")        # handle inmutable a la pestaña

# Leer
datos = ws.read(output_format="dict")

# Escribir
ws.append([["Juan", "juan@example.com"]])
ws.update_cell(2, 1, "María")

# Otra pestaña, handle independiente
ws2 = mgr.worksheet("Hoja2")
```

## 📚 Uso

### Lectura

```python
ws.read(output_format="list")                # lista de listas
ws.read(output_format="dict")                # lista de dicts (1ª fila = encabezados)
ws.read(output_format="pandas")              # DataFrame (extra [pandas])
ws.read_range(1, 10, "A", "D")               # rango por índices de fila/columna
```

### Escritura y actualización

```python
ws.append([["Ana", "ana@example.com"]])
ws.update_cell(3, 2, "Nuevo Valor")
ws.update_row(5, ["X", "Y", "Z"], start_column=3)
ws.insert([["A", "B"]], fila=10)             # inserta en una fila (o al final)
ws.batch_update([{"range": "Hoja1!A1:B1", "values": [["Mes", "Total"]]}])
```

### Consultas

```python
filas = ws.rows_where_column_equals(0, "Activo")   # [(nro_fila, fila), ...]
ultima = ws.last_row()
fila, idx = ws.row_with_empty_in_column("B")
celda = ws.find("Total")
```

### Formato, validación y condicional

```python
from gspreadmanager import CellFormat, TextFormat, Color

ws.format_header()                                   # negrita + fondo, primera fila
ws.freeze(rows=1)
ws.format_range("A1:D1", CellFormat(
    text_format=TextFormat(bold=True, foreground_color=Color.from_hex("#FFFFFF")),
    background_color=Color.from_hex("#0B5394"),
    horizontal_alignment="CENTER",
))
ws.set_background("A2:A100", Color.from_hex("#FFF2CC"))
ws.set_number_format("C2:C100", "#,##0.00", number_type="CURRENCY")
ws.merge("A1:D1")

ws.add_dropdown("E2:E100", ["Pendiente", "En curso", "Hecho"])
ws.add_checkbox("F2:F100")
ws.add_conditional_format("C2:C100", "NUMBER_LESS", [0],
                          CellFormat(background_color=Color.from_hex("#F4CCCC")))
```

### DataFrames (pandas o polars)

```python
df = ws.read_dataframe()                      # backend por defecto: pandas
ws.write_dataframe(df)                         # limpia la hoja y escribe desde A1
ws.write_dataframe(df, start_cell="B2", include_index=True, clear=False)
ws.read_dataframe(drop_empty_rows=True, drop_empty_cols=True, index_col="id")

mgr = SheetManager("Mi Hoja", "creds.json", dataframe_backend="polars")
```

### Estructura, orden, exportación

```python
ws.insert_rows(2, number=3); ws.delete_cols(5)        # filas/columnas (1-based)
ws.sort_range("A2:C100", (1, "asc"), (3, "desc"))     # ordenar por columnas
ws.set_basic_filter("A1:C100")                         # filtro básico
ws.set_tab_color(Color.from_hex("#D9EAD3"))

ws.update_note("B2", "revisar"); ws.define_named_range("Datos", "A1:B100")

from gspreadmanager import ExportFormat
pdf = mgr.export()                                     # bytes (PDF por defecto)
xlsx = mgr.export(ExportFormat.EXCEL)
```

### Modelos de fila tipados (dataclasses)

```python
from dataclasses import dataclass

@dataclass
class Persona:
    nombre: str
    edad: int
    activo: bool

personas = ws.read_as(Persona)                # -> list[Persona], con tipos convertidos
ws.append_models([Persona("Ana", 30, True)])
```

### Caché y rate limiting

```python
mgr = SheetManager("Mi Hoja", "creds.json",
                   cache=True,        # memoiza lecturas, se invalida al escribir
                   rate_limit=1)      # token bucket: ~1 operación/seg (no choca la cuota)
mgr.clear_cache()                     # refresco manual ante cambios externos
```

### Testear sin red

```python
from gspreadmanager.testing import InMemoryBackend

backend = InMemoryBackend()
backend.add_spreadsheet("MiDoc", {"Hoja1": [["nombre", "email"], ["Ana", "ana@x.com"]]})
mgr = backend.manager("MiDoc")        # un SheetManager que no toca la red
```

### CLI

```bash
gspreadmanager read   "Mi Doc" Hoja1 --format json --json-file creds.json
gspreadmanager append "Mi Doc" Hoja1 Ana ana@example.com --json-file creds.json
gspreadmanager export "Mi Doc" --format xlsx -o reporte.xlsx --json-file creds.json
```

### Hojas, documentos y permisos

```python
nueva = mgr.create_sheet("Reporte 2026", rows=500, cols=10)   # devuelve un handle
mgr.delete_sheet("Borrador")

nuevo = mgr.create_spreadsheet("Reporte mensual")
copia = mgr.copy_spreadsheet(nuevo.id, title="Reporte (copia)")
mgr.list_spreadsheets(title="Reporte")
mgr.delete_spreadsheet(copia.id)

mgr.share("alguien@example.com", role="writer")
mgr.list_permissions()
mgr.remove_permission("alguien@example.com")
```

### Context manager

```python
with SheetManager("Mi Hoja", "creds.json") as mgr:
    df = mgr.worksheet("Hoja1").read_dataframe()
```

### Manejo de errores y reintentos

Las operaciones reintentan automáticamente ante errores transitorios (HTTP 429/500/503) con
backoff exponencial, configurable con `max_retries` y `retry_backoff` en `SheetManager`.

```python
from gspreadmanager import InsertError

try:
    ws.insert([["A", "B"]])
except InsertError as e:
    print(f"No se pudo insertar: {e}")
```

## 🏗️ Arquitectura

GSpreadManager sigue una arquitectura por capas (Clean Architecture / DDD táctico). La
dependencia de gspread queda **aislada en `infrastructure/`**: el dominio y la capa de
aplicación no la importan, lo que facilita testear con *fakes* y, eventualmente, sustituir el
cliente subyacente.

```
gspreadmanager/
├── domain/          # value objects (formato, rangos, reglas), schema, numericise, export, errores — sin I/O
├── ports/           # Protocols: sheets (client/spreadsheet/worksheet), auth, retry, rate_limit, dataframe
├── application/     # servicios de casos de uso (data, formatting, validation, worksheet,
│                    #   document, sharing, metadata, dataframe, row_model) — sin gspread
├── infrastructure/  # gspread adapters/client, auth, retry, rate_limit, cache, request_builders,
│                    #   pandas/polars adapters, native/ (spike de cliente REST)
├── testing/         # backend en memoria (InMemoryBackend) que implementa los puertos
├── facade.py        # SheetManager + WorksheetContext (API público)
├── cli.py           # CLI `gspreadmanager`
├── config.py
└── retry.py
```

Los puertos nominales (`ClientPort`/`SpreadsheetPort`/`WorksheetPort`) tienen **cuatro**
implementaciones intercambiables, verificadas por un test de contrato: adaptador de gspread
(por defecto), cliente REST nativo (spike), backend en memoria y wrappers de caché.

**Dependencias:** `gspread` (>=3.0), `google-auth` (>=2.0); `pandas` (>=1.2.4) y `polars`
(>=0.20) opcionales.

## 🧪 Desarrollo

```bash
pip install -e ".[dev]"

ruff check .            # lint
ruff format --check .   # formato
mypy                    # type-check estricto
pytest                  # tests (con cobertura)
```

## 🤝 Contribuir

1. Hacé un **fork** y creá una branch (`git checkout -b feature/mi-feature`).
2. Mantené verdes `ruff`, `mypy` y `pytest`, y agregá tests para lo nuevo.
3. Abrí un **Pull Request**.

## 📄 Licencia

MIT License — ver [LICENSE](LICENSE).

## 🙏 Agradecimientos

- [gspread](https://github.com/burnash/gspread) — cliente de Google Sheets API
- [google-auth](https://github.com/googleapis/google-auth-library-python) — autenticación oficial de Google
- [pandas](https://pandas.pydata.org/) — análisis de datos

---

**Hecho con ❤️ por Pablo Alaniz**
