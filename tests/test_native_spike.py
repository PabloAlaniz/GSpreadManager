"""Tests del spike del cliente nativo (REST) con una sesión HTTP falsa.

Validan que el cliente nativo implementa los puertos y arma las llamadas correctas a la
Sheets API v4 / Drive API v3, sin red real. No prueban el wiring (el spike no está cableado).
"""

from typing import Any

import pytest
from gspread.utils import a1_range_to_grid_range
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.infrastructure.native._a1 import (
    a1_to_grid_range,
    column_to_letter,
    rowcol_to_a1,
)
from gspreadmanager.infrastructure.native.errors import SheetsApiError
from gspreadmanager.infrastructure.native.sheets_api_client import (
    Cell,
    NativeSpreadsheet,
    NativeWorksheet,
    SheetsApiClient,
)
from gspreadmanager.ports.sheets import ClientPort, SpreadsheetPort, WorksheetPort


class FakeResponse:
    def __init__(
        self, data: Any = None, ok: bool = True, status_code: int = 200, text: str = ""
    ) -> None:
        self._data = data if data is not None else {}
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(self) -> Any:
        return self._data


class FakeSession:
    """Sesión HTTP falsa: registra llamadas y devuelve respuestas en cola por verbo."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self._queue: dict[str, list[FakeResponse]] = {}

    def queue(
        self, method: str, data: Any, *, ok: bool = True, status_code: int = 200, text: str = ""
    ) -> None:
        self._queue.setdefault(method, []).append(
            FakeResponse(data, ok=ok, status_code=status_code, text=text)
        )

    def _resp(self, method: str) -> FakeResponse:
        q = self._queue.get(method)
        return q.pop(0) if q else FakeResponse({})

    def get(self, url: str, *, params: Any = None) -> FakeResponse:
        self.calls.append(("GET", url, params, None))
        return self._resp("get")

    def post(self, url: str, *, params: Any = None, json: Any = None) -> FakeResponse:
        self.calls.append(("POST", url, params, json))
        return self._resp("post")

    def put(self, url: str, *, params: Any = None, json: Any = None) -> FakeResponse:
        self.calls.append(("PUT", url, params, json))
        return self._resp("put")

    def delete(self, url: str, *, params: Any = None) -> FakeResponse:
        self.calls.append(("DELETE", url, params, None))
        return self._resp("delete")


class TestA1Helpers:
    @pytest.mark.parametrize(
        ("col", "letter"),
        [(1, "A"), (26, "Z"), (27, "AA"), (52, "AZ"), (702, "ZZ"), (703, "AAA")],
    )
    def test_column_to_letter(self, col, letter):
        assert column_to_letter(col) == letter

    def test_rowcol_to_a1(self):
        assert rowcol_to_a1(2, 3) == "C2"
        assert rowcol_to_a1(1, 27) == "AA1"

    def test_invalid(self):
        with pytest.raises(ValueError, match="Columna"):
            column_to_letter(0)
        with pytest.raises(ValueError, match="Fila"):
            rowcol_to_a1(0, 1)


class TestPortConformance:
    def test_satisfies_ports(self):
        session = FakeSession()
        client: ClientPort = SheetsApiClient(session)
        spreadsheet: SpreadsheetPort = NativeSpreadsheet(session, "id", [("Hoja1", 0)])
        worksheet: WorksheetPort = NativeWorksheet(spreadsheet, session, "id", "Hoja1", 0)  # type: ignore[arg-type]
        assert callable(client.open)
        assert callable(spreadsheet.values_get)
        assert callable(worksheet.get_all_values)


class TestClientOpen:
    def test_open_resolves_by_name_and_loads_sheets(self):
        session = FakeSession()
        session.queue("get", {"files": [{"id": "doc123", "name": "MiDoc"}]})
        session.queue("get", {"sheets": [{"properties": {"title": "Hoja1", "sheetId": 7}}]})

        ss = SheetsApiClient(session).open("MiDoc")

        assert isinstance(ss, NativeSpreadsheet)
        assert ss.raw_id == "doc123"
        # Primera llamada: búsqueda en Drive por nombre
        method, url, params, _ = session.calls[0]
        assert method == "GET"
        assert url.endswith("/drive/v3/files")
        assert "MiDoc" in params["q"]
        # Segunda: metadata del documento en Sheets
        assert session.calls[1][1].endswith("/v4/spreadsheets/doc123")
        ws = ss.worksheet("Hoja1")
        assert ws.id == 7

    def test_open_not_found_raises(self):
        session = FakeSession()
        session.queue("get", {"files": []})
        with pytest.raises(GSpreadManagerError, match="No se encontró"):
            SheetsApiClient(session).open("Inexistente")


class TestClientDrive:
    def test_create(self):
        session = FakeSession()
        SheetsApiClient(session).create("Nuevo", None)
        method, url, _, body = session.calls[0]
        assert method == "POST"
        assert url.endswith("/v4/spreadsheets")
        assert body == {"properties": {"title": "Nuevo"}}

    def test_del_spreadsheet(self):
        session = FakeSession()
        SheetsApiClient(session).del_spreadsheet("file1")
        assert session.calls[0][:2] == ("DELETE", "https://www.googleapis.com/drive/v3/files/file1")

    def test_list_spreadsheet_files(self):
        session = FakeSession()
        session.queue("get", {"files": [{"id": "1", "name": "A"}]})
        result = SheetsApiClient(session).list_spreadsheet_files("A", "folder9")
        assert result == [{"id": "1", "name": "A"}]
        q = session.calls[0][2]["q"]
        assert "name = 'A'" in q
        assert "'folder9' in parents" in q


class TestSpreadsheet:
    def _ss(self, session: FakeSession) -> NativeSpreadsheet:
        return NativeSpreadsheet(session, "doc123", [("Hoja1", 0)])

    def test_values_get(self):
        session = FakeSession()
        session.queue("get", {"values": [["a"]]})
        assert self._ss(session).values_get("Hoja1!A1:A1") == {"values": [["a"]]}
        assert session.calls[0][1].endswith("/v4/spreadsheets/doc123/values/Hoja1%21A1%3AA1")

    def test_batch_update(self):
        session = FakeSession()
        body: dict[str, Any] = {"requests": [{"setDataValidation": {}}]}
        self._ss(session).batch_update(body)
        method, url, _, sent = session.calls[0]
        assert method == "POST"
        assert url.endswith("/v4/spreadsheets/doc123:batchUpdate")
        assert sent == body

    def test_add_worksheet(self):
        session = FakeSession()
        session.queue("post", {"replies": [{"addSheet": {"properties": {"sheetId": 42}}}]})
        ws = self._ss(session).add_worksheet("Nueva", 10, 5, None)
        assert ws.id == 42
        sent = session.calls[0][3]
        assert sent["requests"][0]["addSheet"]["properties"]["title"] == "Nueva"

    def test_delete_worksheet(self):
        session = FakeSession()
        self._ss(session).delete_worksheet("Hoja1")
        sent = session.calls[0][3]
        assert sent["requests"][0]["deleteSheet"]["sheetId"] == 0

    def test_share(self):
        session = FakeSession()
        self._ss(session).share("a@b.com", "user", "writer", True, "hola", False)
        method, url, params, body = session.calls[0]
        assert method == "POST"
        assert url.endswith("/drive/v3/files/doc123/permissions")
        assert body == {"type": "user", "role": "writer", "emailAddress": "a@b.com"}
        assert params == {"sendNotificationEmail": True, "emailMessage": "hola"}

    def test_list_permissions(self):
        session = FakeSession()
        session.queue("get", {"permissions": [{"id": "p1", "role": "writer"}]})
        assert self._ss(session).list_permissions() == [{"id": "p1", "role": "writer"}]

    def test_remove_permissions_matching(self):
        session = FakeSession()
        session.queue(
            "get",
            {
                "permissions": [
                    {"id": "p1", "emailAddress": "a@b.com", "role": "writer"},
                    {"id": "p2", "emailAddress": "c@d.com", "role": "reader"},
                ]
            },
        )
        removed = self._ss(session).remove_permissions("a@b.com", "any")
        assert removed == ["p1"]
        assert session.calls[-1][:2] == (
            "DELETE",
            "https://www.googleapis.com/drive/v3/files/doc123/permissions/p1",
        )


class TestWorksheet:
    def _ws(self, session: FakeSession) -> NativeWorksheet:
        ss = NativeSpreadsheet(session, "doc123", [("Hoja1", 0)])
        return NativeWorksheet(ss, session, "doc123", "Hoja1", 0)

    def test_get_all_values(self):
        session = FakeSession()
        session.queue("get", {"values": [["a", "b"], ["1", "2"]]})
        assert self._ws(session).get_all_values() == [["a", "b"], ["1", "2"]]

    def test_update_cell(self):
        session = FakeSession()
        self._ws(session).update_cell(2, 3, "x")
        method, url, params, body = session.calls[0]
        assert method == "PUT"
        assert url.endswith("/values/Hoja1%21C2")
        assert params["valueInputOption"] == "USER_ENTERED"
        assert body == {"values": [["x"]]}

    def test_append_rows(self):
        session = FakeSession()
        self._ws(session).append_rows([["a", "b"]], "USER_ENTERED")
        method, url, params, body = session.calls[0]
        assert method == "POST"
        assert url.endswith("/values/Hoja1:append")
        assert params == {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
        assert body == {"values": [["a", "b"]]}

    def test_batch_update_values(self):
        session = FakeSession()
        self._ws(session).batch_update([{"range": "Hoja1!A1", "values": [["x"]]}], "RAW")
        method, url, _, body = session.calls[0]
        assert method == "POST"
        assert url.endswith("/values:batchUpdate")
        assert body == {
            "valueInputOption": "RAW",
            "data": [{"range": "Hoja1!A1", "values": [["x"]]}],
        }

    def test_clear_and_batch_clear(self):
        session = FakeSession()
        ws = self._ws(session)
        ws.clear()
        ws.batch_clear(["Hoja1!A1:A5"])
        assert session.calls[0][1].endswith("/values/Hoja1:clear")
        assert session.calls[1][1].endswith("/values:batchClear")
        assert session.calls[1][3] == {"ranges": ["Hoja1!A1:A5"]}

    def test_col_and_row_values(self):
        session = FakeSession()
        session.queue("get", {"values": [["a", "b"], ["c", "d"]]})
        session.queue("get", {"values": [["a", "b"], ["c", "d"]]})
        ws = self._ws(session)
        assert ws.col_values(1) == ["a", "c"]
        assert ws.row_values(2) == ["c", "d"]

    def test_find(self):
        session = FakeSession()
        session.queue("get", {"values": [["a", "Total"], ["x", "y"]]})
        assert self._ws(session).find("Total", True) == Cell(row=1, col=2, value="Total")

    def test_find_not_found(self):
        session = FakeSession()
        session.queue("get", {"values": [["a"]]})
        assert self._ws(session).find("zzz", True) is None

    def test_get_all_values_pads_ragged_rows(self):
        session = FakeSession()
        session.queue("get", {"values": [["a", "b"], ["c"]]})
        assert self._ws(session).get_all_values() == [["a", "b"], ["c", ""]]

    def test_format_builds_repeat_cell(self):
        session = FakeSession()
        fmt = {"backgroundColor": {"red": 1.0}}
        self._ws(session).format("A1:B2", fmt)
        sent = session.calls[0][3]
        request = sent["requests"][0]["repeatCell"]
        assert request["range"] == {
            "sheetId": 0,
            "startRowIndex": 0,
            "endRowIndex": 2,
            "startColumnIndex": 0,
            "endColumnIndex": 2,
        }
        assert request["cell"] == {"userEnteredFormat": fmt}
        assert request["fields"] == "userEnteredFormat(backgroundColor)"

    def test_freeze_builds_update_sheet_properties(self):
        session = FakeSession()
        self._ws(session).freeze(1, None)
        request = session.calls[0][3]["requests"][0]["updateSheetProperties"]
        assert request["properties"]["gridProperties"] == {"frozenRowCount": 1}
        assert request["fields"] == "gridProperties.frozenRowCount"

    def test_merge_builds_merge_cells(self):
        session = FakeSession()
        self._ws(session).merge_cells("A1:B2", "MERGE_ALL")
        request = session.calls[0][3]["requests"][0]["mergeCells"]
        assert request["mergeType"] == "MERGE_ALL"
        assert request["range"]["sheetId"] == 0

    def test_range_returns_cells(self):
        session = FakeSession()
        session.queue("get", {"values": [["x", "y"]]})
        cells = self._ws(session).range("B2:C2")
        assert cells == [Cell(row=2, col=2, value="x"), Cell(row=2, col=3, value="y")]


class TestA1ToGridRange:
    @pytest.mark.parametrize("a1", ["A1", "A1:C10", "A:A", "A:C", "1:1", "2:5", "AA1:AB2"])
    def test_parity_with_gspread(self, a1):
        assert a1_to_grid_range(a1, 0) == a1_range_to_grid_range(a1, 0)

    def test_strips_sheet_prefix(self):
        # La versión nativa acepta el prefijo de pestaña (gspread no).
        assert a1_to_grid_range("Hoja1!B2:D4", 0) == a1_to_grid_range("B2:D4", 0)


class TestPagination:
    def test_list_follows_next_page_token(self):
        session = FakeSession()
        session.queue("get", {"files": [{"id": "1"}], "nextPageToken": "tok"})
        session.queue("get", {"files": [{"id": "2"}]})
        result = SheetsApiClient(session).list_spreadsheet_files(None, None)
        assert [f["id"] for f in result] == ["1", "2"]
        assert session.calls[1][2]["pageToken"] == "tok"


class TestErrorMapping:
    def test_api_error_is_parsed(self):
        session = FakeSession()
        session.queue(
            "get",
            {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "nope"}},
            ok=False,
            status_code=403,
        )
        ss = NativeSpreadsheet(session, "doc", [])
        with pytest.raises(SheetsApiError, match="PERMISSION_DENIED") as exc:
            ss.values_get("A1")
        assert exc.value.code == 403
        assert exc.value.message == "nope"

    def test_non_json_error_falls_back_to_text(self):
        session = FakeSession()
        session.queue("post", None, ok=False, status_code=500, text="boom")
        with pytest.raises(SheetsApiError, match="boom") as exc:
            NativeSpreadsheet(session, "doc", []).batch_update({})
        assert exc.value.code == 500
        assert exc.value.status == "UNKNOWN"
