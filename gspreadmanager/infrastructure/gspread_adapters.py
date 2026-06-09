"""Adaptadores de gspread que implementan los puertos de Sheets.

Cada adaptador envuelve un objeto de gspread y reenvía las llamadas, traduciendo lo
específico (ej. ``value_input_option`` de ``str`` al enum ``ValueInputOption``). Son la
única pieza que conoce la forma concreta de la API de gspread; la capa de aplicación solo
ve los puertos.
"""

from __future__ import annotations

from typing import Any

from gspread.utils import ValueInputOption

from gspreadmanager.ports.sheets import SpreadsheetPort, WorksheetPort


class GspreadWorksheet:
    """Adaptador de ``gspread.Worksheet`` que implementa ``WorksheetPort``."""

    def __init__(self, worksheet: Any) -> None:
        """Envuelve la hoja de gspread."""
        self._ws = worksheet

    @property
    def raw(self) -> Any:
        """Objeto de hoja de gspread subyacente (escape hatch)."""
        return self._ws

    @property
    def id(self) -> int:
        """Id numérico de la hoja."""
        return self._ws.id

    @property
    def title(self) -> str:
        """Nombre de la pestaña."""
        return self._ws.title

    @property
    def spreadsheet(self) -> SpreadsheetPort:
        """Documento al que pertenece la hoja."""
        return GspreadSpreadsheet(self._ws.spreadsheet)

    def update_cell(self, row: int, col: int, value: Any) -> None:
        """Actualiza una celda."""
        self._ws.update_cell(row, col, value)

    def get_all_values(self) -> list[list[str]]:
        """Devuelve todas las filas."""
        return self._ws.get_all_values()

    def append_rows(self, data: list[list[Any]], value_input_option: str) -> Any:
        """Añade filas al final."""
        return self._ws.append_rows(data, value_input_option=ValueInputOption(value_input_option))

    def batch_update(self, range_data: list[dict[str, Any]], value_input_option: str) -> None:
        """Actualiza varios rangos."""
        self._ws.batch_update(range_data, value_input_option=ValueInputOption(value_input_option))

    def col_values(self, col: int) -> list[Any]:
        """Valores de una columna."""
        return self._ws.col_values(col)

    def range(self, name: str) -> list[Any]:
        """Celdas de un rango A1."""
        return self._ws.range(name)

    def row_values(self, row: int) -> list[Any]:
        """Valores de una fila."""
        return self._ws.row_values(row)

    def format(self, ranges: str | list[str], cell_format: dict[str, Any]) -> Any:
        """Aplica un formato ya serializado."""
        return self._ws.format(ranges, cell_format)

    def freeze(self, rows: int | None, cols: int | None) -> Any:
        """Congela filas/columnas."""
        return self._ws.freeze(rows=rows, cols=cols)

    def merge_cells(self, range_name: str, merge_type: str) -> Any:
        """Combina celdas."""
        return self._ws.merge_cells(range_name, merge_type=merge_type)

    def clear(self) -> None:
        """Limpia toda la hoja."""
        self._ws.clear()

    def batch_clear(self, ranges: list[str]) -> None:
        """Limpia varios rangos."""
        self._ws.batch_clear(ranges)

    def find(self, query: str, case_sensitive: bool) -> Any:
        """Busca la primera celda coincidente."""
        return self._ws.find(query, case_sensitive=case_sensitive)

    def update(self, values: list[list[Any]], value_input_option: str) -> Any:
        """Escribe ``values`` desde A1."""
        return self._ws.update(values, value_input_option=ValueInputOption(value_input_option))


class GspreadSpreadsheet:
    """Adaptador de ``gspread.Spreadsheet`` que implementa ``SpreadsheetPort``."""

    def __init__(self, spreadsheet: Any) -> None:
        """Envuelve el documento de gspread."""
        self._ss = spreadsheet

    @property
    def raw(self) -> Any:
        """Documento de gspread subyacente (escape hatch)."""
        return self._ss

    @property
    def sheet1(self) -> WorksheetPort:
        """Primera hoja del documento."""
        return GspreadWorksheet(self._ss.sheet1)

    def worksheet(self, name: str) -> WorksheetPort:
        """Hoja por nombre."""
        return GspreadWorksheet(self._ss.worksheet(name))

    def add_worksheet(self, title: str, rows: int, cols: int, index: int | None) -> WorksheetPort:
        """Crea una nueva hoja y la devuelve."""
        return GspreadWorksheet(self._ss.add_worksheet(title, rows=rows, cols=cols, index=index))

    def delete_worksheet(self, title: str) -> None:
        """Elimina la hoja con el nombre dado."""
        self._ss.del_worksheet(self._ss.worksheet(title))

    def values_get(self, a1_range: str) -> Any:
        """Lee un rango A1."""
        return self._ss.values_get(a1_range)

    def values_append(self, a1_range: str, params: dict[str, Any], body: dict[str, Any]) -> Any:
        """Añade valores a un rango."""
        return self._ss.values_append(a1_range, params, body)

    def batch_update(self, body: dict[str, Any]) -> Any:
        """Envía una petición ``spreadsheets.batchUpdate``."""
        return self._ss.batch_update(body)

    def get_metadata(self, ranges: list[str] | None, fields: str) -> dict[str, Any]:
        """Lee metadata del documento (``spreadsheets.get``) vía gspread."""
        params: dict[str, Any] = {"fields": fields}
        if ranges is not None:
            params["ranges"] = ranges
        result: dict[str, Any] = self._ss.fetch_sheet_metadata(params)
        return result

    def export(self, mime_type: str) -> bytes:
        """Exporta el documento (gspread ``Spreadsheet.export``)."""
        data: bytes = self._ss.export(format=mime_type)
        return data

    def share(
        self,
        email_address: str,
        perm_type: str,
        role: str,
        notify: bool,
        email_message: str | None,
        with_link: bool,
    ) -> Any:
        """Comparte el documento."""
        return self._ss.share(
            email_address,
            perm_type=perm_type,
            role=role,
            notify=notify,
            email_message=email_message,
            with_link=with_link,
        )

    def list_permissions(self) -> list[dict[str, Any]]:
        """Lista los permisos."""
        return self._ss.list_permissions()

    def remove_permissions(self, value: str, role: str) -> list[str]:
        """Quita permisos; devuelve los IDs eliminados."""
        return self._ss.remove_permissions(value, role=role)
