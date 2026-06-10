# Migración 2.x → 3.0

La 3.0 culmina el plan de 10 sprints (ver ROADMAP): todo lo de la serie es **aditivo**
salvo dos cambios de comportamiento, ambos motivados por el fin del mantenimiento de
gspread ([ADR 0001](adr/0001-dependencia-de-gspread.md)).

## Cambios con impacto

### 1. gspread es un extra opcional

El núcleo solo depende de `google-auth`. Si tu código fuerza el backend de gspread (o pasás
un `client` preautorizado), instalá el extra:

```bash
pip install "GSpreadManager[gspread]"
```

### 2. El backend default es el cliente nativo

`SheetManager(...)` sin `backend=` usa el **cliente REST propio** (antes: gspread). La API
es idéntica — ambos backends implementan los mismos puertos y pasan el mismo test de
contrato — así que para la mayoría de los usos no cambia nada observable.

- Si pasás `client=` (un cliente de gspread ya autorizado), se sigue usando gspread
  (compatibilidad).
- Para forzar el comportamiento 2.x: `backend="auto"` (gspread si está instalado) o
  `backend="gspread"`.

```python
mgr = SheetManager("Doc", json_google_file="creds.json")                      # nativo (3.0)
mgr = SheetManager("Doc", json_google_file="creds.json", backend="gspread")  # como en 2.x
```

## Novedades de la 3.0 (resumen)

Ver el [CHANGELOG](changelog.md) completo. Lo más importante de la serie:

- **API async real** (`AsyncSheetManager`, extra `[async]` con httpx) — lectura/escritura,
  streaming, tabla, modelos y documento; testeable con
  `gspreadmanager.testing.AsyncInMemoryBackend`.
- **Jerarquía de errores propia** (`ApiError`, `QuotaExceededError`, `*NotFoundError`):
  ninguna excepción del backend escapa sin traducir.
- **La hoja como tabla**: `upsert`/`upsert_models`, `update_where`/`delete_where`,
  `worksheet_or_create`, chunking automático de escrituras.
- **Hojas grandes**: `iter_rows`/`iter_records`/`iter_as` paginados; caché con TTL, LRU e
  invalidación selectiva por rango.
- **Modelos Pydantic v2** (extra `[pydantic]`) + `ensure_schema` con reporte de drift;
  coerciones `Decimal`/`Enum`/`Literal` en dataclasses.
- **Paridad total** con gspread/pygsheets/EZSheets: import CSV, find/replace, `copy_to`,
  render options, propiedades del documento, pestañas por índice/id.
- **API v4 profunda**: charts, pivot tables, banding y developer metadata.
- **Logging opt-in** (`logging.getLogger("gspreadmanager")`), timeouts por petición y
  benchmarks (`benchmarks/run_benchmarks.py`).

## Qué no cambió

- Toda la API 2.x (`SheetManager`/`WorksheetContext` y sus métodos) sigue igual.
- El backend en memoria (`InMemoryBackend`) y los puertos son compatibles (sumaron
  `copy_to` y el parámetro `value_render_option` en `get_all_values`).
- La API async cubre el flujo de datos; **formato/validación/charts** siguen, por ahora,
  solo en la API síncrona.
