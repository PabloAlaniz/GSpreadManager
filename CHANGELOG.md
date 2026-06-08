# Changelog

All notable changes to GSpreadManager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Sprint 2 de purificación — puerto `RetryPolicy` (`gspreadmanager.ports.retry`) e
  implementación `ExponentialBackoffRetry` (`gspreadmanager.infrastructure.retry`):** el
  reintento deja de leer `self.max_retries`/`self.retry_backoff` y pasa a ser una política
  inyectable (`run(operation)`). El decorador `retry_on_rate_limit` se conserva como capa
  de compatibilidad que delega en la política. Nuevos tests aíslan la política del conector.
  Sin cambios de comportamiento (misma semántica: 429/500/503, backoff `b·2^intento`).
- **Sprint 1 de purificación — capa de dominio (`gspreadmanager.domain`):** nuevos value
  objects inmutables (`@dataclass(frozen=True)`) que serializan a la forma JSON de la
  Sheets API. Se mueven los modelos de formato (`Color`, `TextFormat`, `NumberFormat`,
  `Border`, `Borders`, `CellFormat`) a `domain/values/` y se agregan `A1Range`,
  `GridRange`, `SpreadsheetId`, `WorksheetRef`, `Condition`, `DataValidationRule` y
  `ConditionalFormatRule`. Jerarquía de errores en `domain/errors.py` (nuevos
  `InvalidColorError`, `InvalidRangeError`, `InvalidIdentifierError`, todos subclase de
  `ValueError` por compatibilidad). `gspreadmanager.formatting` y
  `gspreadmanager.exceptions` quedan como shims de re-export: los imports antiguos y la
  identidad de las clases se mantienen. Sin cambios de comportamiento.

### Changed
- **Sprint 0 de purificación (tooling, sin cambios de comportamiento):** ruff estricto
  (se suman `W`, `C4`, `SIM`, `TID`, `PTH`, `RET`, `ARG`, `PIE`, `PERF`, `PL`, `RUF`,
  `ANN`, `S`, `PT`, `D`) con `per-file-ignores` para `tests/`; mypy en modo `strict`
  ahora también type-checkea `tests/`, con el `Any` de gspread acotado al borde
  (`gspreadmanager.connector`) vía override. Pin de `ruff-pre-commit` actualizado.
  Primer paso del plan de migración hacia DDD/SOLID/Clean (2.0).

## [1.2.0] - 2026-06-07

### Added
- **Formato de celdas (implementación propia, sin dependencias nuevas):** módulo
  `gspreadmanager.formatting` con modelo tipado (`CellFormat`, `Color`, `TextFormat`,
  `NumberFormat`, `Border`, `Borders`), exportado desde el paquete.
- Métodos en el conector: `format_range`, `format_header`, `set_background`,
  `set_text_format`, `set_number_format`, `freeze`, `merge`.
- **Validación de datos:** `add_dropdown`, `add_checkbox`, `set_data_validation`.
- **Formato condicional:** `add_conditional_format` (reglas booleanas).
- **Operaciones a nivel documento (Drive):** `create_spreadsheet`, `delete_spreadsheet`,
  `copy_spreadsheet`, `list_spreadsheets`.
- **Compartir / permisos:** `share`, `list_permissions`, `remove_permission`.

### Notes
- Decisión de diseño: en lugar de depender de `gspread-formatting` (~1.564 LOC, un solo
  mantenedor), se implementó un modelo propio y enfocado sobre el transporte de gspread
  (`worksheet.format`, `freeze`, `merge_cells` y `spreadsheets.batchUpdate`). Ver
  [análisis competitivo](https://github.com/PabloAlaniz/GSpreadManager/blob/main/docs/competitive-analysis.md).

## [1.1.0] - 2026-06-07

### Added
- **Autenticación flexible:** además del service account por archivo, ahora se acepta
  `credentials` (objeto google-auth), `client` (cliente gspread ya autorizado),
  `service_account_info` (dict) y `use_adc=True` (Application Default Credentials).
- Documento de [análisis competitivo](https://github.com/PabloAlaniz/GSpreadManager/blob/main/docs/competitive-analysis.md) y roadmap actualizado.

### Changed
- **Caché de cliente y documento:** cambiar de pestaña ya no re-autentica ni reabre el
  documento (antes `connect_to_sheet` reconstruía el cliente en cada llamada).
- `json_google_file` pasa a ser opcional (default `None`) para habilitar los otros métodos
  de autenticación; sigue siendo el segundo parámetro posicional (compatible).

## [1.0.0] - 2026-06-07

Primer release estable. Consolida los sprints de estabilización, tipado, robustez y features.

### Added
- Sitio de documentación con **MkDocs Material** + **mkdocstrings** (`docs/`, `mkdocs.yml`).
- **Bandit** (escaneo de seguridad) integrado al job de lint del CI; job de build de docs.
- Badges de CI, mypy y ruff en el README.

### Changed
- Estado del paquete a `Development Status :: 5 - Production/Stable`; clasificadores
  `Typing :: Typed` y de tópicos.
- `.gitignore` ampliado para cubrir artefactos de build, caches y `site/`.

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
