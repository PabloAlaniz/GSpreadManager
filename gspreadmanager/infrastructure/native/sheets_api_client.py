"""Cliente nativo (spike) de Google Sheets/Drive vía REST, detrás de los puertos.

Implementa ``ClientPort`` / ``SpreadsheetPort`` / ``WorksheetPort`` llamando a la Sheets API
v4 y la Drive API v3 a través de una ``HttpSession`` (inyectable). **No está cableado** en el
facade. Lo no cubierto por el spike lanza ``NotImplementedError`` con la etiqueta "spike".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from gspreadmanager.config import DEFAULT_VALUE_INPUT_OPTION
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.ports.sheets import SpreadsheetPort, WorksheetPort

from ._a1 import rowcol_to_a1
from .http import HttpSession

SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


def _spike(method: str) -> NotImplementedError:
    """Marca una operación aún no cubierta por el spike del cliente nativo."""
    return NotImplementedError(f"spike: '{method}' aún no implementado en el cliente nativo.")


@dataclass(frozen=True)
class Cell:
    """Celda encontrada por ``find`` (equivalente nativo de ``gspread.Cell``)."""

    row: int
    col: int
    value: str


class SheetsApiClient:
    """``ClientPort`` nativo: abre documentos (Drive) y opera a nivel Drive/Sheets."""

    def __init__(self, session: HttpSession) -> None:
        """Recibe una sesión HTTP autorizada (ver ``build_authorized_session``)."""
        self._session = session

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _post(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = self._session.post(url, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def open(self, doc_name: str) -> SpreadsheetPort:
        """Resuelve el documento por nombre (Drive) y carga sus hojas (Sheets)."""
        files = self._get(
            DRIVE_FILES,
            params={
                "q": f"name = '{doc_name}' and mimeType = '{_SPREADSHEET_MIME}' and trashed = false",
                "fields": "files(id,name)",
            },
        ).get("files", [])
        if not files:
            raise GSpreadManagerError(f"No se encontró el documento '{doc_name}'.")
        spreadsheet_id = files[0]["id"]
        meta = self._get(
            f"{SHEETS_BASE}/{spreadsheet_id}",
            params={"fields": "sheets.properties(sheetId,title)"},
        )
        sheets = [
            (s["properties"]["title"], s["properties"]["sheetId"]) for s in meta.get("sheets", [])
        ]
        return NativeSpreadsheet(self._session, spreadsheet_id, sheets)

    def create(self, title: str, folder_id: str | None) -> Any:
        """Crea un documento (Sheets API). ``folder_id`` aún no se mueve (spike)."""
        return self._post(SHEETS_BASE, json={"properties": {"title": title}})

    def del_spreadsheet(self, file_id: str) -> None:
        """Elimina un documento (Drive)."""
        response = self._session.delete(f"{DRIVE_FILES}/{file_id}")
        response.raise_for_status()

    def copy(
        self, file_id: str, title: str | None, copy_permissions: bool, folder_id: str | None
    ) -> Any:
        """Copia un documento (Drive ``files.copy``)."""
        body: dict[str, Any] = {}
        if title is not None:
            body["name"] = title
        if folder_id is not None:
            body["parents"] = [folder_id]
        return self._post(f"{DRIVE_FILES}/{file_id}/copy", json=body)

    def list_spreadsheet_files(
        self, title: str | None, folder_id: str | None
    ) -> list[dict[str, Any]]:
        """Lista documentos accesibles (Drive)."""
        clauses = [f"mimeType = '{_SPREADSHEET_MIME}'", "trashed = false"]
        if title is not None:
            clauses.append(f"name = '{title}'")
        if folder_id is not None:
            clauses.append(f"'{folder_id}' in parents")
        files: list[dict[str, Any]] = self._get(
            DRIVE_FILES, params={"q": " and ".join(clauses), "fields": "files(id,name)"}
        ).get("files", [])
        return files


class NativeSpreadsheet:
    """``SpreadsheetPort`` nativo: opera sobre un documento por su id."""

    def __init__(
        self, session: HttpSession, spreadsheet_id: str, sheets: list[tuple[str, int]]
    ) -> None:
        """Recibe la sesión, el id del documento y la lista (título, sheetId) de sus hojas."""
        self._session = session
        self._id = spreadsheet_id
        self._sheets = sheets

    @property
    def raw_id(self) -> str:
        """Id del documento (escape hatch del spike)."""
        return self._id

    def _post(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = self._session.post(url, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def _sheet_id(self, title: str) -> int:
        for name, sheet_id in self._sheets:
            if name == title:
                return sheet_id
        raise GSpreadManagerError(f"No existe la hoja '{title}'.")

    @property
    def sheet1(self) -> WorksheetPort:
        """Primera hoja del documento."""
        if not self._sheets:
            raise GSpreadManagerError("El documento no tiene hojas.")
        title, sheet_id = self._sheets[0]
        return NativeWorksheet(self, self._session, self._id, title, sheet_id)

    def worksheet(self, name: str) -> WorksheetPort:
        """Hoja por nombre."""
        return NativeWorksheet(self, self._session, self._id, name, self._sheet_id(name))

    def add_worksheet(self, title: str, rows: int, cols: int, index: int | None) -> WorksheetPort:
        """Crea una hoja vía ``spreadsheets:batchUpdate`` (addSheet) y la devuelve."""
        props: dict[str, Any] = {
            "title": title,
            "gridProperties": {"rowCount": rows, "columnCount": cols},
        }
        if index is not None:
            props["index"] = index
        result = self.batch_update({"requests": [{"addSheet": {"properties": props}}]})
        sheet_id = result["replies"][0]["addSheet"]["properties"]["sheetId"]
        self._sheets.append((title, sheet_id))
        return NativeWorksheet(self, self._session, self._id, title, sheet_id)

    def delete_worksheet(self, title: str) -> None:
        """Elimina una hoja vía ``spreadsheets:batchUpdate`` (deleteSheet)."""
        sheet_id = self._sheet_id(title)
        self.batch_update({"requests": [{"deleteSheet": {"sheetId": sheet_id}}]})
        self._sheets = [(n, sid) for (n, sid) in self._sheets if n != title]

    def values_get(self, a1_range: str) -> Any:
        """``spreadsheets.values.get``."""
        response = self._session.get(f"{SHEETS_BASE}/{self._id}/values/{quote(a1_range, safe='')}")
        response.raise_for_status()
        return response.json()

    def values_append(self, a1_range: str, params: dict[str, Any], body: dict[str, Any]) -> Any:
        """``spreadsheets.values.append``."""
        return self._post(
            f"{SHEETS_BASE}/{self._id}/values/{quote(a1_range, safe='')}:append",
            params=params,
            json=body,
        )

    def batch_update(self, body: dict[str, Any]) -> Any:
        """``spreadsheets:batchUpdate`` (formato, validación, gestión de hojas)."""
        return self._post(f"{SHEETS_BASE}/{self._id}:batchUpdate", json=body)

    def share(
        self,
        email_address: str,
        perm_type: str,
        role: str,
        notify: bool,
        email_message: str | None,
        with_link: bool,
    ) -> Any:
        """Comparte el documento (Drive permissions)."""
        raise _spike("spreadsheet.share")

    def list_permissions(self) -> list[dict[str, Any]]:
        """Lista permisos (Drive permissions)."""
        raise _spike("spreadsheet.list_permissions")

    def remove_permissions(self, value: str, role: str) -> list[str]:
        """Quita permisos (Drive permissions)."""
        raise _spike("spreadsheet.remove_permissions")


class NativeWorksheet:
    """``WorksheetPort`` nativo: opera sobre una hoja por su título/sheetId."""

    def __init__(
        self,
        spreadsheet: NativeSpreadsheet,
        session: HttpSession,
        spreadsheet_id: str,
        title: str,
        sheet_id: int,
    ) -> None:
        """Recibe el documento padre, la sesión y la identidad de la hoja."""
        self._parent = spreadsheet
        self._session = session
        self._ss_id = spreadsheet_id
        self._title = title
        self._sheet_id = sheet_id

    @property
    def id(self) -> int:
        """Id numérico de la hoja (sheetId)."""
        return self._sheet_id

    @property
    def title(self) -> str:
        """Nombre de la pestaña."""
        return self._title

    @property
    def spreadsheet(self) -> SpreadsheetPort:
        """Documento al que pertenece."""
        return self._parent

    def _values_url(self, a1_range: str) -> str:
        return f"{SHEETS_BASE}/{self._ss_id}/values/{quote(a1_range, safe='')}"

    def _post(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = self._session.post(url, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def get_all_values(self) -> list[list[str]]:
        """Lee toda la hoja (``values.get`` con el título como rango)."""
        data = self._parent.values_get(self._title)
        values: list[list[str]] = data.get("values", [])
        return values

    def update_cell(self, row: int, col: int, value: Any) -> None:
        """Actualiza una celda (``values.update``)."""
        a1 = f"{self._title}!{rowcol_to_a1(row, col)}"
        response = self._session.put(
            self._values_url(a1),
            params={"valueInputOption": DEFAULT_VALUE_INPUT_OPTION},
            json={"values": [[value]]},
        )
        response.raise_for_status()

    def append_rows(self, data: list[list[Any]], value_input_option: str) -> Any:
        """Añade filas al final (``values.append``)."""
        return self._post(
            f"{self._values_url(self._title)}:append",
            params={"valueInputOption": value_input_option, "insertDataOption": "INSERT_ROWS"},
            json={"values": data},
        )

    def batch_update(self, range_data: list[dict[str, Any]], value_input_option: str) -> None:
        """Actualiza varios rangos (``values:batchUpdate``)."""
        self._post(
            f"{SHEETS_BASE}/{self._ss_id}/values:batchUpdate",
            json={"valueInputOption": value_input_option, "data": range_data},
        )

    def update(self, values: list[list[Any]], value_input_option: str) -> Any:
        """Escribe ``values`` desde A1 (``values.update``)."""
        response = self._session.put(
            self._values_url(self._title),
            params={"valueInputOption": value_input_option},
            json={"values": values},
        )
        response.raise_for_status()
        return response.json()

    def clear(self) -> None:
        """Limpia toda la hoja (``values.clear``)."""
        response = self._session.post(f"{self._values_url(self._title)}:clear")
        response.raise_for_status()

    def batch_clear(self, ranges: list[str]) -> None:
        """Limpia varios rangos (``values:batchClear``)."""
        self._post(f"{SHEETS_BASE}/{self._ss_id}/values:batchClear", json={"ranges": ranges})

    def col_values(self, col: int) -> list[Any]:
        """Valores de una columna (derivado de ``get_all_values``)."""
        return [row[col - 1] if col - 1 < len(row) else "" for row in self.get_all_values()]

    def row_values(self, row: int) -> list[Any]:
        """Valores de una fila (derivado de ``get_all_values``)."""
        values = self.get_all_values()
        return values[row - 1] if 0 < row <= len(values) else []

    def find(self, query: str, case_sensitive: bool) -> Any:
        """Busca la primera celda con valor ``query`` (escaneo client-side)."""
        needle = query if case_sensitive else query.lower()
        for r, row in enumerate(self.get_all_values(), start=1):
            for c, value in enumerate(row, start=1):
                haystack = value if case_sensitive else value.lower()
                if haystack == needle:
                    return Cell(row=r, col=c, value=value)
        return None

    def range(self, name: str) -> list[Any]:
        """Celdas de un rango (devolvería objetos Cell)."""
        raise _spike("worksheet.range")

    def format(self, ranges: str | list[str], cell_format: dict[str, Any]) -> Any:
        """Aplica formato (requiere construir ``repeatCell`` en batchUpdate)."""
        raise _spike("worksheet.format")

    def freeze(self, rows: int | None, cols: int | None) -> Any:
        """Congela filas/columnas (``updateSheetProperties`` en batchUpdate)."""
        raise _spike("worksheet.freeze")

    def merge_cells(self, range_name: str, merge_type: str) -> Any:
        """Combina celdas (``mergeCells`` en batchUpdate)."""
        raise _spike("worksheet.merge_cells")
