"""Tests del API 2.0: ``SheetManager`` + ``WorksheetContext`` (handles inmutables).

gspread se mockea en el borde de autenticación, igual que en los tests del conector.
"""

import warnings
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from gspread.utils import ValueInputOption
from gspreadmanager import (
    CellFormat,
    Color,
    ExportFormat,
    GSpreadManagerError,
    SheetManager,
    WorksheetContext,
)
from gspreadmanager.infrastructure.gspread_adapters import GspreadWorksheet


@pytest.fixture
def gs():
    """Mockea gspread: authorize -> client -> open -> spreadsheet, con hojas por nombre."""
    with (
        patch("gspreadmanager.infrastructure.auth.service_account.Credentials") as mock_creds,
        patch("gspreadmanager.infrastructure.auth._authorize") as mock_authorize,
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

        mock_authorize.return_value = client
        client.open.return_value = spreadsheet
        spreadsheet.worksheet.side_effect = make_ws
        spreadsheet.sheet1 = make_ws("Sheet1")

        yield {
            "authorize": mock_authorize,
            "client": client,
            "spreadsheet": spreadsheet,
            "worksheets": worksheets,
        }


def test_worksheet_returns_context(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("Hoja1")
    assert isinstance(ws, WorksheetContext)
    assert ws.title == "Hoja1"
    assert isinstance(ws.worksheet, GspreadWorksheet)
    assert ws.worksheet.raw is gs["worksheets"]["Hoja1"]


def test_worksheet_default_uses_sheet1(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet()
    assert isinstance(ws.worksheet, GspreadWorksheet)
    assert ws.worksheet.raw is gs["worksheets"]["Sheet1"]


def test_handles_are_independent_no_global_active_sheet(gs):
    """Operar sobre un handle no afecta a otro: no hay 'hoja activa' global."""
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    a = mgr.worksheet("A")
    b = mgr.worksheet("B")

    a.update_cell(1, 1, "x")
    b.update_cell(2, 2, "y")

    gs["worksheets"]["A"].update_cell.assert_called_once_with(1, 1, "x")
    gs["worksheets"]["B"].update_cell.assert_called_once_with(2, 2, "y")
    assert a.worksheet is not b.worksheet


def test_client_and_doc_cached_across_worksheets(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.worksheet("A")
    mgr.worksheet("B")
    # Autoriza una vez y abre el documento una vez (caché del adaptador)
    gs["authorize"].assert_called_once()
    gs["client"].open.assert_called_once_with("Doc")


def test_append_uses_value_input_option_enum(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.worksheet("A").append([["a", "b"]])
    _, kwargs = gs["worksheets"]["A"].append_rows.call_args
    assert kwargs["value_input_option"] == ValueInputOption.user_entered


def test_read_dict(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["h1", "h2"], ["1", "2"]]
    assert ws.read(output_format="dict") == [{"h1": "1", "h2": "2"}]


def test_read_range_uses_worksheet_title(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("Hoja1")
    gs["spreadsheet"].values_get.return_value = {"values": [["a"], ["b"]]}
    result = ws.read_range(1, 2, "A", "A")
    gs["spreadsheet"].values_get.assert_called_once_with("Hoja1!A1:A2")
    assert result == [{"fila": 1, "values": ["a"]}, {"fila": 2, "values": ["b"]}]


def test_format_header_delegates(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    ws.format_header()
    gs["worksheets"]["A"].format.assert_called_once()


def test_add_dropdown_builds_validation_request(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].id = 0
    ws.add_dropdown("A1:A3", ["x", "y"])
    body = gs["spreadsheet"].batch_update.call_args[0][0]
    assert body["requests"][0]["setDataValidation"]["rule"]["condition"]["type"] == "ONE_OF_LIST"


def test_clear_whole_sheet(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.worksheet("A").clear()
    gs["worksheets"]["A"].clear.assert_called_once_with()


def test_create_sheet_returns_context_without_activating(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    new_ws = type(gs["worksheets"]["Sheet1"])(name="ws:Nueva")
    new_ws.title = "Nueva"
    gs["spreadsheet"].add_worksheet.return_value = new_ws
    ctx = mgr.create_sheet("Nueva", rows=10, cols=5)
    gs["spreadsheet"].add_worksheet.assert_called_once_with("Nueva", rows=10, cols=5, index=None)
    assert isinstance(ctx, WorksheetContext)
    assert isinstance(ctx.worksheet, GspreadWorksheet)
    assert ctx.worksheet.raw is new_ws


def test_document_ops(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.create_spreadsheet("Nuevo", folder_id="f1")
    gs["client"].create.assert_called_once_with("Nuevo", folder_id="f1")
    mgr.list_spreadsheets(title="x")
    gs["client"].list_spreadsheet_files.assert_called_once_with(title="x", folder_id=None)


def test_share_uses_managers_doc_by_default(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.share("a@b.com", role="writer")
    gs["spreadsheet"].share.assert_called_once()


def test_sheet_manager_does_not_warn(gs):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")


# --- Cobertura de las operaciones de WorksheetContext (wiring) ---


def test_update_row(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.worksheet("A").update_row(5, ["a", "b"], start_column=2)
    assert gs["worksheets"]["A"].update_cell.call_count == 2


def test_read_list(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["h"], ["1"]]
    assert ws.read() == [["h"], ["1"]]


def test_last_row(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["h"], ["1"], ["2"]]
    assert ws.last_row() == 3


def test_rows_where_column_equals(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["x", "ok"], ["y", "no"]]
    assert ws.rows_where_column_equals(1, "ok") == [(1, ["x", "ok"])]


def test_batch_update_uses_enum(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.worksheet("A").batch_update([{"range": "A1", "values": [["x"]]}])
    _, kwargs = gs["worksheets"]["A"].batch_update.call_args
    assert kwargs["value_input_option"] == ValueInputOption.user_entered


def test_insert_delegates(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("Hoja1")
    gs["worksheets"]["Hoja1"].get_all_values.return_value = []
    ws.insert([["a", "b"]], fila=1)
    args = gs["spreadsheet"].values_append.call_args[0]
    assert args[0] == "Hoja1!A1:B1"


def test_set_background_and_text_and_number(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    ws.set_background("A1", Color(red=1.0))
    ws.set_text_format("A1", bold=True)
    ws.set_number_format("A1", "0.00%", "PERCENT")
    assert gs["worksheets"]["A"].format.call_count == 3


def test_freeze_and_merge(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    ws.freeze(rows=1, cols=2)
    ws.merge("A1:B2")
    gs["worksheets"]["A"].freeze.assert_called_once_with(rows=1, cols=2)
    gs["worksheets"]["A"].merge_cells.assert_called_once_with("A1:B2", merge_type="MERGE_ALL")


def test_add_checkbox_and_conditional_format(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].id = 0
    ws.add_checkbox("A1:A3")
    ws.add_conditional_format("B1:B3", "NUMBER_LESS", [0], CellFormat(background_color=Color()))
    assert gs["spreadsheet"].batch_update.call_count == 2


def test_find(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.worksheet("A").find("Total")
    gs["worksheets"]["A"].find.assert_called_once_with("Total", case_sensitive=True)


def test_read_dataframe(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    gs["worksheets"]["A"].get_all_values.return_value = [["a", "b"], ["1", "2"]]
    df = ws.read_dataframe()
    assert list(df.columns) == ["a", "b"]


def test_write_dataframe_uses_enum(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    ws = mgr.worksheet("A")
    ws.write_dataframe(pd.DataFrame([["x"]], columns=["c"]))
    gs["worksheets"]["A"].clear.assert_called_once_with()
    _, kwargs = gs["worksheets"]["A"].update.call_args
    assert kwargs["value_input_option"] == ValueInputOption.user_entered


# --- Cobertura de las operaciones a nivel documento de SheetManager ---


def test_delete_sheet(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.delete_sheet("Vieja")
    called_with = gs["spreadsheet"].del_worksheet.call_args[0][0]
    assert called_with is gs["worksheets"]["Vieja"]


def test_delete_and_copy_spreadsheet(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.delete_spreadsheet("file1")
    gs["client"].del_spreadsheet.assert_called_once_with("file1")
    mgr.copy_spreadsheet("file1", title="Copia")
    gs["client"].copy.assert_called_once_with(
        "file1", title="Copia", copy_permissions=False, folder_id=None
    )


def test_list_and_remove_permissions(gs):
    mgr = SheetManager("Doc", "fake.json", backend="gspread")
    mgr.list_permissions()
    gs["spreadsheet"].list_permissions.assert_called_once()
    mgr.remove_permission("a@b.com", role="writer")
    gs["spreadsheet"].remove_permissions.assert_called_once_with("a@b.com", role="writer")


class TestOpenByKeyAndUrl:
    def test_open_by_key(self, gs):
        mgr = SheetManager.open_by_key("KEY123", "fake.json", backend="gspread")
        mgr.worksheet("A")
        gs["client"].open_by_key.assert_called_once_with("KEY123")
        gs["client"].open.assert_not_called()

    def test_open_by_url(self, gs):
        url = "https://docs.google.com/spreadsheets/d/KEY999/edit"
        mgr = SheetManager.open_by_url(url, "fake.json", backend="gspread")
        mgr.worksheet("A")
        gs["client"].open_by_key.assert_called_once_with("KEY999")

    def test_requires_name_or_key(self):
        with pytest.raises(GSpreadManagerError, match="doc_name"):
            SheetManager()


class TestReadNumericise:
    def test_read_list_numericise(self, gs):
        mgr = SheetManager("Doc", "fake.json", backend="gspread")
        ws = mgr.worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [["edad"], ["30"], ["x"]]
        assert ws.read(numericise=True) == [["edad"], [30], ["x"]]

    def test_read_dict_numericise(self, gs):
        mgr = SheetManager("Doc", "fake.json", backend="gspread")
        ws = mgr.worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [["n", "edad"], ["Ana", "30"]]
        assert ws.read(output_format="dict", numericise=True) == [{"n": "Ana", "edad": 30}]


class TestDimensions:
    def _request(self, gs: Any) -> Any:
        return gs["spreadsheet"].batch_update.call_args[0][0]["requests"][0]

    def test_insert_rows_translates_index(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.insert_rows(3, number=2)
        rng = self._request(gs)["insertDimension"]["range"]
        assert rng == {"sheetId": 0, "dimension": "ROWS", "startIndex": 2, "endIndex": 4}

    def test_delete_cols_inclusive(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.delete_cols(2, 4)
        rng = self._request(gs)["deleteDimension"]["range"]
        assert rng == {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 4}

    def test_add_rows(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.add_rows(5)
        assert self._request(gs)["appendDimension"] == {
            "sheetId": 0,
            "dimension": "ROWS",
            "length": 5,
        }

    def test_hide_and_resize(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.hide_rows(2)
        assert self._request(gs)["updateDimensionProperties"]["properties"] == {
            "hiddenByUser": True
        }
        ws.resize_cols(1, 3, 120)
        upd = self._request(gs)["updateDimensionProperties"]
        assert upd["properties"] == {"pixelSize": 120}
        assert upd["fields"] == "pixelSize"


class TestNotesAndRanges:
    def _request(self, gs: Any) -> Any:
        return gs["spreadsheet"].batch_update.call_args[0][0]["requests"][0]

    def test_update_note(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.update_note("B2", "revisar")
        req = self._request(gs)["updateCells"]
        assert req["rows"] == [{"values": [{"note": "revisar"}]}]
        assert req["fields"] == "note"

    def test_get_note(self, gs):
        # El adaptador gspread lee metadata vía fetch_sheet_metadata.
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("Hoja1")
        gs["spreadsheet"].fetch_sheet_metadata.return_value = {
            "sheets": [{"data": [{"rowData": [{"values": [{"note": "hola"}]}]}]}]
        }
        assert ws.get_note("B2") == "hola"
        gs["spreadsheet"].fetch_sheet_metadata.assert_called_once_with(
            {"fields": "sheets(data(rowData(values(note))))", "ranges": ["Hoja1!B2"]}
        )

    def test_define_named_range(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.define_named_range("Ventas", "A1:B10")
        assert self._request(gs)["addNamedRange"]["namedRange"]["name"] == "Ventas"

    def test_add_and_list_protected_ranges(self, gs):
        mgr = SheetManager("Doc", "fake.json", backend="gspread")
        ws = mgr.worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.add_protected_range("A1:A5", description="solo lectura")
        assert "addProtectedRange" in self._request(gs)
        gs["spreadsheet"].fetch_sheet_metadata.return_value = {
            "sheets": [
                {"properties": {"sheetId": 0}, "protectedRanges": [{"protectedRangeId": "p1"}]}
            ]
        }
        assert ws.list_protected_ranges() == [{"protectedRangeId": "p1"}]

    def test_manager_named_ranges(self, gs):
        mgr = SheetManager("Doc", "fake.json", backend="gspread")
        gs["spreadsheet"].fetch_sheet_metadata.return_value = {
            "namedRanges": [{"namedRangeId": "nr1"}]
        }
        assert mgr.list_named_ranges() == [{"namedRangeId": "nr1"}]
        mgr.delete_named_range("nr1")
        body = gs["spreadsheet"].batch_update.call_args[0][0]
        assert body["requests"][0] == {"deleteNamedRange": {"namedRangeId": "nr1"}}


class TestSortFilterMergeTab:
    def _request(self, gs: Any) -> Any:
        return gs["spreadsheet"].batch_update.call_args[0][0]["requests"][0]

    def test_sort_range_translates_specs(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.sort_range("A1:C10", (1, "asc"), (3, "desc"))
        req = self._request(gs)["sortRange"]
        assert req["sortSpecs"] == [
            {"dimensionIndex": 0, "sortOrder": "ASCENDING"},
            {"dimensionIndex": 2, "sortOrder": "DESCENDING"},
        ]

    def test_set_basic_filter_with_range(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.set_basic_filter("A1:C10")
        assert "setBasicFilter" in self._request(gs)

    def test_set_basic_filter_whole_sheet(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.set_basic_filter()
        assert self._request(gs)["setBasicFilter"]["filter"]["range"] == {"sheetId": 0}

    def test_clear_basic_filter(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.clear_basic_filter()
        assert self._request(gs) == {"clearBasicFilter": {"sheetId": 0}}

    def test_unmerge(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.unmerge("A1:B2")
        assert "unmergeCells" in self._request(gs)

    def test_set_and_clear_tab_color(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].id = 0
        ws.set_tab_color(Color(red=1.0))
        req = self._request(gs)["updateSheetProperties"]
        assert req["properties"]["tabColor"]["red"] == 1.0
        assert req["fields"] == "tabColor"
        ws.clear_tab_color()
        cleared = self._request(gs)["updateSheetProperties"]
        assert "tabColor" not in cleared["properties"]


class TestExport:
    def test_export_default_pdf(self, gs):
        mgr = SheetManager("Doc", "fake.json", backend="gspread")
        gs["spreadsheet"].export.return_value = b"%PDF-1.7"
        data = mgr.export()
        assert data == b"%PDF-1.7"
        gs["spreadsheet"].export.assert_called_once_with(format="application/pdf")

    def test_export_explicit_format(self, gs):
        mgr = SheetManager("Doc", "fake.json", backend="gspread")
        gs["spreadsheet"].export.return_value = b"col1,col2"
        data = mgr.export(ExportFormat.CSV)
        assert data == b"col1,col2"
        gs["spreadsheet"].export.assert_called_once_with(format="text/csv")


class TestDataframeAdvanced:
    def test_read_dataframe_drop_empty(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [
            ["name", "extra"],
            ["Ana", ""],
            ["", ""],
        ]
        df = ws.read_dataframe(drop_empty_rows=True, drop_empty_cols=True)
        assert list(df.columns) == ["name"]
        assert df.values.tolist() == [["Ana"]]

    def test_read_dataframe_index_col(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [["id", "name"], ["1", "Ana"]]
        df = ws.read_dataframe(index_col="id")
        assert df.index.name == "id"
        assert list(df.columns) == ["name"]

    def test_write_dataframe_anchor_and_index(self, gs):
        ws = SheetManager("Doc", "fake.json", backend="gspread").worksheet("A")
        df = pd.DataFrame([["Ana"]], columns=["name"], index=pd.Index(["1"], name="id"))
        ws.write_dataframe(df, clear=False, start_cell="B2", include_index=True)
        kwargs = gs["worksheets"]["A"].update.call_args.kwargs
        assert kwargs["range_name"] == "B2"
        assert kwargs["values"] == [["id", "name"], ["1", "Ana"]]

    def test_polars_backend(self, gs):
        pytest.importorskip("polars")
        ws = SheetManager("Doc", "fake.json", backend="gspread", dataframe_backend="polars").worksheet("A")
        gs["worksheets"]["A"].get_all_values.return_value = [["name", "age"], ["Ana", "3"]]
        df = ws.read_dataframe()
        assert df.columns == ["name", "age"]
        assert df.rows() == [("Ana", "3")]

    def test_unknown_backend_raises(self, gs):
        with pytest.raises(GSpreadManagerError, match="desconocido"):
            SheetManager("Doc", "fake.json", backend="gspread", dataframe_backend="dask")
