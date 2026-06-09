"""Tests del API 2.0: ``SheetManager`` + ``WorksheetContext`` (handles inmutables).

gspread se mockea en el borde de autenticación, igual que en los tests del conector.
"""

import warnings
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from gspread.utils import ValueInputOption
from gspreadmanager import CellFormat, Color, GSpreadManagerError, SheetManager, WorksheetContext
from gspreadmanager.infrastructure.gspread_adapters import GspreadWorksheet


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
    assert isinstance(ws.worksheet, GspreadWorksheet)
    assert ws.worksheet.raw is gs["worksheets"]["Hoja1"]


def test_worksheet_default_uses_sheet1(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet()
    assert isinstance(ws.worksheet, GspreadWorksheet)
    assert ws.worksheet.raw is gs["worksheets"]["Sheet1"]


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
    assert isinstance(ctx.worksheet, GspreadWorksheet)
    assert ctx.worksheet.raw is new_ws


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


def test_sheet_manager_does_not_warn(gs):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SheetManager("Doc", "fake.json").worksheet("A")


# --- Cobertura de las operaciones de WorksheetContext (wiring) ---


def test_update_row(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.worksheet("A").update_row(5, ["a", "b"], start_column=2)
    assert gs["worksheets"]["A"].update_cell.call_count == 2


def test_read_list(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["h"], ["1"]]
    assert ws.read() == [["h"], ["1"]]


def test_last_row(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["h"], ["1"], ["2"]]
    assert ws.last_row() == 3


def test_rows_where_column_equals(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["x", "ok"], ["y", "no"]]
    assert ws.rows_where_column_equals(1, "ok") == [(1, ["x", "ok"])]


def test_batch_update_uses_enum(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.worksheet("A").batch_update([{"range": "A1", "values": [["x"]]}])
    _, kwargs = gs["worksheets"]["A"].batch_update.call_args
    assert kwargs["value_input_option"] == ValueInputOption.user_entered


def test_insert_delegates(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("Hoja1")
    gs["worksheets"]["Hoja1"].get_all_values.return_value = []
    ws.insert([["a", "b"]], fila=1)
    args = gs["spreadsheet"].values_append.call_args[0]
    assert args[0] == "Hoja1!A1:B1"


def test_set_background_and_text_and_number(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    ws.set_background("A1", Color(red=1.0))
    ws.set_text_format("A1", bold=True)
    ws.set_number_format("A1", "0.00%", "PERCENT")
    assert gs["worksheets"]["A"].format.call_count == 3


def test_freeze_and_merge(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    ws.freeze(rows=1, cols=2)
    ws.merge("A1:B2")
    gs["worksheets"]["A"].freeze.assert_called_once_with(rows=1, cols=2)
    gs["worksheets"]["A"].merge_cells.assert_called_once_with("A1:B2", merge_type="MERGE_ALL")


def test_add_checkbox_and_conditional_format(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].id = 0
    ws.add_checkbox("A1:A3")
    ws.add_conditional_format("B1:B3", "NUMBER_LESS", [0], CellFormat(background_color=Color()))
    assert gs["spreadsheet"].batch_update.call_count == 2


def test_find(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.worksheet("A").find("Total")
    gs["worksheets"]["A"].find.assert_called_once_with("Total", case_sensitive=True)


def test_read_dataframe(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["a", "b"], ["1", "2"]]
    df = ws.read_dataframe()
    assert list(df.columns) == ["a", "b"]


def test_write_dataframe_uses_enum(gs):
    mgr = SheetManager("Doc", "fake.json")
    ws = mgr.worksheet("A")
    ws.write_dataframe(pd.DataFrame([["x"]], columns=["c"]))
    gs["worksheets"]["A"].clear.assert_called_once_with()
    _, kwargs = gs["worksheets"]["A"].update.call_args
    assert kwargs["value_input_option"] == ValueInputOption.user_entered


# --- Cobertura de las operaciones a nivel documento de SheetManager ---


def test_delete_sheet(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.delete_sheet("Vieja")
    called_with = gs["spreadsheet"].del_worksheet.call_args[0][0]
    assert called_with is gs["worksheets"]["Vieja"]


def test_delete_and_copy_spreadsheet(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.delete_spreadsheet("file1")
    gs["client"].del_spreadsheet.assert_called_once_with("file1")
    mgr.copy_spreadsheet("file1", title="Copia")
    gs["client"].copy.assert_called_once_with(
        "file1", title="Copia", copy_permissions=False, folder_id=None
    )


def test_list_and_remove_permissions(gs):
    mgr = SheetManager("Doc", "fake.json")
    mgr.list_permissions()
    gs["spreadsheet"].list_permissions.assert_called_once()
    mgr.remove_permission("a@b.com", role="writer")
    gs["spreadsheet"].remove_permissions.assert_called_once_with("a@b.com", role="writer")


class TestOpenByKeyAndUrl:
    def test_open_by_key(self, gs):
        mgr = SheetManager.open_by_key("KEY123", "fake.json")
        mgr.worksheet("A")
        gs["client"].open_by_key.assert_called_once_with("KEY123")
        gs["client"].open.assert_not_called()

    def test_open_by_url(self, gs):
        url = "https://docs.google.com/spreadsheets/d/KEY999/edit"
        mgr = SheetManager.open_by_url(url, "fake.json")
        mgr.worksheet("A")
        gs["client"].open_by_key.assert_called_once_with("KEY999")

    def test_requires_name_or_key(self):
        with pytest.raises(GSpreadManagerError, match="doc_name"):
            SheetManager()


class TestReadNumericise:
    def test_read_list_numericise(self, gs):
        mgr = SheetManager("Doc", "fake.json")
        ws = mgr.worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [["edad"], ["30"], ["x"]]
        assert ws.read(numericise=True) == [["edad"], [30], ["x"]]

    def test_read_dict_numericise(self, gs):
        mgr = SheetManager("Doc", "fake.json")
        ws = mgr.worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [["n", "edad"], ["Ana", "30"]]
        assert ws.read(output_format="dict", numericise=True) == [{"n": "Ana", "edad": 30}]
