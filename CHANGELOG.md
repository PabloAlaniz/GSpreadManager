# Changelog

All notable changes to GSpreadManager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2026-06-10

Los 10 sprints del plan v2.2 → v3.0 (ver ROADMAP), publicados como un único release mayor:
pureza de capas y contrato de errores, **cliente nativo como backend por defecto**
(culmina el ADR 0001; gspread queda como extra opcional), **paridad total** con
gspread/pygsheets/EZSheets, la hoja como tabla, streaming para hojas grandes, modelos
Pydantic, la API v4 profunda (charts/pivot/banding/metadata) y la **API async real**.
Guía de migración: ``docs/migration-3.0.md``.

### Breaking changes (desde 2.1.0)
- **El backend por defecto es el cliente nativo** (REST sobre google-auth). Se usa gspread
  solo si se pasa ``client=`` (preautorizado) o ``backend="gspread"``/``"auto"``.
- **gspread es un extra opcional**: ``pip install "GSpreadManager[gspread]"``. El núcleo
  solo depende de ``google-auth``.

### Added
- **API async (Sprint 10):** ``AsyncSheetManager`` + ``AsyncWorksheetContext`` —
  lectura (list/dict/render/numericise), escritura con chunking, streaming
  (``iter_rows``/``iter_records``/``iter_as`` como async generators), la hoja como tabla
  (``upsert``/``upsert_models``/``update_where``/``delete_where``), modelos tipados
  (``read_as``/``append_models``/``write_models``/``ensure_schema``), import CSV,
  find/replace, ``copy_to`` y operaciones de documento (Drive, permisos, propiedades,
  export). Reutiliza la lógica pura del paquete (planners de tabla extraídos a funciones
  de módulo en ``table_service``); usable como ``async with`` (cierra la sesión httpx).
  Formato/validación/charts siguen, por ahora, solo en la API síncrona.
- **``AsyncInMemoryBackend``** (``gspreadmanager.testing``): el mismo fake en memoria con
  superficie async, para testear ``AsyncSheetManager`` sin red.
- **Async nativo, núcleo (Sprint 9):** asyncio real, no threadpool (nadie en el ecosistema
  lo tiene; `gspread-asyncio` usa threads):
  - Puertos async espejo (`ports/async_sheets.py`): `AsyncClientPort`/
    `AsyncSpreadsheetPort`/`AsyncWorksheetPort` con la **misma superficie** que los
    síncronos (verificado por test), más `AsyncRetryPolicy` y `AsyncRateLimiter`.
  - `AsyncSheetsApiClient` (`infrastructure/native/async_client.py`): espejo async del
    cliente nativo — Sheets v4 + Drive v3 completos, caché de documentos, 404 →
    `SpreadsheetNotFoundError`, mismos errores de dominio.
  - Sesión `httpx` autorizada (`build_async_session`, extra opcional
    `pip install "GSpreadManager[async]"`): token Bearer de google-auth con refresh fuera
    del event loop (`asyncio.to_thread`), timeout por petición, usable como
    `async with`.
  - `AsyncExponentialBackoffRetry` y `AsyncTokenBucketRateLimiter` con `asyncio.sleep`
    (esperas cooperativas, sin bloquear el loop; reloj y sleep inyectables).
- **API v4 profunda (Sprint 8, nuevo `VisualizationService`):**
  - `ws.add_chart(tipo, domain, series, title=..., anchor_cell=...)` — gráficos embebidos
    (LINE/BAR/COLUMN/AREA/SCATTER/PIE) y `ws.delete_chart(id)`.
  - `ws.add_pivot_table(source, anchor_cell, rows=..., values=..., columns=...)` — pivot
    tables (offsets 0-based + función de agregación).
  - `ws.set_banding(rango, first_color=..., second_color=..., header_color=...)` y
    `ws.delete_banding(id)` — bandas de color alternadas.
  - **Developer metadata**: `ws.set_developer_metadata` (por pestaña),
    `mgr.set_developer_metadata` (por documento), `mgr.list_developer_metadata` y
    `mgr.delete_developer_metadata(key)`.
  - Todo modelado como value objects del dominio (`ChartSpec`, `PivotTableSpec`,
    `PivotField`/`PivotValue`, `BandingSpec`, `DeveloperMetadataEntry`) con `to_request`
    validado por tests contra la forma exacta de la API. Fix del fake in-memory: solo
    trata `updateCells` como nota cuando `fields="note"` (las pivots usan el mismo verbo).
