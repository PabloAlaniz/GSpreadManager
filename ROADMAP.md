# ROADMAP - GSpreadManager

Prioridad por impacto/esfuerzo. Ver también el [análisis competitivo](docs/competitive-analysis.md)
y las [decisiones de arquitectura (ADR)](docs/adr/0001-dependencia-de-gspread.md).

## ✅ Hecho (1.0 – 1.2)

- Packaging moderno (`pyproject.toml`), `ruff` + `mypy` + `bandit`, CI 3.9–3.12, `py.typed`.
- Retry + backoff, excepciones propias, fixes de rangos (> columna Z), `pandas` opcional.
- Caché de cliente/documento y **autenticación flexible** (service account file/dict,
  credenciales de google-auth, cliente autorizado, ADC).
- **Formato propio** (modelo tipado: `format_range`/`format_header`/`set_*`/`freeze`/`merge`),
  **validación** (`add_dropdown`/`add_checkbox`), **formato condicional**.
- **Documento (Drive)**: crear/copiar/listar/borrar; **compartir/permisos**.
- Documentación con MkDocs.

## ✅ v2.0 — Refactor a Clean Architecture / DDD (HECHO)

Reescritura interna a una arquitectura por capas, con tooling estricto y un API nuevo sin
estado mutable. **Sin usuarios previos, se hizo el corte limpio** (se eliminó el API 1.x).

- [x] **Tooling estricto**: ruff ampliado + `mypy --strict` (incluye tests).
- [x] **Capa de dominio**: value objects inmutables (formato, rangos, reglas) + errores.
- [x] **Puertos**: `AuthStrategy`, `RetryPolicy`, `DataFramePort`.
- [x] **Infraestructura**: estrategias de auth, adaptador de cliente con caché, retry policy,
      request builders, adaptador de pandas.
- [x] **Capa de aplicación**: 7 servicios de casos de uso (sin gspread, testeables con fakes).
- [x] **API nuevo**: `SheetManager` + `WorksheetContext` (handles inmutables, sin "hoja activa"
      global ni efectos colaterales de `tab_name`). Eliminada `GoogleSheetConector`.

## 🧭 Independencia de gspread

Ver [ADR 0001](docs/adr/0001-dependencia-de-gspread.md). gspread quedó aislado en
`infrastructure/` detrás de puertos nominales. **Disparador cumplido (jun-2026):** gspread
quedó sin mantenimiento activo, así que la opción C está en ejecución.

- [x] **Puertos nominales `WorksheetPort`/`SpreadsheetPort`/`ClientPort` + adaptadores**
      sobre gspread (opción B): resuelto el tipado y gspread queda 100% sustituible.
- [x] **Cliente nativo opt-in** (`SheetManager(backend="native")`): REST directo con
      google-auth detrás de los mismos puertos, con caché de documentos, timeouts y mapeo
      de errores a la jerarquía propia (Sprint 2).
- [x] **gspread como extra opcional** (`pip install "GSpreadManager[gspread]"`) con
      `backend="auto"`: usa gspread si está instalado, si no el nativo. El núcleo solo
      depende de google-auth (Sprint 3). Benchmarks: `benchmarks/run_benchmarks.py`.
- [ ] **Nativo como default explícito** (independiente de qué haya instalado) — release 3.0.

## ✅ v2.1 — Paridad con gspread/pygsheets + diferenciación (RELEASED)

Cerró lo que nos separaba y sumó capacidades que el ecosistema no ofrece, todo sobre la
arquitectura hexagonal de la 2.0 (ver [análisis competitivo](docs/competitive-analysis.md)):

- [x] **Abrir por key / URL** (`open_by_key`, `open_by_url`), además de por nombre.
- [x] **Type inference** opcional al leer (`numericise`): `read(numericise=True)`.
- [x] **Filas/columnas estructurales**: insertar/eliminar/redimensionar/ocultar.
- [x] **Notas de celda**, **named ranges** y **protected ranges**.
- [x] **Sort / basic filter**, **unmerge**, **tab color**, **export** (xlsx/csv/pdf/tsv/ods/html).
- [x] **Pandas avanzado**: anclaje en posición arbitraria (`start_cell`), `drop_empty_rows/cols`,
      índice opcional (`index_col`/`include_index`).

### Diferenciación incluida en v2.1 (donde el ecosistema es débil)

- [x] **Modelos de fila tipados** (dataclasses) con coerción y validación
      (`read_as`/`append_models`/`write_models`). Pydantic: pendiente.
- [x] **Backend de DataFrame pluggable** (pandas + **polars**) vía el `DataFramePort`
      (`SheetManager(dataframe_backend=...)`).
- [x] **Caché de lecturas con invalidación** al escribir (`SheetManager(cache=True)`).
- [x] **Fake in-memory** del backend para que los usuarios testeen sin red
      (`gspreadmanager.testing.InMemoryBackend`).
- [x] **Rate limiting** proactivo (token bucket) además del retry reactivo
      (`SheetManager(rate_limit=...)`).
- [x] **CLI** (`gspreadmanager read/append/export/share`).

## 🔜 Plan de 10 sprints (v2.2 → v3.0)

Plan derivado de la auditoría SOLID/Clean Architecture/DDD de junio 2026 y del
[análisis competitivo](docs/competitive-analysis.md). **Contexto clave:** los maintainers de
gspread anunciaron que no pueden seguir manteniéndolo, lo que activa el disparador del
[ADR 0001](docs/adr/0001-dependencia-de-gspread.md) para promover el cliente nativo.

1. **Pureza de capas y errores de dominio (v2.2.0):** jerarquía completa de errores
   (`ApiError`, `QuotaExceededError`, `PermissionDeniedError`, `*NotFoundError`), traducción
   de todas las excepciones de gspread en los adaptadores, retry desacoplado de gspread,
   helpers A1 promovidos al dominio (adiós a `gspread.utils` en aplicación) y logging
   estructurado opt-in.
2. **Cliente nativo, parte 1 (v2.2):** ejecutar ADR 0001 — `SheetManager(backend="native")`
   opt-in, paridad total del spike con la facade, timeouts, tests de integración opcionales.
3. **Cliente nativo, parte 2:** gspread pasa a extra opcional (`[gspread]`), benchmarks
   nativo vs gspread, hardening (paginación Drive, refresh de credenciales).
4. **Paridad final con el ecosistema (v2.3):** import CSV, update_title/locale/timezone,
   listar/abrir pestañas por índice-id, find/replace, copy_to entre documentos, value render
   options (fórmulas).
5. **Operaciones de alto nivel (v2.4):** `upsert` por clave (también para modelos),
   `worksheet_or_create`, `update_where`/`delete_where`, chunking automático de batch.
6. **Hojas grandes (v2.5):** `iter_rows` paginado, lecturas/escrituras en streaming,
   caché v2 (TTL, LRU, invalidación por rango).
7. **Pydantic y esquema avanzado (v2.6):** puerto `ModelCodec` (dataclasses + Pydantic v2
   opcional), `ensure_schema` con reporte de drift, coerciones extra (Decimal/Enum/Literal).
8. **API v4 profunda (v2.7):** charts, pivot tables, banding y developer metadata como
   value objects + requests (terreno donde solo pygsheets llega a medias).
9. **Async nativo, parte 1 (v3.0a):** puertos async, cliente nativo sobre httpx
   (extra `[async]`), retry y rate limiting con `asyncio.sleep`.
10. **Async parte 2 + release 3.0:** `AsyncSheetManager`, in-memory async, **nativo como
    backend default** (culmina ADR 0001), documentación bilingüe es/en y release mayor.
