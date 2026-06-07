# Changelog

All notable changes to GSpreadManager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-06-07

### Added
- Gestión de hojas: `create_sheet(title, rows, cols, index, activate)` y `delete_sheet(title)`.
- `clear_range(ranges=None, tab_name=None)`: limpia uno o varios rangos, o toda la hoja.
- `find_cell(query, case_sensitive=True)`: devuelve la primera celda coincidente o `None`.
- Integración con pandas: `from_gsheet(...)` (lee como DataFrame) y
  `to_gsheet(df, tab_name, include_header, clear)` (vuelca un DataFrame a la hoja).
- Soporte de **context manager**: `with GoogleSheetConector(...) as conn:`.

## [0.3.0] - 2026-06-07

### Added
- `pyproject.toml` con metadata de packaging moderna (PEP 621) y versión dinámica.
- Archivo `LICENSE` (MIT) y `CONTRIBUTING.md`.
- Configuración de `ruff` (lint + format), `mypy` y `.pre-commit-config.yaml`.
- Extra opcional `pandas` (`pip install GSpreadManager[pandas]`) y extra `dev`.
- **Type hints** en todos los métodos públicos de `GoogleSheetConector`.
- Marcador `py.typed` (PEP 561) para que los consumidores reciban los tipos.
- **Reintentos automáticos con backoff exponencial** ante errores transitorios de la API
  (HTTP 429/500/503), configurables vía `max_retries` y `retry_backoff` en el constructor.
- **Excepciones propias** `GSpreadManagerError` e `InsertError`, exportadas desde el paquete.

### Changed
- **BREAKING:** los métodos `update_cell`, `update_row`, `spreadsheet_read_range` y
  `get_row_with_empty_in_column` ya no reciben `sheet` como primer parámetro; usan la hoja
  activa del conector. `sheet` sigue aceptándose como argumento opcional final por
  compatibilidad, pero emite `DeprecationWarning`.
- **`pandas` ahora es una dependencia opcional**, ya no se instala por defecto. Solo
  se requiere para `read_sheet_data(output_format='pandas')`, que lo importa de forma
  lazy y lanza un `ImportError` claro si no está instalado.
- Versión unificada: `gspreadmanager.__version__` es la única fuente de verdad,
  antes había desincronización entre `__init__.py` (0.1.5) y `setup.py` (0.2.0).
- `requires-python` elevado a `>=3.9`; CI con matriz 3.9–3.12, lint (`ruff` + `mypy`) y
  cobertura sobre `gspreadmanager`.
- `value_input_option` usa el enum `gspread.utils.ValueInputOption` en lugar de strings sueltos.

### Fixed
- `spreadsheet_read_range` y `spreadsheet_insert` llamaban a `values_get`/`values_append`
  sobre el `Worksheet`; ahora se invocan correctamente sobre el `Spreadsheet`
  (`sheet.spreadsheet`), evitando un `AttributeError` en runtime con gspread 6.x.
- `spreadsheet_insert` construía el rango con `chr(ord('A') + n)`, que se rompía más allá de
  la columna Z; ahora usa `gspread.utils.rowcol_to_a1` y soporta cualquier cantidad de columnas.
- `spreadsheet_insert` ahora lanza `InsertError` (antes `Exception` genérica).

## [0.2.0] - 2026-02-22

### Changed
- **BREAKING:** Migrated from deprecated `oauth2client` to `google-auth` library
  - `oauth2client` has been deprecated by Google since 2017
  - Replaced `oauth2client.service_account.ServiceAccountCredentials` with `google.oauth2.service_account.Credentials`
  - Updated dependency from `oauth2client>=4.0` to `google-auth>=2.0`

### Migration Guide

**For most users:** The change is transparent. The API remains the same:

```python
from gspreadmanager import GoogleSheetConector

# This still works exactly as before
conector = GoogleSheetConector(
    doc_name='My Sheet',
    json_google_file='credentials.json'
)
```

**For advanced users** who may have been using internal authentication methods:

**Before (v0.1.x):**
```python
from oauth2client.service_account import ServiceAccountCredentials
scope = ['https://spreadsheets.google.com/feeds', 
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)
```

**After (v0.2.0):**
```python
from google.oauth2 import service_account
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    'creds.json',
    scopes=scope
)
```

**Why this change?**
- `oauth2client` was deprecated in 2017 and is no longer maintained
- `google-auth` is the official, actively maintained Google authentication library
- Better security, performance, and future compatibility
- Aligns with Google's recommended authentication practices

**Compatibility:**
- Python 3.7+ (no change)
- All public APIs remain unchanged
- Service account JSON file format unchanged
- No code changes required for standard usage

### Fixed
- Future-proofed authentication against `oauth2client` deprecation warnings

## [0.1.5] - Previous Release
- Stable release with `oauth2client` dependency