- **Modelos Pydantic v2 y esquema avanzado (Sprint 7):**
  - Nuevo puerto `ModelCodec` con dos codecs (`infrastructure/model_codecs.py`):
    dataclasses (el mapeo puro del dominio) y **Pydantic v2** (extra opcional
    `pip install "GSpreadManager[pydantic]"`, import diferido). `read_as`/`append_models`/
    `write_models`/`upsert_models`/`iter_as` aceptan ambos tipos de modelo; con Pydantic
    la validación/coerción es nativa (alias de campo = nombre de columna; los
    `ValidationError` llegan como `SchemaError`).
  - `ws.ensure_schema(Model, create=True, strict=False)`: valida (o crea) el encabezado
    contra el modelo, con **reporte de drift** — `SchemaError` enriquecido con
    `missing_columns` / `extra_columns`.
  - Coerciones nuevas en el codec de dataclasses: `Decimal`, `Enum` (por valor o nombre)
    y `Literal`, también al serializar (`format_cell`).
- **Streaming para hojas grandes (Sprint 6):** `ws.iter_rows(page_size=...)`,
  `ws.iter_records(...)` (dicts por encabezado) y `ws.iter_as(Model, ...)` (dataclasses) —
  iteradores perezosos que leen de a páginas vía `values_get`; cada página con su propio
  retry y permiso del rate limiter. Solo se materializa una página por vez.
- **Caché v2 (Sprint 6):** TTL opcional (`SheetManager(cache_ttl=...)`, acota la ventana de
  staleness), límite de entradas con desalojo LRU (`cache_max_entries=...`; pasar
  cualquiera de los dos activa la caché) e **invalidación selectiva**: `update_cell`/
  `batch_update`/`batch_clear` solo invalidan lo cacheado que se superpone con el rango
  escrito (nuevo `GridRange.overlaps` en el dominio); las escrituras de alcance hoja
  (`update`/`append`/`clear`/formato) invalidan esa hoja sin tocar las demás; las
  operaciones a nivel documento invalidan todo.
- **La hoja como tabla (Sprint 5, nuevo `TableService`):**
  - `ws.upsert(rows, key=...)` — actualiza por columna clave y agrega lo nuevo; acepta
    dicts (actualiza solo las columnas presentes) o listas alineadas al encabezado;
    devuelve `{"updated": n, "appended": m}`. `ws.upsert_models(models, key=...)` para
    dataclasses. Idempotente: re-ejecutar el mismo upsert no duplica filas.
  - `mgr.worksheet_or_create(title, rows=..., cols=...)` — find-or-create de pestaña.
  - `ws.update_where(where, updates)` y `ws.delete_where(where)` — `where` como dict de
    igualdades o predicado sobre la fila; el delete agrupa rangos contiguos y borra de
    abajo hacia arriba (`deleteDimension`).
  - **Chunking automático de escrituras** (`SheetManager(batch_cell_limit=50_000)`):
    `append`/`batch_update`/`upsert` grandes se parten en varias peticiones — cada chunk
    con su propio retry y permiso del rate limiter, así un 429 a mitad de camino no
    re-ejecuta los chunks ya aplicados. Helpers puros en `domain/batching.py`
    (`split_rows`/`split_range_data`; una fila o rango nunca se parte). `None` lo
    desactiva.
- **Paridad final con el ecosistema (Sprint 4):**
  - `ws.import_csv(ruta_o_buffer, clear=..., delimiter=...)` — vuelca un CSV en la hoja
    (parsing puro en `domain/csv_data.py`, escritura `RAW`).
  - `mgr.update_title()` / `update_locale()` / `update_timezone()` — propiedades del
    documento vía `updateSpreadsheetProperties`.
  - `mgr.list_worksheets()` y apertura de pestañas por posición o id:
    `worksheet_by_index(i)` / `worksheet_by_id(sheet_id)`.
  - `ws.find_replace(find, replacement, match_case=..., match_entire_cell=...,
    search_by_regex=..., include_formulas=...)` — `findReplace` de la API v4; devuelve el
    resumen (`occurrencesChanged`, ...). El backend en memoria lo aplica de verdad a la
    grilla (literal, sin regex) para poder testearlo.
  - `ws.copy_to(destination_key)` — copia la pestaña a otro documento (`sheets.copyTo`;
    nuevo método del `WorksheetPort` en los 4 backends; el in-memory copia entre documentos
    del mismo `InMemoryBackend`).
  - `ws.read(render="formatted" | "unformatted" | "formula")` — value render options al
    leer (fórmulas o valores crudos); `get_all_values` del puerto acepta el render y la
    caché memoiza por opción.
