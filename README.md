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
- 📖 **Lectura flexible**: listas, diccionarios o `pandas.DataFrame`
- ✏️ **Escritura y actualización**: celdas, filas, rangos, append, insert y lotes
- 🗂️ **Gestión de hojas y documentos** (Drive): crear, copiar, listar, borrar y **compartir/permisos**
- 🎨 **Formato propio** (sin dependencias): colores, fuentes, números, freeze, merge, validación y formato condicional
- 🐼 **Integración con pandas** (`read_dataframe` / `write_dataframe`)
- ♻️ **Reintentos automáticos** con backoff ante límites de cuota (429/500/503)
- 🧱 **Arquitectura por capas** (dominio / aplicación / infraestructura / puertos) con type hints (PEP 561)
- 📦 **Dependencias mínimas**: solo `gspread` y `google-auth` (`pandas` opcional)

## 🚀 Instalación

```bash
pip install GSpreadManager

# Con soporte pandas (opcional)
pip install "GSpreadManager[pandas]"
```

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

### pandas

```python
df = ws.read_dataframe()
ws.write_dataframe(df)                        # limpia la hoja y escribe desde A1
ws.write_dataframe(df, include_header=False, clear=False)
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
├── domain/          # value objects (formato, rangos, reglas) + errores — sin I/O
├── ports/           # Protocols: AuthStrategy, RetryPolicy, DataFramePort
├── application/     # 7 servicios de casos de uso (data, formatting, validation,
│                    #   worksheet, document, sharing, dataframe) — sin gspread
├── infrastructure/  # auth (estrategias), gspread_client (caché), retry,
│                    #   request_builders, pandas_adapter
├── facade.py        # SheetManager + WorksheetContext (API público)
├── config.py
└── retry.py
```

**Dependencias:** `gspread` (>=3.0), `google-auth` (>=2.0) y `pandas` (>=1.2.4, opcional).

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
