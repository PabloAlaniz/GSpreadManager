"""Excepciones propias de GSpreadManager."""

from __future__ import annotations


class GSpreadManagerError(Exception):
    """Error base para todas las operaciones de GSpreadManager."""


class InsertError(GSpreadManagerError):
    """Se lanza cuando falla la inserción de datos en una hoja de cálculo."""
