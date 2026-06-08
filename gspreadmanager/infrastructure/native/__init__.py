"""Spike (experimental) de un cliente nativo de Google Sheets/Drive vía REST.

Implementa los mismos puertos que los adaptadores de gspread (``ports.sheets``) usando
``google-auth`` para autorizar una sesión HTTP y llamando directamente a la Sheets API v4 /
Drive API v3. **No está cableado** en el facade: gspread sigue siendo el adaptador por
defecto. Existe para validar factibilidad y medir esfuerzo (ver ADR 0001 / ROADMAP).

Cobertura del spike: autenticación, apertura por nombre (Drive), lectura (con padding),
escrituras (update/append/batch values), formato/freeze/merge y validación/condicional
(``spreadsheets:batchUpdate``), gestión de hojas, permisos de Drive (share/list/remove),
``find``/``range`` y conversión A1 <-> GridRange propia. Pendientes menores: mover a carpeta
en ``create``, semántica de ``with_link`` y mapeo de errores de la API a excepciones propias.
"""
