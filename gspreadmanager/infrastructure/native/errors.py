"""Errores del cliente nativo.

``SheetsApiError`` mapea un error de la Sheets/Drive API (cuerpo ``{"error": {...}}``) a la
jerarquía propia de GSpreadManager, al estilo de ``gspread.exceptions.APIError`` pero sin
depender de gspread ni de ``requests``.
"""

from __future__ import annotations

from gspreadmanager.domain.errors import ApiError


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
