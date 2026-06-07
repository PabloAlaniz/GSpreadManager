# ROADMAP - GSpreadManager

Roadmap posterior al release **1.0.0**, derivado del [análisis competitivo](docs/competitive-analysis.md).
Prioridad por impacto/esfuerzo, reusando el ecosistema (`gspread-*`) donde conviene.

## ✅ Hecho (hasta 1.0.0)

- Packaging moderno (`pyproject.toml`), versión única, `ruff` + `mypy` + `bandit`, CI 3.9–3.12.
- Type hints completos + `py.typed`. `pandas` opcional.
- Fix de bugs (`values_get`/`values_append`, rangos > columna Z), retry + backoff, excepciones propias.
- Gestión de hojas (`create_sheet`/`delete_sheet`/`clear_range`/`find_cell`), integración pandas, context manager.
- Documentación con MkDocs. Primer release estable.

## ✅ v1.1 - Eficiencia y autenticación (HECHO)

- [x] **Caché de cliente + documento** (no re-autenticar al cambiar de pestaña).
- [x] **Autenticación flexible**: service account (file/dict), credenciales de google-auth, cliente ya autorizado, ADC.
- [ ] **Caché opcional de lecturas** con invalidación al escribir.

## ✅ v1.2 - Formato y operaciones de documento (HECHO)

- [x] **Formato de celdas (implementación propia)**: modelo tipado + `format_range`,
      `format_header`, `set_background`, `set_text_format`, `set_number_format`, `freeze`, `merge`.
- [x] **Validación de datos**: `add_dropdown`, `add_checkbox`, `set_data_validation`.
- [x] **Formato condicional**: `add_conditional_format`.
- [x] **Operaciones a nivel documento**: `create_spreadsheet`, `delete_spreadsheet`,
      `copy_spreadsheet`, `list_spreadsheets` (vía Drive).
- [x] **Compartir / permisos**: `share`, `list_permissions`, `remove_permission`.

## v1.3 - Productividad de datos (paridad con gspread-pandas)

- [ ] **Pandas avanzado**: anclar DataFrame en posición arbitraria, `drop_empty_rows/cols`,
      escribir el índice opcional, inferencia de tipos.
- [ ] **Freeze rows/cols, merge cells, auto-filtros**.
- [ ] **Data validation**: dropdowns y checkboxes.

## v2.0 - Async y escala

- [ ] **Soporte async** (wrapper con threadpool al estilo `gspread-asyncio`).
- [ ] **Paginación/streaming** para hojas grandes.
- [ ] **Rate limiting** proactivo (token bucket), además del retry reactivo.

## Backlog (sin priorizar)

- [ ] **CLI** para operaciones comunes (`gspreadmanager read/append/export`).
- [ ] Named ranges / protected ranges.
- [ ] Export a CSV/Excel.
- [ ] Documentación bilingüe (es/en).
