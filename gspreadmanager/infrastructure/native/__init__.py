"""Cliente nativo de Google Sheets/Drive vía REST (sin gspread).

Implementa los mismos puertos que los adaptadores de gspread (``ports.sheets``) usando
``google-auth`` para autorizar una sesión HTTP y llamando directamente a la Sheets API v4 /
Drive API v3. Se activa con ``SheetManager(backend="native")``; gspread sigue siendo el
default hasta la 3.0 (ver ADR 0001 / ROADMAP).

Cobertura: autenticación, apertura por nombre/key (con caché), lectura (con padding),
escrituras (update/append/batch values), formato/freeze/merge y validación/condicional
(``spreadsheets:batchUpdate``), gestión de hojas, permisos de Drive (share/list/remove),
``find``/``range``, conversión A1 <-> GridRange del dominio, timeouts por petición y mapeo
de errores de la API a la jerarquía propia (``SheetsApiError`` es un ``ApiError``).
Pendientes menores: mover a carpeta en ``create`` y semántica de ``with_link``.
"""

from .async_client import AsyncSheetsApiClient
from .async_http import AuthorizedAsyncSession, build_async_session
from .http import DEFAULT_HTTP_TIMEOUT, TimeoutHttpSession, build_authorized_session
from .sheets_api_client import SheetsApiClient

__all__ = [
    "DEFAULT_HTTP_TIMEOUT",
    "AsyncSheetsApiClient",
    "AuthorizedAsyncSession",
    "SheetsApiClient",
    "TimeoutHttpSession",
    "build_async_session",
    "build_authorized_session",
]
