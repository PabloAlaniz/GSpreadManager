"""Traducción de excepciones de gspread a la jerarquía de errores del dominio.

Única pieza que conoce ``gspread.exceptions``: los adaptadores se decoran con
``translates_gspread_errors`` para que ninguna excepción de gspread escape al usuario ni a
la política de reintentos (que opera sobre ``ApiError`` del dominio).
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from gspread import exceptions as gspread_exceptions

from gspreadmanager.domain.errors import (
    CellNotFoundError,
    GSpreadManagerError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
    api_error_from_status,
)

C = TypeVar("C")

# gspread < 5 lanzaba ``CellNotFound`` desde ``find``; en gspread >= 5 devuelve None.
_CELL_NOT_FOUND: type[Exception] | None = getattr(gspread_exceptions, "CellNotFound", None)


def _status_code(error: gspread_exceptions.APIError) -> int | None:
    """Extrae el código de estado HTTP de un APIError de gspread."""
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    code = getattr(error, "code", None)
    return code if isinstance(code, int) else None


def translate_gspread_error(exc: Exception) -> GSpreadManagerError:
    """Devuelve el error de dominio equivalente a una excepción de gspread."""
    if isinstance(exc, gspread_exceptions.SpreadsheetNotFound):
        return SpreadsheetNotFoundError(str(exc) or "No se encontró el documento.")
    if isinstance(exc, gspread_exceptions.WorksheetNotFound):
        # gspread usa el título de la hoja como mensaje.
        title = str(exc)
        message = f"No existe la hoja {title!r}." if title else "No existe la hoja pedida."
        return WorksheetNotFoundError(message)
    if _CELL_NOT_FOUND is not None and isinstance(exc, _CELL_NOT_FOUND):
        return CellNotFoundError(str(exc) or "No se encontró la celda buscada.")
    if isinstance(exc, gspread_exceptions.APIError):
        return api_error_from_status(_status_code(exc), str(exc))
    return GSpreadManagerError(str(exc))


def _wrapped(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except gspread_exceptions.GSpreadException as exc:
            raise translate_gspread_error(exc) from exc

    return wrapper


def translates_gspread_errors(cls: type[C]) -> type[C]:
    """Decora un adaptador: sus métodos y properties públicos traducen errores de gspread."""
    for name, attr in list(vars(cls).items()):
        if name.startswith("_"):
            continue
        if isinstance(attr, property) and attr.fget is not None:
            translated = property(_wrapped(attr.fget), attr.fset, attr.fdel, attr.__doc__)
            setattr(cls, name, translated)
        elif inspect.isfunction(attr):
            setattr(cls, name, _wrapped(attr))
    return cls
