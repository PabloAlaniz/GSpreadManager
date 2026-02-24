"""
Tests for GoogleSheetConector class.
Uses mocking to avoid actual Google API calls.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd


class TestGoogleSheetConector:
    """Tests for GoogleSheetConector class."""

    @pytest.fixture
    def mock_credentials(self):
        """Mock Google credentials."""
        with patch('gspreadmanager.connector.service_account.Credentials') as mock_creds:
            mock_creds.from_service_account_file.return_value = Mock()
            yield mock_creds

    @pytest.fixture
    def mock_gspread(self):
        """Mock gspread client and worksheet."""
        with patch('gspreadmanager.connector.gspread') as mock_gs:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()
            
            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet
            
            yield {
                'gspread': mock_gs,
                'client': mock_client,
                'spreadsheet': mock_spreadsheet,
                'worksheet': mock_worksheet
            }

    @pytest.fixture
    def connector(self, mock_credentials, mock_gspread):
        """Create a GoogleSheetConector instance with mocked dependencies."""
        from gspreadmanager.connector import GoogleSheetConector
        return GoogleSheetConector("TestDoc", "fake_credentials.json", "Sheet1")

    def test_init_with_sheet_name(self, connector):
        """Test initialization with specific sheet name."""
        assert connector.sheet_title == "TestDoc"
        assert connector.tab_name == "Sheet1"
        assert connector.sheet is not None

    def test_init_without_sheet_name(self, mock_credentials, mock_gspread):
        """Test initialization without sheet name (uses sheet1)."""
        from gspreadmanager.connector import GoogleSheetConector
        conn = GoogleSheetConector("TestDoc", "fake_credentials.json")
        assert conn.tab_name is None
        assert conn.sheet is not None

    def test_update_cell(self, connector):
        """Test updating a single cell."""
        mock_sheet = Mock()
        connector.update_cell(mock_sheet, 1, 1, "Test Value")
        mock_sheet.update_cell.assert_called_once_with(1, 1, "Test Value")

    def test_update_row(self, connector):
        """Test updating a row of data."""
        mock_sheet = Mock()
        data = ["A", "B", "C"]
        
        # The method calls update_cell for each value
        connector.update_row(mock_sheet, 2, data)
        
        # Should call update_cell 3 times (one for each value)
        assert mock_sheet.update_cell.call_count == 3

    def test_read_sheet_data_list_format(self, connector, mock_gspread):
        """Test reading sheet data as list."""
        mock_worksheet = mock_gspread['worksheet']
        mock_worksheet.get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
            ["Value3", "Value4"]
        ]
        
        result = connector.read_sheet_data(output_format='list')
        
        assert isinstance(result, list)
        mock_worksheet.get_all_values.assert_called()

    def test_read_sheet_data_dataframe_format(self, connector, mock_gspread):
        """Test reading sheet data as DataFrame."""
        mock_worksheet = mock_gspread['worksheet']
        mock_worksheet.get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
            ["Value3", "Value4"]
        ]
        
        result = connector.read_sheet_data(output_format='pandas')
        
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["Header1", "Header2"]

    def test_read_sheet_data_with_skiprows(self, connector, mock_gspread):
        """Test reading sheet data with skipped rows."""
        mock_worksheet = mock_gspread['worksheet']
        mock_worksheet.get_all_values.return_value = [
            ["Skip this"],
            ["Header1", "Header2"],
            ["Value1", "Value2"]
        ]
        
        result = connector.read_sheet_data(skiprows=1, output_format='pandas')
        
        # After skipping 1 row, headers should be from row 2
        assert isinstance(result, pd.DataFrame)

    def test_get_rows_where_column_equals(self, connector, mock_gspread):
        """Test filtering rows by column value."""
        mock_worksheet = mock_gspread['worksheet']
        mock_worksheet.get_all_values.return_value = [
            ["Name", "Status"],
            ["Alice", "Active"],
            ["Bob", "Inactive"],
            ["Charlie", "Active"]
        ]
        
        # Column 1 is "Status", looking for "Active"
        result = connector.get_rows_where_column_equals(1, "Active")
        
        # Should return tuples of (row_number, row_data) where Status == "Active"
        assert isinstance(result, list)
        assert len(result) == 2  # Alice and Charlie have "Active"

    def test_spreadsheet_append(self, connector, mock_gspread):
        """Test appending data to spreadsheet."""
        mock_worksheet = mock_gspread['worksheet']
        data = [["New1", "Data1"], ["New2", "Data2"]]
        
        connector.spreadsheet_append(data)
        
        mock_worksheet.append_rows.assert_called()

    def test_get_last_row(self, connector, mock_gspread):
        """Test getting the last row number."""
        mock_worksheet = mock_gspread['worksheet']
        mock_worksheet.get_all_values.return_value = [
            ["Header"],
            ["Row1"],
            ["Row2"],
            ["Row3"]
        ]
        
        result = connector.get_last_row()
        
        assert result == 4  # 4 rows total

    def test_get_last_row_empty_sheet(self, connector, mock_gspread):
        """Test getting last row on empty sheet."""
        mock_worksheet = mock_gspread['worksheet']
        mock_worksheet.get_all_values.return_value = []
        
        result = connector.get_last_row()
        
        assert result == 0

    def test_batch_update(self, connector, mock_gspread):
        """Test batch updating multiple ranges."""
        mock_worksheet = mock_gspread['worksheet']
        
        range_data = [
            {"range": "A1:B2", "values": [["a", "b"], ["c", "d"]]}
        ]
        
        connector.batch_update(range_data)
        
        # Should call batch_update on the worksheet
        mock_worksheet.batch_update.assert_called()

    def test_options_default_value(self, connector):
        """Test that options has correct default value."""
        assert connector.options == {'valueInputOption': 'USER_ENTERED'}


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_all(self):
        """Mock all external dependencies."""
        with patch('gspreadmanager.connector.service_account.Credentials') as mock_creds, \
             patch('gspreadmanager.connector.gspread') as mock_gs:
            
            mock_creds.from_service_account_file.return_value = Mock()
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()
            
            mock_gs.authorize.return_value = mock_client
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_spreadsheet.sheet1 = mock_worksheet
            
            yield {
                'worksheet': mock_worksheet,
                'spreadsheet': mock_spreadsheet
            }

    def test_read_empty_sheet(self, mock_all):
        """Test reading from an empty sheet."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = []
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format='list')
        
        assert result == []

    def test_read_single_row_sheet(self, mock_all):
        """Test reading sheet with only headers."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = [["Header1", "Header2"]]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format='pandas')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # No data rows, only headers

    def test_update_cell_with_number(self, mock_all):
        """Test updating cell with numeric value."""
        from gspreadmanager.connector import GoogleSheetConector
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        mock_sheet = Mock()
        
        conn.update_cell(mock_sheet, 1, 1, 42)
        mock_sheet.update_cell.assert_called_with(1, 1, 42)

    def test_update_cell_with_none(self, mock_all):
        """Test updating cell with None value."""
        from gspreadmanager.connector import GoogleSheetConector
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        mock_sheet = Mock()
        
        conn.update_cell(mock_sheet, 1, 1, None)
        mock_sheet.update_cell.assert_called_with(1, 1, None)

    def test_read_sheet_data_dict_format(self, mock_all):
        """Test reading sheet data as list of dictionaries."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"]
        ]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format='dict')
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"Name": "Alice", "Age": "30", "City": "NYC"}
        assert result[1] == {"Name": "Bob", "Age": "25", "City": "LA"}

    def test_read_sheet_data_dict_empty(self, mock_all):
        """Test reading empty sheet as dict returns empty list."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = []
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(output_format='dict')
        
        assert result == []

    def test_spreadsheet_read_range(self, mock_all):
        """Test reading a specific range from spreadsheet."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].values_get.return_value = {
            'values': [
                ["A1", "B1", "C1"],
                ["A2", "B2", "C2"],
                ["A3", "B3", "C3"]
            ]
        }
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.spreadsheet_read_range(
            mock_all['worksheet'], "Sheet1", 1, 3, "A", "C"
        )
        
        assert len(result) == 3
        assert result[0] == {"fila": 1, "values": ["A1", "B1", "C1"]}
        assert result[1] == {"fila": 2, "values": ["A2", "B2", "C2"]}
        assert result[2] == {"fila": 3, "values": ["A3", "B3", "C3"]}

    def test_spreadsheet_read_range_empty(self, mock_all):
        """Test reading empty range returns empty list."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].values_get.return_value = {}
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.spreadsheet_read_range(
            mock_all['worksheet'], "Sheet1", 1, 3, "A", "C"
        )
        
        assert result == []

    def test_get_row_with_empty_in_column_found(self, mock_all):
        """Test finding row with empty cell in column."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_sheet = Mock()
        mock_sheet.col_values.return_value = ["Header", "Value1", "", "Value3"]
        mock_sheet.range.return_value = [
            Mock(value="Header"),
            Mock(value="Value1"),
            Mock(value=""),
            Mock(value="Value3")
        ]
        mock_sheet.row_values.return_value = ["Data", "", "MoreData"]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        row, index = conn.get_row_with_empty_in_column(mock_sheet, 'B')
        
        assert index == 3  # Empty cell is at row 3
        assert row == ["Data", "", "MoreData"]

    def test_get_row_with_empty_in_column_not_found(self, mock_all):
        """Test when no empty cell exists in column."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_sheet = Mock()
        mock_sheet.col_values.return_value = ["Header", "Value1", "Value2"]
        mock_sheet.range.return_value = [
            Mock(value="Header"),
            Mock(value="Value1"),
            Mock(value="Value2")
        ]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        row, index = conn.get_row_with_empty_in_column(mock_sheet, 'B')
        
        assert row is None
        assert index is None

    def test_spreadsheet_insert_at_row(self, mock_all):
        """Test inserting data at specific row."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].values_append.return_value = {"updates": {"updatedRows": 2}}
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["A", "B"], ["C", "D"]]
        
        result = conn.spreadsheet_insert("TestDoc", "Sheet1", data, fila=5)
        
        mock_all['worksheet'].values_append.assert_called()
        assert result is not None

    def test_spreadsheet_insert_at_end(self, mock_all):
        """Test inserting data at end of sheet."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Data1", "Data2"]
        ]
        mock_all['worksheet'].values_append.return_value = {"updates": {"updatedRows": 1}}
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["New1", "New2"]]
        
        result = conn.spreadsheet_insert("TestDoc", "Sheet1", data)
        
        mock_all['worksheet'].values_append.assert_called()

    def test_spreadsheet_insert_invalid_data(self, mock_all):
        """Test inserting invalid data raises error."""
        from gspreadmanager.connector import GoogleSheetConector
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        
        # Data is not list of lists
        with pytest.raises(ValueError, match="lista de listas"):
            conn.spreadsheet_insert("TestDoc", "Sheet1", ["not", "nested"])

    def test_spreadsheet_insert_uneven_rows(self, mock_all):
        """Test inserting rows of different lengths raises error."""
        from gspreadmanager.connector import GoogleSheetConector
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        
        # Rows have different lengths
        data = [["A", "B", "C"], ["D", "E"]]
        with pytest.raises(ValueError, match="misma longitud"):
            conn.spreadsheet_insert("TestDoc", "Sheet1", data)

    def test_update_row_with_start_column(self, mock_all):
        """Test updating row starting from specific column."""
        from gspreadmanager.connector import GoogleSheetConector
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        mock_sheet = Mock()
        data = ["X", "Y", "Z"]
        
        conn.update_row(mock_sheet, 3, data, start_column=5)
        
        # Should start from column 5
        calls = mock_sheet.update_cell.call_args_list
        assert calls[0][0] == (3, 5, "X")
        assert calls[1][0] == (3, 6, "Y")
        assert calls[2][0] == (3, 7, "Z")

    def test_spreadsheet_append_with_tab_name(self, mock_all):
        """Test appending data with specific tab name."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].append_rows.return_value = {"updates": {"updatedRows": 2}}
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["A", "B"], ["C", "D"]]
        
        result = conn.spreadsheet_append(data, tab_name="OtherSheet")
        
        mock_all['worksheet'].append_rows.assert_called()

    def test_get_last_row_with_tab_name(self, mock_all):
        """Test getting last row with specific tab name."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = [
            ["Row1"], ["Row2"], ["Row3"]
        ]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.get_last_row(tab_name="SpecificTab")
        
        assert result == 3

    def test_read_sheet_data_with_tab_name(self, mock_all):
        """Test reading data with specific tab name."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].get_all_values.return_value = [
            ["Header"], ["Data"]
        ]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        result = conn.read_sheet_data(tab_name="CustomTab", output_format='list')
        
        assert len(result) == 2

    def test_spreadsheet_insert_api_error(self, mock_all):
        """Test spreadsheet_insert wraps API errors properly."""
        from gspreadmanager.connector import GoogleSheetConector
        
        mock_all['worksheet'].values_append.side_effect = Exception("API quota exceeded")
        mock_all['worksheet'].get_all_values.return_value = [["Row1"]]
        
        conn = GoogleSheetConector("TestDoc", "fake.json")
        data = [["A", "B"]]
        
        with pytest.raises(Exception, match="Error al insertar datos en Sheet1"):
            conn.spreadsheet_insert("TestDoc", "Sheet1", data)
