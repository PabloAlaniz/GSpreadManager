"""Errores del cliente nativo.

``SheetsApiError`` mapea un error de la Sheets/Drive API (cuerpo ``{"error": {...}}``) a la
jerarquía propia de GSpreadManager, al estilo de ``gspread.exceptions.APIError`` pero sin
depender de gspread ni de ``requests``.
"""

from __future__ import annotations

from gspreadmanager.domain.errors import ApiError, PermissionDeniedError, QuotaExceededError

_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_FORBIDDEN = 403


class SheetsApiError(ApiError):
    """Error devuelto por la Google Sheets/Drive API (status HTTP no exitoso).

    Subclase de ``ApiError`` del dominio: expone ``status_code`` para que la política de
    reintentos lo trate igual que a los errores traducidos del adaptador de gspread.
    """

    def __init__(self, code: int, status: str, message: str) -> None:
        """Guarda el código HTTP, el ``status`` de la API y el mensaje."""
        super().__init__(f"[{code} {status}] {message}", status_code=code)
        self.code = code
        self.status = status
        self.message = message


class SheetsQuotaExceededError(SheetsApiError, QuotaExceededError):
    """Cuota excedida (HTTP 429) devuelta por la API en el backend nativo.

    Hereda de ``QuotaExceededError`` para que el código del usuario capture el mismo tipo
    sin importar el backend.
    """


class SheetsPermissionDeniedError(SheetsApiError, PermissionDeniedError):
    """Permiso denegado (HTTP 403) devuelto por la API en el backend nativo."""


def build_sheets_api_error(code: int, status: str, message: str) -> SheetsApiError:
    """Construye el ``SheetsApiError`` más específico según el código de estado HTTP."""
    if code == _HTTP_TOO_MANY_REQUESTS:
        return SheetsQuotaExceededError(code, status, message)
    if code == _HTTP_FORBIDDEN:
        return SheetsPermissionDeniedError(code, status, message)
    return SheetsApiError(code, status, message)
