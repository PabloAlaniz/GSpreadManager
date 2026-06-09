"""Errores del cliente nativo.

``SheetsApiError`` mapea un error de la Sheets/Drive API (cuerpo ``{"error": {...}}``) a la
jerarquía propia de GSpreadManager, al estilo de ``gspread.exceptions.APIError`` pero sin
depender de gspread ni de ``requests``.
"""

from __future__ import annotations

from gspreadmanager.domain.errors import GSpreadManagerError


class SheetsApiError(GSpreadManagerError):
    """Error devuelto por la Google Sheets/Drive API (status HTTP no exitoso)."""

    def __init__(self, code: int, status: str, message: str) -> None:
        """Guarda el código HTTP, el ``status`` de la API y el mensaje."""
        super().__init__(f"[{code} {status}] {message}")
        self.code = code
        self.status = status
        self.message = message