- **gspread es ahora un extra opcional** (`pip install "GSpreadManager[gspread]"`): el
  núcleo solo depende de `google-auth`. Nuevo default `backend="auto"`: usa gspread si está
  instalado (o si se pasa `client=`), si no el cliente nativo — el quick start funciona
  igual con cualquier instalación. Si se fuerza `backend="gspread"` sin el paquete, el
  error explica cómo instalarlo. (Breaking solo para quien dependía de que gspread viniera
  de fábrica: instalá el extra.)
- **Hardening del cliente nativo:** `create(..., folder_id=...)` ahora mueve el documento a
  la carpeta (Drive `files.update` con `addParents`; cierra un pendiente del spike), y los
  errores 429/403 producen `SheetsQuotaExceededError` / `SheetsPermissionDeniedError`, que
  heredan de `QuotaExceededError` / `PermissionDeniedError` del dominio: el mismo `except`
  funciona con cualquier backend.
- **Suite de benchmarks** (`benchmarks/run_benchmarks.py` + página en docs): compara
  gspread vs nativo contra la API real (read/append/batch/update/formato) y emite la tabla
  en Markdown. Manual, con las mismas credenciales que la suite de integración.
- **Backend nativo opt-in (`SheetManager(backend="native")`):** ejecuta el ADR 0001 (gspread
  quedó sin mantenimiento activo). El cliente REST propio (`infrastructure/native/`) deja de
  ser spike: se cablea detrás de los mismos puertos con caché de documentos abiertos por
  nombre/key, **timeouts por petición** (`http_timeout`, default 60s) y mapeo de
  404 → `SpreadsheetNotFoundError`. Acepta `json_google_file`, `credentials`,
  `service_account_info` o `use_adc` (nuevo `build_credentials` en `infrastructure/auth.py`,
  que construye credenciales de google-auth sin gspread). gspread sigue como default
  hasta la 3.0.
- **Tests de integración opcionales** contra la API real (marker `integration`; se saltean
  sin `GSPREADMANAGER_TEST_CREDENTIALS`).
- **Jerarquía completa de errores de dominio:** `ApiError` (con `status_code`),
  `QuotaExceededError` (429), `PermissionDeniedError` (403), `SpreadsheetNotFoundError`,
  `WorksheetNotFoundError` y `CellNotFoundError`, exportadas desde el paquete raíz.
  Los adaptadores de gspread traducen **todas** las excepciones de gspread a esta jerarquía
  (`infrastructure/gspread_errors.py`): ninguna excepción del backend escapa al usuario.
  El `SheetsApiError` del cliente nativo y los not-found del backend en memoria se integran
  a la misma jerarquía.
- **Logging estructurado opt-in:** logger `gspreadmanager` con `NullHandler` por defecto.
  Reintentos en `WARNING`; rate limiting, caché (hit/miss/invalidación) y apertura de
  documentos en `DEBUG`.
- **Helpers A1 en el dominio:** `rowcol_to_a1`, `column_to_letter`, `letter_to_column` y
  `GridRange.from_a1` viven en `domain/values/ranges.py` (lógica pura, errores
  `InvalidRangeError`), con paridad verificada contra `gspread.utils`.

### Changed
- **`ExponentialBackoffRetry` desacoplada de gspread:** ahora opera sobre el `ApiError`
  del dominio (los adaptadores traducen antes), por lo que funciona igual con cualquier
  backend (gspread, nativo, in-memory).
- **Sin `gspread.utils` fuera de los adaptadores:** la capa de aplicación
  (`data_service`), los request builders y el backend en memoria usan las conversiones A1
  del dominio. Cierra la última fuga de la regla de dependencias (DIP).

