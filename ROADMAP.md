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
`infrastructure/` detrás de puertos nominales.

- [x] **Puertos nominales `WorksheetPort`/`SpreadsheetPort`/`ClientPort` + adaptadores**
      sobre gspread (opción B): resuelto el tipado y gspread queda 100% sustituible.
- [ ] **Reemplazo total por cliente propio nativo** (REST directo con google-auth) detrás de
      los mismos puertos. **Disparador (política):** se ejecuta si gspread es declarado EOL o
      su repositorio queda inactivo (sin releases ni actividad de mantenimiento por un período
      prolongado). Mientras tanto, gspread sigue como adaptador por defecto.

## 🔜 v2.1 — Paridad con gspread/pygsheets

Cerrar lo que aún nos separa (ver [análisis competitivo](docs/competitive-analysis.md)):

- [x] **Abrir por key / URL** (`open_by_key`, `open_by_url`), además de por nombre.
- [x] **Type inference** opcional al leer (`numericise`): `read(numericise=True)`.
- [x] **Filas/columnas estructurales**: insertar/eliminar/redimensionar/ocultar.
- [x] **Notas de celda**, **named ranges** y **protected ranges**.
- [x] **Sort / basic filter**, **unmerge**, **tab color**, **export** (xlsx/csv/pdf/tsv/ods/html).
- [ ] **Import CSV** (volcar un CSV/archivo a la hoja) — pendiente, fuera del Sprint 4.
- [x] **Pandas avanzado**: anclaje en posición arbitraria (`start_cell`), `drop_empty_rows/cols`,
      índice opcional (`index_col`/`include_index`).

## 🌟 Diferenciación (donde el ecosistema es débil)

- [ ] **Async nativo** (`asyncio` sobre `httpx`, no threadpool) detrás de los puertos.
- [ ] **Modelos de fila tipados** (dataclasses/Pydantic) con esquema y validación.
- [x] **Backend de DataFrame pluggable** (pandas + **polars**) vía el `DataFramePort`
      (`SheetManager(dataframe_backend=...)`).
- [ ] **Caché de lecturas con invalidación** al escribir.
- [x] **Fake in-memory** del backend para que los usuarios testeen sin red
      (`gspreadmanager.testing.InMemoryBackend`).

## 🗂️ Backlog (sin priorizar)

- [ ] **Rate limiting** proactivo (token bucket) además del retry reactivo.
- [ ] Paginación/streaming para hojas grandes; operaciones de alto nivel (`upsert`, find-or-create).
- [ ] **CLI** (`gspreadmanager read/append/export`).
- [ ] Documentación bilingüe (es/en).
