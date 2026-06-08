"""Tests del spike del cliente nativo (REST) con una sesión HTTP falsa.

Validan que el cliente nativo implementa los puertos y arma las llamadas correctas a la
Sheets API v4 / Drive API v3, sin red real. No prueban el wiring (el spike no está cableado).
"""

from typing import Any

import pytest
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.infrastructure.native._a1 import column_to_letter, rowcol_to_a1
from gspreadmanager.infrastructure.native.sheets_api_client import (
    Cell,
    NativeSpreadsheet,
    NativeWorksheet,
    SheetsApiClient,
)
from gspreadmanager.ports.sheets import ClientPort, SpreadsheetPort, WorksheetPort


class FakeResponse:
    def __init__(self, data: Any = None) -> None:
        self._data = data if data is not None else {}
        self.raised = False

    def json(self) -> Any:
        return self._data

    def raise_for_status(self) -> None:
        self.raised = True


class FakeSession:
    """Sesión HTTP falsa: registra llamadas y devuelve respuestas en cola por verbo."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self._queue: dict[str, list[FakeResponse]] = {}

    def queue(self, method: str, data: Any) -> None:
        self._queue.setdefault(method, []).append(FakeResponse(data))

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

    def test_permissions_are_spike_pending(self):
        with pytest.raises(NotImplementedError, match="spike"):
            self._ss(FakeSession()).list_permissions()


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

    def test_format_is_spike_pending(self):
        with pytest.raises(NotImplementedError, match="spike"):
            self._ws(FakeSession()).format("A1", {})