### Fixed
- `pytest.ini` usaba la sección `[tool:pytest]` (solo válida en setup.cfg), por lo que pytest
  ignoraba `addopts`/`testpaths`; ahora es `[pytest]` y la config (cobertura mínima, markers)
  aplica de verdad.

### Docs
- ROADMAP con el plan de 10 sprints (v2.2 → v3.0).
- ADR 0001 actualizado: **disparador cumplido** (gspread sin maintainers); se ejecuta la
  opción C de forma incremental (nativo opt-in primero, default en 3.0).
- Análisis competitivo actualizado (estado de gspread) y guía con la jerarquía de errores,
  el logging y el backend nativo (`backend="native"`).

## [2.1.0] - 2026-06-09

Paridad con gspread/pygsheets y un conjunto de capacidades de diferenciación, todo sobre la
arquitectura hexagonal de la 2.0 (sin reemplazar gspread, que sigue como adaptador por defecto).

### Added
- **v2.1 — Diferenciación: CLI (`gspreadmanager`):** comando de terminal (solo `argparse`, sin
  dependencias extra) con `read` (CSV/TSV/JSON), `append`, `export` (a archivo o stdout) y
  `share`. El documento se indica por nombre, key (`--key`) o URL; autenticación con
  `--json-file` o `--use-adc`. Entry point `gspreadmanager = "gspreadmanager.cli:main"`; la
  construcción del gestor es inyectable (`manager_factory`) para testear sin red.
- **v2.1 — Diferenciación: rate limiting proactivo (token bucket):**
  `SheetManager(..., rate_limit=<ops/seg>, rate_limit_burst=<ráfaga>)` frena las operaciones
  *antes* de pegarle a la cuota (a diferencia del retry, que reacciona a un 429). Nuevo puerto
  `RateLimiter` e implementación `TokenBucketRateLimiter` (con reloj/sleep inyectables,
  thread-safe); el decorador `retry_on_rate_limit` pide un permiso antes de cada operación.
  Opt-in (apagado por defecto). El bucket es global por gestor (compartido entre handles).
- **v2.1 — Diferenciación: caché de lecturas con invalidación:** `SheetManager(..., cache=True)`
  activa una caché transparente que memoiza las lecturas (`get_all_values`, `values_get`,
  `get_metadata`) por documento y se invalida con cada escritura propia (a nivel hoja o
  documento). Implementada como wrappers de los puertos (`CachingClient`/`CachingSpreadsheet`/
  `CachingWorksheet`), opt-in (no detecta cambios de otros procesos); `mgr.clear_cache()` fuerza
  el refresco. El test de contrato cubre también los wrappers.
- **v2.1 — Diferenciación: modelos de fila tipados (dataclasses):** `WorksheetContext` gana
  `read_as(Model)` (devuelve `list[Model]`), `append_models(...)` y `write_models(...)`. El
  encabezado mapea a los campos del dataclass por nombre o por `field(metadata={"column": ...})`,
  con coerción de tipos (int/float/bool/date/datetime, `Optional` -> `None`) y validación
  (`SchemaError`, exportada desde el paquete raíz). Mapeo puro en `domain/schema.py`, orquestado
  por `RowModelService`. Nadie en el ecosistema lo ofrece de fábrica.
- **v2.1 — Diferenciación: backend en memoria para tests (`gspreadmanager.testing`):**
  nuevo `InMemoryBackend`/`InMemoryClient`/`InMemorySpreadsheet`/`InMemoryWorksheet` que
  implementan los puertos `ClientPort`/`SpreadsheetPort`/`WorksheetPort`, para que los usuarios
  prueben su código sin red. Los valores hacen round-trip y las operaciones estructurales
  (insertar/eliminar filas, notas, named/protected ranges) se aplican sobre la grilla; el
  formato/validación/orden/filtro se registran en `spreadsheet.requests` sin alterarla.
  `SheetManager` acepta `sheets_client=...` para inyectar cualquier `ClientPort`. El test de
  contrato ahora cubre también el fake (mismo set de métodos que gspread y el cliente nativo).
