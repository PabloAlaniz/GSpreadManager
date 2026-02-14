# ROADMAP - GSpreadManager

## v0.2.0 - Estabilización Crítica (Prioridad URGENTE)

### Tests (Crítico para paquete PyPI)
- [ ] Setup pytest con fixtures
- [ ] Crear mocks de gspread para tests aislados
- [ ] Tests unitarios para todos los métodos públicos:
  - [ ] `connect_to_sheet()`
  - [ ] `read_sheet_data()` - los 3 formatos de output
  - [ ] `spreadsheet_append()`
  - [ ] `update_cell()` / `update_row()`
  - [ ] `batch_update()`
  - [ ] `get_rows_where_column_equals()`
- [ ] Coverage mínimo: 80%
- [ ] Badge de coverage en README

### CI/CD
- [ ] GitHub Actions con tests en push/PR
- [ ] Matrix de Python versions (3.9, 3.10, 3.11, 3.12)
- [ ] Publicación automática a PyPI en tags

---

## v0.3.0 - Modernización (Prioridad Alta)

### Migración a google-auth
- [ ] Reemplazar oauth2client por google-auth + google-auth-oauthlib
- [ ] Soportar múltiples métodos de autenticación:
  - [ ] Service Account (JSON file)
  - [ ] OAuth2 (user credentials)
  - [ ] Application Default Credentials (ADC)
- [ ] Documentar migración para usuarios existentes

### Type Hints
- [ ] Anotaciones de tipos en todos los métodos
- [ ] Crear archivo py.typed para PEP 561
- [ ] Configurar mypy en CI

### Dependencias
- [ ] Actualizar gspread a versión más reciente
- [ ] Hacer pandas opcional (no forzar instalación)

---

## v0.4.0 - Mejoras de API (Prioridad Media)

### Nuevos Métodos
- [ ] `find_cell(value)` - Buscar celda por valor
- [ ] `clear_range(range)` - Limpiar rango
- [ ] `format_cells(range, format)` - Aplicar formato
- [ ] `create_sheet(name)` - Crear nueva hoja
- [ ] `delete_sheet(name)` - Eliminar hoja

### Context Manager
- [ ] Implementar `__enter__` / `__exit__`
- [ ] Auto-flush de cambios pendientes

### Async Support
- [ ] Versión async de métodos principales
- [ ] Usar httpx en lugar de requests internamente

---

## v1.0.0 - Release Estable

### Documentación
- [ ] Sitio de documentación con MkDocs
- [ ] Guía de migración desde gspread directo
- [ ] Ejemplos de uso comunes (notebooks)
- [ ] API reference completa

### Calidad
- [ ] 90%+ code coverage
- [ ] 0 issues de seguridad (bandit)
- [ ] 0 code smells (ruff/pylint)

### Release
- [ ] Semantic versioning automático
- [ ] CHANGELOG.md automático
- [ ] Anuncio en redes/Medium

---

## Backlog (Sin Priorizar)

- [ ] Soporte para Google Drive (listar archivos, crear spreadsheets)
- [ ] Caché de lecturas para reducir API calls
- [ ] Rate limiting automático
- [ ] Retry con backoff exponencial
- [ ] Integración con pandas más profunda (to_gsheet, from_gsheet)
- [ ] CLI para operaciones comunes
- [ ] Streaming de datos grandes (paginación)
