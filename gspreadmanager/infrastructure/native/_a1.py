"""Conversión de filas/columnas a notación A1, sin dependencias de gspread.

Para el spike del cliente nativo: demuestra que las utilidades de A1 (lo poco "no trivial"
que aporta gspread más allá del transporte) también se pueden reemplazar con pocas líneas.
"""

from __future__ import annotations


def column_to_letter(col: int) -> str:
    """Convierte un índice de columna 1-based a letras ('A', 'Z', 'AA', ...)."""
    if col < 1:
        raise ValueError(f"Columna inválida: {col} (debe ser >= 1).")
    letters = ""
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def rowcol_to_a1(row: int, col: int) -> str:
    """Convierte (fila, columna) 1-based a notación A1 (ej. (2, 3) -> 'C2')."""
    if row < 1:
        raise ValueError(f"Fila inválida: {row} (debe ser >= 1).")
    return f"{column_to_letter(col)}{row}"