- **v2.1 — Sprint 5 (pandas avanzado + backend polars):** el motor de DataFrame es
  pluggable vía `SheetManager(dataframe_backend="pandas"|"polars")` (nuevo
  `PolarsDataFrameAdapter` detrás del `DataFramePort`, factory `build_dataframe_adapter`,
  extra `pip install GSpreadManager[polars]`). `read_dataframe` gana `drop_empty_rows`,
  `drop_empty_cols` e `index_col` (índice solo pandas); el limpiado de filas/columnas vacías
  es una función pura del dominio (`domain/dataframe.prune_empty`). `write_dataframe` gana
  `start_cell` (anclar la escritura en una celda arbitraria) e `include_index`. El puerto
  `WorksheetPort.update` acepta un `range_name` opcional, implementado en ambos adaptadores.
- **v2.1 — Sprint 4 (orden/filtro, unmerge, color de pestaña, exportación):**
  `WorksheetContext` gana `sort_range(rango, (columna, "asc"|"desc"), ...)`,
  `set_basic_filter`/`clear_basic_filter`, `unmerge` y `set_tab_color`/`clear_tab_color`
  (requests `sortRange`/`setBasicFilter`/`clearBasicFilter`/`unmergeCells`/
  `updateSheetProperties` en `WorksheetService`, sin nueva superficie de puerto).
  `SheetManager.export(export_format=ExportFormat.PDF)` descarga el documento como bytes
  (PDF/CSV/TSV/Excel/ODS/HTML); nuevo enum `ExportFormat` exportado desde el paquete raíz,
  un único método de puerto `SpreadsheetPort.export` (vía `files.export` de Drive)
  implementado en ambos adaptadores, y `HttpResponse.content` para el cliente nativo.
  La importación desde CSV queda pendiente (ver ROADMAP).
- **v2.1 — Sprint 3 (notas + named/protected ranges):** `WorksheetContext` gana
  `update_note`/`clear_note`/`get_note`, `define_named_range`, `add_protected_range`/
  `list_protected_ranges`/`delete_protected_range`; `SheetManager` gana `list_named_ranges`/
  `delete_named_range`. Nuevo `MetadataService` y un único método de puerto
  `SpreadsheetPort.get_metadata` (lecturas vía `spreadsheets.get`), implementado en ambos
  adaptadores. El resto son requests de `batchUpdate` (sin más superficie de puerto).
- **v2.1 — Sprint 2 (filas/columnas estructurales):** `WorksheetContext` gana
  `insert_rows`/`insert_cols`, `delete_rows`/`delete_cols`, `add_rows`/`add_cols`,
  `resize_rows`/`resize_cols` y `hide_rows`/`unhide_rows`/`hide_cols`/`unhide_cols`
  (posiciones 1-based). Implementado como requests `insertDimension`/`deleteDimension`/
  `appendDimension`/`updateDimensionProperties` en `WorksheetService`; no agrega métodos de
  puerto (usa `worksheet.spreadsheet.batch_update`), así que funciona en ambos backends.
- **v2.1 — Sprint 1 (direccionamiento + lectura tipada):**
  - **Abrir por key / URL:** `SheetManager.open_by_key(key)` y `SheetManager.open_by_url(url)`
    (además del nombre). Nuevo `ClientPort.open_by_key` implementado en ambos adaptadores
    (gspread y nativo) y `SpreadsheetId.from_url`. El `__init__` acepta `key=...`.
  - **Type inference al leer:** `WorksheetContext.read(..., numericise=True)` convierte los
    valores a int/float cuando corresponde (preserva ceros a la izquierda). Módulo
    `gspreadmanager.domain.numericise`.

## [2.0.0] - 2026-06-08

Reescritura interna a Clean Architecture / DDD táctico (capas dominio / aplicación /
infraestructura / puertos) y un API nuevo sin estado mutable. Sin usuarios previos, se
hace el corte limpio: se elimina el API 1.x en vez de deprecarlo.

### Breaking changes
- **Se elimina `GoogleSheetConector`.** El nuevo punto de entrada es `SheetManager` +
  `WorksheetContext`: `mgr = SheetManager(doc); ws = mgr.worksheet("Hoja1"); ws.append(...)`.
  Ya no existe una "hoja activa" mutable ni el parámetro `tab_name` con efecto colateral:
  cada `worksheet(...)` devuelve un handle inmutable e independiente.
