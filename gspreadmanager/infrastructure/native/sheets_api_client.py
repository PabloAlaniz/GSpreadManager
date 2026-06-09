"""Cliente nativo (spike) de Google Sheets/Drive vía REST, detrás de los puertos.

Implementa ``ClientPort`` / ``SpreadsheetPort`` / ``WorksheetPort`` llamando a la Sheets API
v4 y la Drive API v3 a través de una ``HttpSession`` (inyectable). **No está cableado** en el
facade: gspread sigue siendo el adaptador por defecto. Cubre todas las operaciones de los
puertos, con mapeo de errores de la API a ``SheetsApiError``; quedan pendientes refinamientos
menores (mover a carpeta en ``create``, semántica de ``with_link``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from gspreadmanager.config import DEFAULT_VALUE_INPUT_OPTION
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.ports.sheets import SpreadsheetPort, WorksheetPort

from ._a1 import a1_to_grid_range, rowcol_to_a1
from .errors import SheetsApiError
from .http import HttpResponse, HttpSession

SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


def _ensure_ok(response: HttpResponse) -> None:
    """Lanza ``SheetsApiError`` si la respuesta no es exitosa (al estilo de gspread.APIError)."""
    if response.ok:
        return
    code, status, message = response.status_code, "UNKNOWN", response.text
    try:
        error = response.json()["error"]
        code = error.get("code", code)
        status = error.get("status", status)
        message = error.get("message", message)
    except (ValueError, KeyError, TypeError):
        pass
    raise SheetsApiError(code, status, message)


class _ApiCaller:
    """Helpers HTTP con un único punto de chequeo de errores (mapeo a ``SheetsApiError``)."""

    _session: HttpSession

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = self._session.get(url, params=params)
        _ensure_ok(response)
        return response.json()

    def _post(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = self._session.post(url, params=params, json=json)
        _ensure_ok(response)
        return response.json()

    def _put(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = self._session.put(url, params=params, json=json)
        _ensure_ok(response)
        return response.json()

    def _delete(self, url: str) -> None:
        response = self._session.delete(url)
        _ensure_ok(response)


@dataclass(frozen=True)
class Cell:
    """Celda encontrada por ``find`` (equivalente nativo de ``gspread.Cell``)."""

    row: int
    col: int
    value: str


class SheetsApiClient(_ApiCaller):
    """``ClientPort`` nativo: abre documentos (Drive) y opera a nivel Drive/Sheets."""

    def __init__(self, session: HttpSession) -> None:
        """Recibe una sesión HTTP autorizada (ver ``build_authorized_session``)."""
        self._session = session

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
        return self.open_by_key(files[0]["id"])

    def open_by_key(self, key: str) -> SpreadsheetPort:
        """Carga las hojas del documento por su key (id) y lo devuelve."""
        meta = self._get(
            f"{SHEETS_BASE}/{key}",
            params={"fields": "sheets.properties(sheetId,title)"},
        )
        sheets = [
            (s["properties"]["title"], s["properties"]["sheetId"]) for s in meta.get("sheets", [])
        ]
        return NativeSpreadsheet(self._session, key, sheets)

    def create(self, title: str, folder_id: str | None) -> Any:
        """Crea un documento (Sheets API). ``folder_id`` aún no se mueve (spike)."""
        return self._post(SHEETS_BASE, json={"properties": {"title": title}})

    def del_spreadsheet(self, file_id: str) -> None:
        """Elimina un documento (Drive)."""
        self._delete(f"{DRIVE_FILES}/{file_id}")

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
        """Lista documentos accesibles (Drive), siguiendo la paginación."""
        clauses = [f"mimeType = '{_SPREADSHEET_MIME}'", "trashed = false"]
        if title is not None:
            clauses.append(f"name = '{title}'")
        if folder_id is not None:
            clauses.append(f"'{folder_id}' in parents")
        query = " and ".join(clauses)

        files: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {"q": query, "fields": "nextPageToken,files(id,name)"}
            if page_token:
                params["pageToken"] = page_token
            data = self._get(DRIVE_FILES, params=params)
            files.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return files


class NativeSpreadsheet(_ApiCaller):
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
        return self._get(f"{SHEETS_BASE}/{self._id}/values/{quote(a1_range, safe='')}")

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

    def get_metadata(self, ranges: list[str] | None, fields: str) -> dict[str, Any]:
        """``spreadsheets.get`` filtrando por ranges/fields."""
        params: dict[str, Any] = {"fields": fields}
        if ranges is not None:
            params["ranges"] = ranges
        result: dict[str, Any] = self._get(f"{SHEETS_BASE}/{self._id}", params=params)
        return result

    def export(self, mime_type: str) -> bytes:
        """Exporta el documento (Drive ``files.export``) y devuelve los bytes."""
        response = self._session.get(
            f"{DRIVE_FILES}/{self._id}/export", params={"mimeType": mime_type}
        )
        _ensure_ok(response)
        return response.content

    def share(
        self,
        email_address: str,
        perm_type: str,
        role: str,
        notify: bool,
        email_message: str | None,
        with_link: bool,
    ) -> Any:
        """Comparte el documento (Drive ``permissions.create``)."""
        body: dict[str, Any] = {"type": perm_type, "role": role}
        if perm_type in ("user", "group"):
            body["emailAddress"] = email_address
        params: dict[str, Any] = {"sendNotificationEmail": notify}
        if email_message:
            params["emailMessage"] = email_message
        return self._post(f"{DRIVE_FILES}/{self._id}/permissions", json=body, params=params)

    def list_permissions(self) -> list[dict[str, Any]]:
        """Lista permisos (Drive ``permissions.list``)."""
        data = self._get(
            f"{DRIVE_FILES}/{self._id}/permissions",
            params={"fields": "permissions(id,type,role,emailAddress,domain)"},
        )
        result: list[dict[str, Any]] = data.get("permissions", [])
        return result

    def remove_permissions(self, value: str, role: str) -> list[str]:
        """Quita los permisos de ``value`` (email/dominio) que coincidan con ``role``."""
        removed: list[str] = []
        for perm in self.list_permissions():
            matches_value = value in (perm.get("emailAddress"), perm.get("domain"))
            matches_role = role == "any" or perm.get("role") == role
            if matches_value and matches_role:
                self._delete(f"{DRIVE_FILES}/{self._id}/permissions/{perm['id']}")
                removed.append(perm["id"])
        return removed


class NativeWorksheet(_ApiCaller):
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

    def get_all_values(self) -> list[list[str]]:
        """Lee toda la hoja (``values.get``), rellenando filas a un ancho uniforme.

        La API recorta celdas vacías al final de cada fila; se rellenan para devolver una
        matriz rectangular (como ``gspread.Worksheet.get_all_values``).
        """
        data = self._parent.values_get(self._title)
        rows: list[list[str]] = data.get("values", [])
        width = max((len(row) for row in rows), default=0)
        return [row + [""] * (width - len(row)) for row in rows]

    def update_cell(self, row: int, col: int, value: Any) -> None:
        """Actualiza una celda (``values.update``)."""
        a1 = f"{self._title}!{rowcol_to_a1(row, col)}"
        self._put(
            self._values_url(a1),
            params={"valueInputOption": DEFAULT_VALUE_INPUT_OPTION},
            json={"values": [[value]]},
        )

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

    def update(
        self, values: list[list[Any]], value_input_option: str, range_name: str | None = None
    ) -> Any:
        """Escribe ``values`` desde A1, o desde ``range_name`` (ancla), vía ``values.update``."""
        target = self._title if range_name is None else self._qualify(range_name)
        return self._put(
            self._values_url(target),
            params={"valueInputOption": value_input_option},
            json={"values": values},
        )

    def _qualify(self, a1_range: str) -> str:
        """Antepone el nombre de la pestaña al rango A1 si no lo trae ya."""
        return a1_range if "!" in a1_range else f"{self._title}!{a1_range}"

    def clear(self) -> None:
        """Limpia toda la hoja (``values.clear``)."""
        self._post(f"{self._values_url(self._title)}:clear")

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
        """Devuelve las celdas con datos del rango como objetos ``Cell``.

        Aproximación del spike: devuelve solo las celdas presentes (sin rellenar el rango
        completo con celdas vacías como hace gspread).
        """
        grid = a1_to_grid_range(name, self._sheet_id)
        a1 = name if "!" in name else f"{self._title}!{name}"
        rows = self._parent.values_get(a1).get("values", [])
        start_row = grid.get("startRowIndex", 0)
        start_col = grid.get("startColumnIndex", 0)
        return [
            Cell(row=start_row + r + 1, col=start_col + c + 1, value=value)
            for r, row in enumerate(rows)
            for c, value in enumerate(row)
        ]

    def format(self, ranges: str | list[str], cell_format: dict[str, Any]) -> Any:
        """Aplica formato a uno o más rangos (``repeatCell`` en batchUpdate)."""
        targets = [ranges] if isinstance(ranges, str) else ranges
        fields = (
            f"userEnteredFormat({','.join(cell_format)})" if cell_format else "userEnteredFormat"
        )
        requests = [
            {
                "repeatCell": {
                    "range": a1_to_grid_range(target, self._sheet_id),
                    "cell": {"userEnteredFormat": cell_format},
                    "fields": fields,
                }
            }
            for target in targets
        ]
        return self._parent.batch_update({"requests": requests})

    def freeze(self, rows: int | None, cols: int | None) -> Any:
        """Congela filas y/o columnas (``updateSheetProperties`` en batchUpdate)."""
        grid_properties: dict[str, Any] = {}
        fields: list[str] = []
        if rows is not None:
            grid_properties["frozenRowCount"] = rows
            fields.append("gridProperties.frozenRowCount")
        if cols is not None:
            grid_properties["frozenColumnCount"] = cols
            fields.append("gridProperties.frozenColumnCount")
        request = {
            "updateSheetProperties": {
                "properties": {"sheetId": self._sheet_id, "gridProperties": grid_properties},
                "fields": ",".join(fields),
            }
        }
        return self._parent.batch_update({"requests": [request]})

    def merge_cells(self, range_name: str, merge_type: str) -> Any:
        """Combina las celdas de un rango (``mergeCells`` en batchUpdate)."""
        request = {
            "mergeCells": {
                "range": a1_to_grid_range(range_name, self._sheet_id),
                "mergeType": merge_type,
            }
        }
        return self._parent.batch_update({"requests": [request]})
