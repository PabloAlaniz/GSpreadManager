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

## 🔜 v2.1 — Productividad de datos

- [ ] **Pandas avanzado**: anclar DataFrame en posición arbitraria, `drop_empty_rows/cols`,
      escribir el índice opcional, inferencia de tipos.
- [ ] **Caché opcional de lecturas** con invalidación al escribir.
- [ ] Auto-filtros.

## 🗂️ Backlog (sin priorizar)

- [ ] **Async** (wrapper con threadpool) y **rate limiting** proactivo (token bucket).
- [ ] Paginación/streaming para hojas grandes.
- [ ] **CLI** para operaciones comunes (`gspreadmanager read/append/export`).
- [ ] Named ranges / protected ranges.
- [ ] Export a CSV/Excel.
- [ ] Documentación bilingüe (es/en).
