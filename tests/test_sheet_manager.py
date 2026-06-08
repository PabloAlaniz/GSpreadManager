"""Tests del API 2.0: ``SheetManager`` + ``WorksheetContext`` (handles inmutables).

gspread se mockea en el borde de autenticación, igual que en los tests del conector.
"""

import warnings
from typing import Any
from unittest.mock import Mock, patch

import pytest
from gspread.utils import ValueInputOption
from gspreadmanager import GoogleSheetConector, SheetManager, WorksheetContext


@pytest.fixture
def gs():
    """Mockea gspread: authorize -> client -> open -> spreadsheet, con hojas por nombre."""
    with (
        patch("gspreadmanager.infrastructure.auth.service_account.Credentials") as mock_creds,
        patch("gspreadmanager.infrastructure.auth.gspread") as mock_gs,
    ):
        mock_creds.from_service_account_file.return_value = Mock()
        client = Mock()
        spreadsheet = Mock()
        worksheets: dict[str, Any] = {}

        def make_ws(name: str) -> Any:
            ws = worksheets.setdefault(name, Mock(name=f"ws:{name}"))
            ws.title = name
            ws.spreadsheet = spreadsheet
            return ws

        mock_gs.authorize.return_value = client
        client.open.return_value = spreadsheet
        spreadsheet.worksheet.side_effect = make_ws
        spreadsheet.sheet1 = make_ws("Sheet1")

        yield {
            "gspread": mock_gs,
            "client": client,
            "spreadsheet": spreadsheet,
            "worksheets": worksheets,
        }


def test_worksheet_returns_context(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("Hoja1")
    assert isinstance(ws, WorksheetContext)
    assert ws.title == "Hoja1"
    assert ws.worksheet is gs["worksheets"]["Hoja1"]


def test_worksheet_default_uses_sheet1(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet()
    assert ws.worksheet is gs["worksheets"]["Sheet1"]


def test_handles_are_independent_no_global_active_sheet(gs):
    """Operar sobre un handle no afecta a otro: no hay 'hoja activa' global."""
    mgr = SheetManager("Doc", "fake.json")
    a = mgr.worksheet("A")
    b = mgr.worksheet("B")

    a.update_cell(1, 1, "x")
    b.update_cell(2, 2, "y")

    gs["worksheets"]["A"].update_cell.assert_called_once_with(1, 1, "x")
    gs["worksheets"]["B"].update_cell.assert_called_once_with(2, 2, "y")
    assert a.worksheet is not b.worksheet


def test_client_and_doc_cached_across_worksheets(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.worksheet("A")
    mgr.worksheet("B")
    # Autoriza una vez y abre el documento una vez (caché del adaptador)
    gs["gspread"].authorize.assert_called_once()
    gs["client"].open.assert_called_once_with("Doc")


def test_append_uses_value_input_option_enum(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.worksheet("A").append([["a", "b"]])
    _, kwargs = gs["worksheets"]["A"].append_rows.call_args
    assert kwargs["value_input_option"] == ValueInputOption.user_entered


def test_read_dict(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["h1", "h2"], ["1", "2"]]
    assert ws.read(output_format="dict") == [{"h1": "1", "h2": "2"}]


def test_read_range_uses_worksheet_title(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("Hoja1")
    gs["spreadsheet"].values_get.return_value = {"values": [["a"], ["b"]]}
    result = ws.read_range(1, 2, "A", "A")
    gs["spreadsheet"].values_get.assert_called_once_with("Hoja1!A1:A2")
    assert result == [{"fila": 1, "values": ["a"]}, {"fila": 2, "values": ["b"]}]


def test_format_header_delegates(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    ws.format_header()
    gs["worksheets"]["A"].format.assert_called_once()


def test_add_dropdown_builds_validation_request(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].id = 0
    ws.add_dropdown("A1:A3", ["x", "y"])
    body = gs["spreadsheet"].batch_update.call_args[0][0]
    assert body["requests"][0]["setDataValidation"]["rule"]["condition"]["type"] == "ONE_OF_LIST"


def test_clear_whole_sheet(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.worksheet("A").clear()
    gs["worksheets"]["A"].clear.assert_called_once_with()


def test_create_sheet_returns_context_without_activating(gs):
    mgr = SheetManager("Doc", "fake.json")
    new_ws = type(gs["worksheets"]["Sheet1"])(name="ws:Nueva")
    new_ws.title = "Nueva"
    gs["spreadsheet"].add_worksheet.return_value = new_ws
    ctx = mgr.create_sheet("Nueva", rows=10, cols=5)
    gs["spreadsheet"].add_worksheet.assert_called_once_with("Nueva", rows=10, cols=5, index=None)
    assert isinstance(ctx, WorksheetContext)
    assert ctx.worksheet is new_ws


def test_document_ops(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.create_spreadsheet("Nuevo", folder_id="f1")
    gs["client"].create.assert_called_once_with("Nuevo", folder_id="f1")
    mgr.list_spreadsheets(title="x")
    gs["client"].list_spreadsheet_files.assert_called_once_with(title="x", folder_id=None)


def test_share_uses_managers_doc_by_default(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.share("a@b.com", role="writer")
    gs["spreadsheet"].share.assert_called_once()


def test_legacy_connector_emits_deprecation_warning(gs):
    with pytest.warns(DeprecationWarning, match="obsoleto"):
        GoogleSheetConector("Doc", "fake.json")


def test_sheet_manager_does_not_warn(gs):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SheetManager("Doc", "fake.json").worksheet("A")
