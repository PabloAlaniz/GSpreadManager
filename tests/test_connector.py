"""
Tests for GoogleSheetConector class.
Uses mocking to avoid actual Google API calls.
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest
from gspread.exceptions import APIError
from gspread.utils import ValueInputOption

from gspreadmanager import GoogleSheetConector, InsertError


def make_api_error(status_code: int) -> APIError:
    """Construye un APIError de gspread con el código de estado HTTP dado."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {
        "error": {"code": status_code, "message": "boom", "status": "ERROR"}
    }
    response.text = "boom"
    return APIError(response)


class TestGoogleSheetConector:
    """Tests for GoogleSheetConector class."""

    @pytest.fixture
    def mock_credentials(self):
        """Mock Google credentials."""
        with patch("gspreadmanager.connector.service_account.Credentials") as mock_creds:
            mock_creds.from_service_account_file.return_value = Mock()
            yield mock_creds

    @pytest.fixture
    def mock_gspread(self):
        """Mock gspread client and worksheet."""
        with patch("gspreadmanager.connector.gspread") as mock_gs:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()

            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet

            yield {
                "gspread": mock_gs,
                "client": mock_client,
                "spreadsheet": mock_spreadsheet,
                "worksheet": mock_worksheet,
            }

    @pytest.fixture
    def connector(self, mock_credentials, mock_gspread):
        """Create a GoogleSheetConector instance with mocked dependencies."""
        return GoogleSheetConector("TestDoc", "fake_credentials.json", "Sheet1")

    def test_init_with_sheet_name(self, connector):
        """Test initialization with specific sheet name."""
        assert connector.sheet_title == "TestDoc"
        assert connector.tab_name == "Sheet1"
        assert connector.sheet is not None

    def test_init_without_sheet_name(self, mock_credentials, mock_gspread):
        """Test initialization without sheet name (uses sheet1)."""
        conn = GoogleSheetConector("TestDoc", "fake_credentials.json")
        assert conn.tab_name is None
        assert conn.sheet is not None

    def test_init_retry_defaults(self, connector):
        """Test that retry configuration has sensible defaults."""
        assert connector.max_retries == 3
        assert connector.retry_backoff == 1.0

    def test_update_cell(self, connector):
        """Test updating a single cell uses the connector's active sheet."""
        connector.update_cell(1, 1, "Test Value")
        connector.sheet.update_cell.assert_called_once_with(1, 1, "Test Value")

    def test_update_row(self, connector):
        """Test updating a row of data."""
        data = ["A", "B", "C"]

        # The method calls update_cell for each value
        connector.update_row(2, data)

        # Should call update_cell 3 times (one for each value)
        assert connector.sheet.update_cell.call_count == 3

    def test_read_sheet_data_list_format(self, connector, mock_gspread):
        """Test reading sheet data as list."""
        mock_worksheet = mock_gspread["worksheet"]
        mock_worksheet.get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
            ["Value3", "Value4"],
        ]

        result = connector.read_sheet_data(output_format="list")

        assert isinstance(result, list)
        mock_worksheet.get_all_values.assert_called()

    def test_read_sheet_data_dataframe_format(self, connector, mock_gspread):
        """Test reading sheet data as DataFrame."""
        mock_worksheet = mock_gspread["worksheet"]
        mock_worksheet.get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
            ["Value3", "Value4"],
        ]

        result = connector.read_sheet_data(output_format="pandas")

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["Header1", "Header2"]

    def test_read_sheet_data_with_skiprows(self, connector, mock_gspread):
        """Test reading sheet data with skipped rows."""
        mock_worksheet = mock_gspread["worksheet"]
        mock_worksheet.get_all_values.return_value = [
            ["Skip this"],
            ["Header1", "Header2"],
            ["Value1", "Value2"],
        ]

        result = connector.read_sheet_data(skiprows=1, output_format="pandas")

        # After skipping 1 row, headers should be from row 2
        assert isinstance(result, pd.DataFrame)

    def test_get_rows_where_column_equals(self, connector, mock_gspread):
        """Test filtering rows by column value."""
        mock_worksheet = mock_gspread["worksheet"]
        mock_worksheet.get_all_values.return_value = [
            ["Name", "Status"],
            ["Alice", "Active"],
            ["Bob", "Inactive"],
            ["Charlie", "Active"],
        ]

        # Column 1 is "Status", looking for "Active"
        result = connector.get_rows_where_column_equals(1, "Active")

        # Should return tuples of (row_number, row_data) where Status == "Active"
        assert isinstance(result, list)
        assert len(result) == 2  # Alice and Charlie have "Active"

    def test_spreadsheet_append(self, connector, mock_gspread):
        """Test appending data to spreadsheet."""
        mock_worksheet = mock_gspread["worksheet"]
        data = [["New1", "Data1"], ["New2", "Data2"]]

        connector.spreadsheet_append(data)

        mock_worksheet.append_rows.assert_called()

    def test_spreadsheet_append_uses_enum(self, connector, mock_gspread):
        """Test that append uses the ValueInputOption enum (not a raw string)."""
        connector.spreadsheet_append([["a", "b"]])

        _, kwargs = mock_gspread["worksheet"].append_rows.call_args
        assert kwargs["value_input_option"] == ValueInputOption.user_entered

    def test_get_last_row(self, connector, mock_gspread):
        """Test getting the last row number."""
        mock_worksheet = mock_gspread["worksheet"]
        mock_worksheet.get_all_values.return_value = [["Header"], ["Row1"], ["Row2"], ["Row3"]]

        result = connector.get_last_row()

        assert result == 4  # 4 rows total

    def test_get_last_row_empty_sheet(self, connector, mock_gspread):
        """Test getting last row on empty sheet."""
        mock_worksheet = mock_gspread["worksheet"]
        mock_worksheet.get_all_values.return_value = []

        result = connector.get_last_row()

        assert result == 0

    def test_batch_update(self, connector, mock_gspread):
        """Test batch updating multiple ranges."""
        mock_worksheet = mock_gspread["worksheet"]

        range_data = [{"range": "A1:B2", "values": [["a", "b"], ["c", "d"]]}]

        connector.batch_update(range_data)

        # Should call batch_update on the worksheet
        mock_worksheet.batch_update.assert_called()

    def test_options_default_value(self, connector):
        """Test that options has correct default value."""
        assert connector.options == {"valueInputOption": "USER_ENTERED"}


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_all(self):
        """Mock all external dependencies."""
        with (
            patch("gspreadmanager.connector.service_account.Credentials") as mock_creds,
            patch("gspreadmanager.connector.gspread") as mock_gs,
        ):
            mock_creds.from_service_account_file.return_value = Mock()
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()

            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet

            yield {"worksheet": mock_worksheet, "spreadsheet": mock_spreadsheet}

    def test_read_empty_sheet(self, mock_all):
        """Test reading from an empty sheet."""
        mock_all["worksheet"].get_all_values.return_value = []

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format="list")

        assert result == []

    def test_read_single_row_sheet(self, mock_all):
        """Test reading sheet with only headers."""
        mock_all["worksheet"].get_all_values.return_value = [["Header1", "Header2"]]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format="pandas")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # No data rows, only headers

    def test_update_cell_with_number(self, mock_all):
        """Test updating cell with numeric value."""
        conn = GoogleSheetConector("TestDoc", "fake.json")

        conn.update_cell(1, 1, 42)
        mock_all["worksheet"].update_cell.assert_called_with(1, 1, 42)

    def test_update_cell_with_none(self, mock_all):
        """Test updating cell with None value."""
        conn = GoogleSheetConector("TestDoc", "fake.json")

        conn.update_cell(1, 1, None)
        mock_all["worksheet"].update_cell.assert_called_with(1, 1, None)

    def test_read_sheet_data_dict_format(self, mock_all):
        """Test reading sheet data as list of dictionaries."""
        mock_all["worksheet"].get_all_values.return_value = [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"],
        ]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format="dict")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"Name": "Alice", "Age": "30", "City": "NYC"}
        assert result[1] == {"Name": "Bob", "Age": "25", "City": "LA"}

    def test_read_sheet_data_dict_empty(self, mock_all):
        """Test reading empty sheet as dict returns empty list."""
        mock_all["worksheet"].get_all_values.return_value = []

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format="dict")

        assert result == []

    def test_spreadsheet_read_range(self, mock_all):
        """Test reading a specific range from spreadsheet."""
        mock_all["worksheet"].spreadsheet.values_get.return_value = {
            "values": [["A1", "B1", "C1"], ["A2", "B2", "C2"], ["A3", "B3", "C3"]]
        }

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.spreadsheet_read_range("Sheet1", 1, 3, "A", "C")

        assert len(result) == 3
        assert result[0] == {"fila": 1, "values": ["A1", "B1", "C1"]}
        assert result[1] == {"fila": 2, "values": ["A2", "B2", "C2"]}
        assert result[2] == {"fila": 3, "values": ["A3", "B3", "C3"]}
        # El rango se construye en notación A1 incluyendo la pestaña
        mock_all["worksheet"].spreadsheet.values_get.assert_called_once_with("Sheet1!A1:C3")

    def test_spreadsheet_read_range_empty(self, mock_all):
        """Test reading empty range returns empty list."""
        mock_all["worksheet"].spreadsheet.values_get.return_value = {}

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.spreadsheet_read_range("Sheet1", 1, 3, "A", "C")

        assert result == []

    def test_get_row_with_empty_in_column_found(self, mock_all):
        """Test finding row with empty cell in column."""
        worksheet = mock_all["worksheet"]
        worksheet.col_values.return_value = ["Header", "Value1", "", "Value3"]
        worksheet.range.return_value = [
            Mock(value="Header"),
            Mock(value="Value1"),
            Mock(value=""),
            Mock(value="Value3"),
        ]
        worksheet.row_values.return_value = ["Data", "", "MoreData"]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        row, index = conn.get_row_with_empty_in_column("B")

        assert index == 3  # Empty cell is at row 3
        assert row == ["Data", "", "MoreData"]

    def test_get_row_with_empty_in_column_not_found(self, mock_all):
        """Test when no empty cell exists in column."""
        worksheet = mock_all["worksheet"]
        worksheet.col_values.return_value = ["Header", "Value1", "Value2"]
        worksheet.range.return_value = [
            Mock(value="Header"),
            Mock(value="Value1"),
            Mock(value="Value2"),
        ]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        row, index = conn.get_row_with_empty_in_column("B")

        assert row is None
        assert index is None

    def test_spreadsheet_insert_at_row(self, mock_all):
        """Test inserting data at specific row."""
        mock_all["worksheet"].spreadsheet.values_append.return_value = {
            "updates": {"updatedRows": 2}
        }

        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["A", "B"], ["C", "D"]]

        result = conn.spreadsheet_insert("TestDoc", "Sheet1", data, fila=5)

        mock_all["worksheet"].spreadsheet.values_append.assert_called()
        assert result is not None

    def test_spreadsheet_insert_at_end(self, mock_all):
        """Test inserting data at end of sheet."""
        mock_all["worksheet"].get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Data1", "Data2"],
        ]
        mock_all["worksheet"].spreadsheet.values_append.return_value = {
            "updates": {"updatedRows": 1}
        }

        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["New1", "New2"]]

        conn.spreadsheet_insert("TestDoc", "Sheet1", data)

        mock_all["worksheet"].spreadsheet.values_append.assert_called()

    def test_spreadsheet_insert_wide_range(self, mock_all):
        """Test that inserting >26 columns builds a correct A1 range (beyond Z)."""
        mock_all["worksheet"].spreadsheet.values_append.return_value = {}

        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [list(range(28))]  # 28 columnas -> termina en AB

        conn.spreadsheet_insert("TestDoc", "Sheet1", data, fila=1)

        rango = mock_all["worksheet"].spreadsheet.values_append.call_args[0][0]
        assert rango == "Sheet1!A1:AB1"

    def test_spreadsheet_insert_invalid_data(self, mock_all):
        """Test inserting invalid data raises error."""
        conn = GoogleSheetConector("TestDoc", "fake.json")

        # Data is not list of lists
        with pytest.raises(ValueError, match="lista de listas"):
            conn.spreadsheet_insert("TestDoc", "Sheet1", ["not", "nested"])

    def test_spreadsheet_insert_uneven_rows(self, mock_all):
        """Test inserting rows of different lengths raises error."""
        conn = GoogleSheetConector("TestDoc", "fake.json")

        # Rows have different lengths
        data = [["A", "B", "C"], ["D", "E"]]
        with pytest.raises(ValueError, match="misma longitud"):
            conn.spreadsheet_insert("TestDoc", "Sheet1", data)

    def test_update_row_with_start_column(self, mock_all):
        """Test updating row starting from specific column."""
        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = ["X", "Y", "Z"]

        conn.update_row(3, data, start_column=5)

        # Should start from column 5
        calls = mock_all["worksheet"].update_cell.call_args_list
        assert calls[0][0] == (3, 5, "X")
        assert calls[1][0] == (3, 6, "Y")
        assert calls[2][0] == (3, 7, "Z")

    def test_spreadsheet_append_with_tab_name(self, mock_all):
        """Test appending data with specific tab name."""
        mock_all["worksheet"].append_rows.return_value = {"updates": {"updatedRows": 2}}

        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["A", "B"], ["C", "D"]]

        conn.spreadsheet_append(data, tab_name="OtherSheet")

        mock_all["worksheet"].append_rows.assert_called()

    def test_get_last_row_with_tab_name(self, mock_all):
        """Test getting last row with specific tab name."""
        mock_all["worksheet"].get_all_values.return_value = [["Row1"], ["Row2"], ["Row3"]]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.get_last_row(tab_name="SpecificTab")

        assert result == 3

    def test_read_sheet_data_with_tab_name(self, mock_all):
        """Test reading data with specific tab name."""
        mock_all["worksheet"].get_all_values.return_value = [["Header"], ["Data"]]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(tab_name="CustomTab", output_format="list")

        assert len(result) == 2

    def test_spreadsheet_insert_api_error(self, mock_all):
        """Test spreadsheet_insert wraps API errors in InsertError."""
        mock_all["worksheet"].spreadsheet.values_append.side_effect = Exception(
            "API quota exceeded"
        )
        mock_all["worksheet"].get_all_values.return_value = [["Row1"]]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["A", "B"]]

        with pytest.raises(InsertError, match="Error al insertar datos en Sheet1"):
            conn.spreadsheet_insert("TestDoc", "Sheet1", data)


