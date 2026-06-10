"""Cliente nativo async de Google Sheets/Drive (espejo de ``sheets_api_client``).

Implementa los puertos async (``ports.async_sheets``) sobre una ``AsyncHttpSession``
(httpx vía ``build_async_session``, o una falsa en tests). Reutiliza del cliente síncrono
las constantes de endpoints, los helpers A1, el chequeo de errores (``_ensure_ok``) y la
jerarquía ``SheetsApiError``: solo cambia el transporte.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from gspreadmanager.config import DEFAULT_VALUE_INPUT_OPTION
from gspreadmanager.domain.errors import (
    GSpreadManagerError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
)
from gspreadmanager.ports.async_sheets import AsyncSpreadsheetPort, AsyncWorksheetPort

from ._a1 import a1_to_grid_range, rowcol_to_a1
from .async_http import AsyncHttpSession
from .errors import SheetsApiError
from .sheets_api_client import (
    _HTTP_NOT_FOUND,
    _SPREADSHEET_MIME,
    DRIVE_FILES,
    SHEETS_BASE,
    Cell,
    _ensure_ok,
)


class _AsyncApiCaller:
    """Helpers HTTP async con un único punto de chequeo de errores."""

    _session: AsyncHttpSession

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._session.get(url, params=params)
        _ensure_ok(response)
        return response.json()

    async def _post(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._session.post(url, params=params, json=json)
        _ensure_ok(response)
        return response.json()

    async def _put(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._session.put(url, params=params, json=json)
        _ensure_ok(response)
        return response.json()

    async def _patch(
        self, url: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._session.patch(url, params=params, json=json)
        _ensure_ok(response)
        return response.json()

    async def _delete(self, url: str) -> None:
        response = await self._session.delete(url)
        _ensure_ok(response)


class AsyncSheetsApiClient(_AsyncApiCaller):
    """``AsyncClientPort`` nativo, con caché de documentos abiertos por nombre/key."""

    def __init__(self, session: AsyncHttpSession) -> None:
        """Recibe una sesión HTTP async autorizada (ver ``build_async_session``)."""
        self._session = session
        self._spreadsheets: dict[str, AsyncSpreadsheetPort] = {}

    async def open(self, doc_name: str) -> AsyncSpreadsheetPort:
        """Resuelve el documento por nombre (Drive) y carga sus hojas, cacheándolo."""
        if doc_name not in self._spreadsheets:
            data = await self._get(
                DRIVE_FILES,
                params={
                    "q": (
                        f"name = '{doc_name}' and mimeType = '{_SPREADSHEET_MIME}' "
                        "and trashed = false"
                    ),
                    "fields": "files(id,name)",
                },
            )
            files = data.get("files", [])
            if not files:
                raise SpreadsheetNotFoundError(f"No se encontró el documento '{doc_name}'.")
            self._spreadsheets[doc_name] = await self.open_by_key(files[0]["id"])
        return self._spreadsheets[doc_name]

    async def open_by_key(self, key: str) -> AsyncSpreadsheetPort:
        """Carga las hojas del documento por su key (id) y lo devuelve, cacheándolo."""
        if key not in self._spreadsheets:
            try:
                meta = await self._get(
                    f"{SHEETS_BASE}/{key}",
                    params={"fields": "sheets.properties(sheetId,title)"},
                )
            except SheetsApiError as exc:
                if exc.code == _HTTP_NOT_FOUND:
                    raise SpreadsheetNotFoundError(
                        f"No se encontró el documento con key '{key}'."
                    ) from exc
                raise
            sheets = [
                (s["properties"]["title"], s["properties"]["sheetId"])
                for s in meta.get("sheets", [])
            ]
            self._spreadsheets[key] = AsyncNativeSpreadsheet(self._session, key, sheets)
        return self._spreadsheets[key]

    async def create(self, title: str, folder_id: str | None) -> Any:
        """Crea un documento; con ``folder_id`` lo mueve a esa carpeta (Drive)."""
        result = await self._post(SHEETS_BASE, json={"properties": {"title": title}})
        if folder_id is not None:
            await self._patch(
                f"{DRIVE_FILES}/{result['spreadsheetId']}",
                params={"addParents": folder_id, "removeParents": "root", "fields": "id,parents"},
            )
        return result

    async def del_spreadsheet(self, file_id: str) -> None:
        """Elimina un documento (Drive)."""
        await self._delete(f"{DRIVE_FILES}/{file_id}")

    async def copy(
        self, file_id: str, title: str | None, copy_permissions: bool, folder_id: str | None
    ) -> Any:
        """Copia un documento (Drive ``files.copy``)."""
        body: dict[str, Any] = {}
        if title is not None:
            body["name"] = title
        if folder_id is not None:
            body["parents"] = [folder_id]
        return await self._post(f"{DRIVE_FILES}/{file_id}/copy", json=body)

    async def list_spreadsheet_files(
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
            data = await self._get(DRIVE_FILES, params=params)
            files.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return files


class AsyncNativeSpreadsheet(_AsyncApiCaller):
    """``AsyncSpreadsheetPort`` nativo: opera sobre un documento por su id."""

    def __init__(
        self, session: AsyncHttpSession, spreadsheet_id: str, sheets: list[tuple[str, int]]
    ) -> None:
        """Recibe la sesión, el id del documento y la lista (título, sheetId) de sus hojas."""
        self._session = session
        self._id = spreadsheet_id
        self._sheets = sheets

    @property
    def raw_id(self) -> str:
        """Id del documento (escape hatch)."""
        return self._id

    def _sheet_id(self, title: str) -> int:
        for name, sheet_id in self._sheets:
            if name == title:
                return sheet_id
        raise WorksheetNotFoundError(f"No existe la hoja '{title}'.")

    @property
    def sheet1(self) -> AsyncWorksheetPort:
        """Primera hoja del documento."""
        if not self._sheets:
            raise GSpreadManagerError("El documento no tiene hojas.")
        title, sheet_id = self._sheets[0]
        return AsyncNativeWorksheet(self, self._session, self._id, title, sheet_id)

    def worksheet(self, name: str) -> AsyncWorksheetPort:
        """Hoja por nombre (lookup local)."""
        return AsyncNativeWorksheet(self, self._session, self._id, name, self._sheet_id(name))

    async def add_worksheet(
        self, title: str, rows: int, cols: int, index: int | None
    ) -> AsyncWorksheetPort:
        """Crea una hoja vía ``spreadsheets:batchUpdate`` (addSheet) y la devuelve."""
        props: dict[str, Any] = {
            "title": title,
            "gridProperties": {"rowCount": rows, "columnCount": cols},
        }
        if index is not None:
            props["index"] = index
        result = await self.batch_update({"requests": [{"addSheet": {"properties": props}}]})
        sheet_id = result["replies"][0]["addSheet"]["properties"]["sheetId"]
        self._sheets.append((title, sheet_id))
        return AsyncNativeWorksheet(self, self._session, self._id, title, sheet_id)

    async def delete_worksheet(self, title: str) -> None:
        """Elimina una hoja vía ``spreadsheets:batchUpdate`` (deleteSheet)."""
        sheet_id = self._sheet_id(title)
        await self.batch_update({"requests": [{"deleteSheet": {"sheetId": sheet_id}}]})
        self._sheets = [(n, sid) for (n, sid) in self._sheets if n != title]

    async def values_get(self, a1_range: str) -> Any:
        """``spreadsheets.values.get``."""
        return await self._get(f"{SHEETS_BASE}/{self._id}/values/{quote(a1_range, safe='')}")

    async def values_append(
        self, a1_range: str, params: dict[str, Any], body: dict[str, Any]
    ) -> Any:
        """``spreadsheets.values.append``."""
        return await self._post(
            f"{SHEETS_BASE}/{self._id}/values/{quote(a1_range, safe='')}:append",
            params=params,
            json=body,
        )

    async def batch_update(self, body: dict[str, Any]) -> Any:
        """``spreadsheets:batchUpdate``."""
        return await self._post(f"{SHEETS_BASE}/{self._id}:batchUpdate", json=body)

    async def get_metadata(self, ranges: list[str] | None, fields: str) -> dict[str, Any]:
        """``spreadsheets.get`` filtrando por ranges/fields."""
        params: dict[str, Any] = {"fields": fields}
        if ranges is not None:
            params["ranges"] = ranges
        result: dict[str, Any] = await self._get(f"{SHEETS_BASE}/{self._id}", params=params)
        return result

    async def export(self, mime_type: str) -> bytes:
        """Exporta el documento (Drive ``files.export``) y devuelve los bytes."""
        response = await self._session.get(
            f"{DRIVE_FILES}/{self._id}/export", params={"mimeType": mime_type}
        )
        _ensure_ok(response)
        return response.content

    async def share(
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
        return await self._post(f"{DRIVE_FILES}/{self._id}/permissions", json=body, params=params)

    async def list_permissions(self) -> list[dict[str, Any]]:
        """Lista permisos (Drive ``permissions.list``)."""
        data = await self._get(
            f"{DRIVE_FILES}/{self._id}/permissions",
            params={"fields": "permissions(id,type,role,emailAddress,domain)"},
        )
        result: list[dict[str, Any]] = data.get("permissions", [])
        return result

    async def remove_permissions(self, value: str, role: str) -> list[str]:
        """Quita los permisos de ``value`` (email/dominio) que coincidan con ``role``."""
        removed: list[str] = []
        for perm in await self.list_permissions():
            matches_value = value in (perm.get("emailAddress"), perm.get("domain"))
            matches_role = role == "any" or perm.get("role") == role
            if matches_value and matches_role:
                await self._delete(f"{DRIVE_FILES}/{self._id}/permissions/{perm['id']}")
                removed.append(perm["id"])
        return removed


class AsyncNativeWorksheet(_AsyncApiCaller):
    """``AsyncWorksheetPort`` nativo: opera sobre una hoja por su título/sheetId."""

    def __init__(
        self,
        spreadsheet: AsyncNativeSpreadsheet,
        session: AsyncHttpSession,
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
    def spreadsheet(self) -> AsyncSpreadsheetPort:
        """Documento al que pertenece."""
        return self._parent

    def _values_url(self, a1_range: str) -> str:
        return f"{SHEETS_BASE}/{self._ss_id}/values/{quote(a1_range, safe='')}"

    async def get_all_values(self, value_render_option: str | None = None) -> list[list[str]]:
        """Lee toda la hoja (``values.get``), rellenando filas a un ancho uniforme."""
        params = {"valueRenderOption": value_render_option} if value_render_option else None
        data = await self._get(self._values_url(self._title), params=params)
        rows: list[list[str]] = data.get("values", [])
        width = max((len(row) for row in rows), default=0)
        return [row + [""] * (width - len(row)) for row in rows]

    async def update_cell(self, row: int, col: int, value: Any) -> None:
        """Actualiza una celda (``values.update``)."""
        a1 = f"{self._title}!{rowcol_to_a1(row, col)}"
        await self._put(
            self._values_url(a1),
            params={"valueInputOption": DEFAULT_VALUE_INPUT_OPTION},
            json={"values": [[value]]},
        )

    async def append_rows(self, data: list[list[Any]], value_input_option: str) -> Any:
        """Añade filas al final (``values.append``)."""
        return await self._post(
            f"{self._values_url(self._title)}:append",
            params={"valueInputOption": value_input_option, "insertDataOption": "INSERT_ROWS"},
            json={"values": data},
        )

    async def batch_update(
        self, range_data: list[dict[str, Any]], value_input_option: str
    ) -> None:
        """Actualiza varios rangos (``values:batchUpdate``)."""
        await self._post(
            f"{SHEETS_BASE}/{self._ss_id}/values:batchUpdate",
            json={"valueInputOption": value_input_option, "data": range_data},
        )

    async def update(
        self, values: list[list[Any]], value_input_option: str, range_name: str | None = None
    ) -> Any:
        """Escribe ``values`` desde A1, o desde ``range_name`` (ancla)."""
        target = self._title if range_name is None else self._qualify(range_name)
        return await self._put(
            self._values_url(target),
            params={"valueInputOption": value_input_option},
            json={"values": values},
        )

    def _qualify(self, a1_range: str) -> str:
        return a1_range if "!" in a1_range else f"{self._title}!{a1_range}"

    async def clear(self) -> None:
        """Limpia toda la hoja (``values.clear``)."""
        await self._post(f"{self._values_url(self._title)}:clear")

    async def batch_clear(self, ranges: list[str]) -> None:
        """Limpia varios rangos (``values:batchClear``)."""
        await self._post(f"{SHEETS_BASE}/{self._ss_id}/values:batchClear", json={"ranges": ranges})

    async def col_values(self, col: int) -> list[Any]:
        """Valores de una columna (derivado de ``get_all_values``)."""
        rows = await self.get_all_values()
        return [row[col - 1] if col - 1 < len(row) else "" for row in rows]

    async def row_values(self, row: int) -> list[Any]:
        """Valores de una fila (derivado de ``get_all_values``)."""
        values = await self.get_all_values()
        return values[row - 1] if 0 < row <= len(values) else []

    async def find(self, query: str, case_sensitive: bool) -> Any:
        """Busca la primera celda con valor ``query`` (escaneo client-side)."""
        needle = query if case_sensitive else query.lower()
        for r, row in enumerate(await self.get_all_values(), start=1):
            for c, value in enumerate(row, start=1):
                haystack = value if case_sensitive else value.lower()
                if haystack == needle:
                    return Cell(row=r, col=c, value=value)
        return None

    async def range(self, name: str) -> list[Any]:
        """Devuelve las celdas con datos del rango como objetos ``Cell``."""
        grid = a1_to_grid_range(name, self._sheet_id)
        a1 = name if "!" in name else f"{self._title}!{name}"
        data = await self._parent.values_get(a1)
        rows = data.get("values", [])
        start_row = grid.get("startRowIndex", 0)
        start_col = grid.get("startColumnIndex", 0)
        return [
            Cell(row=start_row + r + 1, col=start_col + c + 1, value=value)
            for r, row in enumerate(rows)
            for c, value in enumerate(row)
        ]

    async def format(self, ranges: str | list[str], cell_format: dict[str, Any]) -> Any:
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
        return await self._parent.batch_update({"requests": requests})

    async def freeze(self, rows: int | None, cols: int | None) -> Any:
        """Congela filas y/o columnas (``updateSheetProperties``)."""
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
        return await self._parent.batch_update({"requests": [request]})

    async def merge_cells(self, range_name: str, merge_type: str) -> Any:
        """Combina las celdas de un rango (``mergeCells``)."""
        request = {
            "mergeCells": {
                "range": a1_to_grid_range(range_name, self._sheet_id),
                "mergeType": merge_type,
            }
        }
        return await self._parent.batch_update({"requests": [request]})

    async def copy_to(self, destination_spreadsheet_id: str) -> Any:
        """Copia esta hoja a otro documento (``sheets.copyTo``)."""
        return await self._post(
            f"{SHEETS_BASE}/{self._ss_id}/sheets/{self._sheet_id}:copyTo",
            json={"destinationSpreadsheetId": destination_spreadsheet_id},
        )
