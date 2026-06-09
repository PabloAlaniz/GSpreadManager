"""Conversión de filas/columnas a notación A1, sin dependencias de gspread.

Para el spike del cliente nativo: demuestra que las utilidades de A1 (lo poco "no trivial"
que aporta gspread más allá del transporte) también se pueden reemplazar con pocas líneas.
"""

from __future__ import annotations

import re

_A1_CELL = re.compile(r"^([A-Za-z]*)([0-9]*)$")


def column_to_letter(col: int) -> str:
    """Convierte un índice de columna 1-based a letras ('A', 'Z', 'AA', ...)."""
    if col < 1:
        raise ValueError(f"Columna inválida: {col} (debe ser >= 1).")
    letters = ""
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def letter_to_column(letters: str) -> int:
    """Convierte letras de columna ('A', 'AA') a su índice 1-based."""
    col = 0
    for ch in letters.upper():
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return col


def rowcol_to_a1(row: int, col: int) -> str:
    """Convierte (fila, columna) 1-based a notación A1 (ej. (2, 3) -> 'C2')."""
    if row < 1:
        raise ValueError(f"Fila inválida: {row} (debe ser >= 1).")
    return f"{column_to_letter(col)}{row}"


def _split_cell(cell: str) -> tuple[int | None, int | None]:
    """Separa una ancla A1 ('A1', 'A', '10') en (columna, fila) 1-based o None."""
    match = _A1_CELL.match(cell)
    if not match or not cell:
        raise ValueError(f"Ancla A1 inválida: {cell!r}.")
    letters, digits = match.groups()
    col = letter_to_column(letters) if letters else None
    row = int(digits) if digits else None
    return col, row


def a1_to_grid_range(a1_range: str, sheet_id: int) -> dict[str, int]:
    """Convierte un rango A1 en un ``GridRange`` (0-based, fin exclusivo) para ``sheet_id``.

    Equivalente nativo de ``gspread.utils.a1_range_to_grid_range``. Soporta celdas ('A1'),
    rangos ('A1:C10'), columnas ('A:C') y filas ('1:5'); ignora el prefijo de pestaña.
    """
    if "!" in a1_range:
        a1_range = a1_range.split("!", 1)[1]
    start_str, _, end_str = a1_range.partition(":")
    if not end_str:
        end_str = start_str
    start_col, start_row = _split_cell(start_str)
    end_col, end_row = _split_cell(end_str)

    grid: dict[str, int] = {"sheetId": sheet_id}
    if start_row is not None and end_row is not None:
        grid["startRowIndex"] = start_row - 1
        grid["endRowIndex"] = end_row
    if start_col is not None and end_col is not None:
        grid["startColumnIndex"] = start_col - 1
        grid["endColumnIndex"] = end_col
    return grid