class TestRetry:
    """Tests for the rate-limit retry behaviour."""

    @pytest.fixture
    def mock_all(self):
        with (
            patch("gspreadmanager.connector.service_account.Credentials") as mock_creds,
            patch("gspreadmanager.connector.gspread") as mock_gs,
        ):
            mock_creds.from_service_account_file.return_value = Mock()
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()

            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet

            yield {"worksheet": mock_worksheet, "spreadsheet": mock_spreadsheet}

    def test_retry_then_success(self, mock_all):
        """A transient 429 is retried and the call eventually succeeds."""
        conn = GoogleSheetConector("TestDoc", "fake.json", max_retries=2, retry_backoff=0)
        mock_all["worksheet"].get_all_values.side_effect = [
            make_api_error(429),
            make_api_error(429),
            [["a"], ["b"]],
        ]

        with patch("gspreadmanager.retry.time.sleep") as mock_sleep:
            result = conn.get_last_row()

        assert result == 2
        assert mock_sleep.call_count == 2

    def test_retry_exhausted_raises(self, mock_all):
        """When retries are exhausted, the APIError propagates."""
        conn = GoogleSheetConector("TestDoc", "fake.json", max_retries=1, retry_backoff=0)
        mock_all["worksheet"].get_all_values.side_effect = make_api_error(429)

        with patch("gspreadmanager.retry.time.sleep"), pytest.raises(APIError):
            conn.get_last_row()

    def test_non_retryable_error_not_retried(self, mock_all):
        """A non-retryable status (e.g. 403) is not retried."""
        conn = GoogleSheetConector("TestDoc", "fake.json", max_retries=3, retry_backoff=0)
        mock_all["worksheet"].get_all_values.side_effect = make_api_error(403)

        with patch("gspreadmanager.retry.time.sleep") as mock_sleep, pytest.raises(APIError):
            conn.get_last_row()

        mock_sleep.assert_not_called()


