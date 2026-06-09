"""Puerto de autenticación.

Abstrae cómo se obtiene un cliente de gspread autorizado. El facade depende de este
puerto, no de los detalles de google-auth ni de los métodos concretos.
"""

from __future__ import annotations

from typing import Any, Protocol


class AuthStrategy(Protocol):
    """Construye y devuelve un cliente de gspread autorizado."""

    def authorize(self) -> Any:
        """Devuelve un cliente de gspread listo para abrir documentos."""
        ...
