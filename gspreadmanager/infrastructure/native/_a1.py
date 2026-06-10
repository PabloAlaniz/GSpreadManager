"""Conversión de filas/columnas a notación A1 para el cliente nativo.

Las utilidades puras viven en el dominio (``gspreadmanager.domain.values.ranges``); este
módulo las re-exporta y agrega ``a1_to_grid_range`` (la forma dict que consume la API).
"""

from __future__ import annotations

from gspreadmanager.domain.values.ranges import (
    GridRange,
    column_to_letter,
    letter_to_column,
    rowcol_to_a1,
)

__all__ = ["a1_to_grid_range", "column_to_letter", "letter_to_column", "rowcol_to_a1"]


def a1_to_grid_range(a1_range: str, sheet_id: int) -> dict[str, int]:
    """Convierte un rango A1 en un dict ``GridRange`` (0-based, fin exclusivo) para ``sheet_id``.

    Equivalente nativo de ``gspread.utils.a1_range_to_grid_range``. Soporta celdas ('A1'),
    rangos ('A1:C10'), columnas ('A:C') y filas ('1:5'); ignora el prefijo de pestaña.
    """
    return GridRange.from_a1(a1_range, sheet_id).to_dict()
