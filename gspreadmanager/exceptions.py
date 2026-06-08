"""Shim de compatibilidad: las excepciones viven ahora en ``domain.errors``.

Re-exporta la jerarquía pública para mantener estable ``gspreadmanager.exceptions``.
El código nuevo debería importar desde ``gspreadmanager.domain.errors``.
"""

from __future__ import annotations

from .domain.errors import GSpreadManagerError, InsertError

__all__ = ["GSpreadManagerError", "InsertError"]