class TestDeprecation:
    """Tests for the deprecated 'sheet' parameter."""

    @pytest.fixture
    def mock_all(self):
        with (
            patch("gspreadmanager.connector.service_account.Credentials") as mock_creds,
            patch("gspreadmanager.connector.gspread") as mock_gs,
        ):
            mock_creds.from_service_account_file.return_value = Mock()
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()

            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet

            yield {"worksheet": mock_worksheet, "spreadsheet": mock_spreadsheet}

    def test_passing_sheet_emits_deprecation_warning(self, mock_all):
        """Passing the legacy 'sheet' argument warns but still works."""
        conn = GoogleSheetConector("TestDoc", "fake.json")
        legacy_sheet = Mock()

        with pytest.warns(DeprecationWarning):
            conn.update_cell(1, 1, "x", sheet=legacy_sheet)

        legacy_sheet.update_cell.assert_called_once_with(1, 1, "x")


class TestFeatures:
    """Tests for the higher-level feature methods added in 0.4.0."""

    @pytest.fixture
    def mock_all(self):
        with (
            patch("gspreadmanager.connector.service_account.Credentials") as mock_creds,
            patch("gspreadmanager.connector.gspread") as mock_gs,
        ):
            mock_creds.from_service_account_file.return_value = Mock()
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()
            # La hoja activa expone su Spreadsheet contenedor.
            mock_worksheet.spreadsheet = mock_spreadsheet

            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet

            yield {
                "worksheet": mock_worksheet,
                "spreadsheet": mock_spreadsheet,
                "client": mock_client,
            }

    def test_create_sheet(self, mock_all):
        new_ws = Mock()
        mock_all["spreadsheet"].add_worksheet.return_value = new_ws

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.create_sheet("NuevaHoja", rows=50, cols=5)

        mock_all["spreadsheet"].add_worksheet.assert_called_once_with(
            "NuevaHoja", rows=50, cols=5, index=None
        )
        assert result is new_ws

    def test_create_sheet_activate(self, mock_all):
        new_ws = Mock()
        new_ws.spreadsheet = mock_all["spreadsheet"]
        mock_all["spreadsheet"].add_worksheet.return_value = new_ws

        conn = GoogleSheetConector("TestDoc", "fake.json")
        conn.create_sheet("Activa", activate=True)

        assert conn.sheet is new_ws
        assert conn.tab_name == "Activa"

    def test_delete_sheet(self, mock_all):
        target = Mock()
        mock_all["spreadsheet"].worksheet.return_value = target

        conn = GoogleSheetConector("TestDoc", "fake.json")
        conn.delete_sheet("Vieja")

        mock_all["spreadsheet"].worksheet.assert_called_with("Vieja")
        mock_all["spreadsheet"].del_worksheet.assert_called_once_with(target)

    def test_clear_range_single(self, mock_all):
        conn = GoogleSheetConector("TestDoc", "fake.json")
        conn.clear_range("A1:C10")

        mock_all["worksheet"].batch_clear.assert_called_once_with(["A1:C10"])

    def test_clear_range_multiple(self, mock_all):
        conn = GoogleSheetConector("TestDoc", "fake.json")
        conn.clear_range(["A1:A5", "C1:C5"])

        mock_all["worksheet"].batch_clear.assert_called_once_with(["A1:A5", "C1:C5"])

    def test_clear_range_whole_sheet(self, mock_all):
        conn = GoogleSheetConector("TestDoc", "fake.json")
        conn.clear_range()

        mock_all["worksheet"].clear.assert_called_once()
        mock_all["worksheet"].batch_clear.assert_not_called()

    def test_find_cell_found(self, mock_all):
        cell = Mock(row=4, col=2, value="Total")
        mock_all["worksheet"].find.return_value = cell

        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.find_cell("Total")

        assert result is cell
        mock_all["worksheet"].find.assert_called_once_with("Total", case_sensitive=True)

    def test_find_cell_not_found(self, mock_all):
        mock_all["worksheet"].find.return_value = None

        conn = GoogleSheetConector("TestDoc", "fake.json")
        assert conn.find_cell("nope") is None

    def test_from_gsheet(self, mock_all):
        mock_all["worksheet"].get_all_values.return_value = [
            ["Name", "Age"],
            ["Alice", "30"],
            ["Bob", "25"],
        ]

        conn = GoogleSheetConector("TestDoc", "fake.json")
        df = conn.from_gsheet()

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["Name", "Age"]
        assert len(df) == 2

    def test_to_gsheet(self, mock_all):
        conn = GoogleSheetConector("TestDoc", "fake.json")
        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [30, 25]})

        conn.to_gsheet(df)

        mock_all["worksheet"].clear.assert_called_once()
        values = mock_all["worksheet"].update.call_args[0][0]
        assert values[0] == ["Name", "Age"]
        assert values[1] == ["Alice", 30]
        assert values[2] == ["Bob", 25]

    def test_to_gsheet_no_header_no_clear(self, mock_all):
        conn = GoogleSheetConector("TestDoc", "fake.json")
        df = pd.DataFrame({"A": [1], "B": [2]})

        conn.to_gsheet(df, include_header=False, clear=False)

        mock_all["worksheet"].clear.assert_not_called()
        values = mock_all["worksheet"].update.call_args[0][0]
        assert values == [[1, 2]]

    def test_context_manager(self, mock_all):
        with GoogleSheetConector("TestDoc", "fake.json") as conn:
            assert isinstance(conn, GoogleSheetConector)
            assert conn.sheet is mock_all["worksheet"]