- **Se elimina el parámetro `sheet`** (que estaba obsoleto en 1.x) de las operaciones de hoja.
- **Se eliminan los módulos shim `gspreadmanager.formatting` y `gspreadmanager.exceptions`.**
  Importar desde el paquete raíz (`from gspreadmanager import CellFormat, GSpreadManagerError`)
  o desde `gspreadmanager.domain`.
- Renombres de operaciones en el handle de hoja: `read_sheet_data`→`read`,
  `spreadsheet_append`→`append`, `spreadsheet_read_range`→`read_range`,
  `spreadsheet_insert`→`insert`, `clear_range`→`clear`, `find_cell`→`find`,
  `from_gsheet`→`read_dataframe`, `to_gsheet`→`write_dataframe`.

### Added
- **API 2.0 `SheetManager` + `WorksheetContext`
  (`gspreadmanager.facade`):** nuevo punto de entrada sin "hoja activa" mutable.
  `mgr = SheetManager(doc); ws = mgr.worksheet("Hoja1")` devuelve un handle inmutable atado
  a una pestaña; dos handles son independientes y ninguna operación tiene efectos colaterales
  sobre otro. El `WorksheetContext` expone las operaciones de hoja sin parámetro `tab_name`
  ni `sheet`; `SheetManager` expone las operaciones a nivel documento (Drive, permisos,
  crear/eliminar hojas) y `create_sheet` devuelve un handle en vez de "activar" la hoja.
  Ambos delegan en los 7 servicios de la capa de aplicación. Exportados desde el paquete raíz.
- **Sprint 5 de purificación — capa de aplicación (`gspreadmanager.application`):** se
  extraen 7 servicios de casos de uso desde el god class `GoogleSheetConector`, que ahora
  delega en ellos: `DataService` (lectura/escritura/append/insert/consultas),
  `FormattingService` (formato, freeze, merge + builders de `CellFormat`),
  `ValidationService` (validación y formato condicional), `WorksheetService` (crear/eliminar/
  limpiar/buscar), `DocumentService` (Drive), `SharingService` (permisos) y `DataframeService`
  (integración pandas vía el puerto `DataFramePort` y `PandasDataFrameAdapter`). Los servicios
  no importan gspread (salvo utilidades puras) y son testeables con fakes. Sin cambios de
  comportamiento.
- **Puertos nominales de Sheets + adaptadores (ADR 0001, opción B):** se introducen
  `WorksheetPort`/`SpreadsheetPort`/`ClientPort` (`gspreadmanager.ports.sheets`) con firmas
  propias, y los adaptadores `GspreadWorksheet`/`GspreadSpreadsheet`/`GspreadClientAdapter`
  (`gspreadmanager.infrastructure`) que los implementan envolviendo gspread. La capa de
  aplicación pasa a depender de los puertos (no de `Any`); el enum `ValueInputOption` queda
  confinado al adaptador. gspread queda 100% sustituible: un cliente nativo futuro implementa
  los mismos puertos sin tocar dominio ni aplicación.
- **Sprint 4 de purificación — request builders + cableado de los value objects de
  validación:** `_grid` y los dicts crudos de `setDataValidation`/`addConditionalFormatRule`
  se mueven a `gspreadmanager.infrastructure.request_builders`, que convierte A1 -> GridRange
  (vía gspread) y arma las peticiones desde los VOs del dominio (`DataValidationRule`,
  `ConditionalFormatRule`, `GridRange`). `set_data_validation` y `add_conditional_format` del
  conector pasan a delegar en estos builders. Nuevos golden-tests del módulo. Sin cambios de
  comportamiento (peticiones byte a byte idénticas).
- **Sprint 3 de purificación — estrategias de autenticación + adaptador con caché:** la
  cadena `if-elif` de `GoogleSheetConector._build_client` se reemplaza por una estrategia
  por método (`PreauthorizedClientAuth`, `CredentialsAuth`, `ServiceAccountInfoAuth`,
  `ServiceAccountFileAuth`, `ADCAuth`) detrás del puerto `AuthStrategy`
  (`gspreadmanager.ports.auth`) y una factory `build_auth_strategy`
  (`gspreadmanager.infrastructure.auth`). El caché de cliente y documentos se encapsula en
  `GspreadClientAdapter` (`gspreadmanager.infrastructure.gspread_client`). Nuevos tests
  aíslan auth y caché del conector. Sin cambios de comportamiento (misma precedencia y
  mismos mensajes de error).
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
