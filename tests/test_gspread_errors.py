"""Tests de la traducción de excepciones de gspread a errores del dominio.

Verifican el contrato de errores del Sprint 1 (v2.2): ninguna excepción de gspread escapa
de los adaptadores; el usuario y la política de reintentos solo ven la jerarquía propia
(``GSpreadManagerError`` y subclases).
"""

from unittest.mock import Mock

import pytest
from gspread.exceptions import APIError, GSpreadException, SpreadsheetNotFound, WorksheetNotFound
from gspreadmanager.domain.errors import (
    ApiError,
    GSpreadManagerError,
    PermissionDeniedError,
    QuotaExceededError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
    api_error_from_status,
)
from gspreadmanager.infrastructure.gspread_adapters import GspreadSpreadsheet, GspreadWorksheet
from gspreadmanager.infrastructure.gspread_client import GspreadClientAdapter
from gspreadmanager.infrastructure.gspread_errors import translate_gspread_error


def make_gspread_api_error(status_code: int) -> APIError:
    """Construye un APIError de gspread con el código de estado HTTP dado."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {
        "error": {"code": status_code, "message": "boom", "status": "ERROR"}
    }
    response.text = "boom"
    return APIError(response)


class TestTranslateGspreadError:
    def test_spreadsheet_not_found(self):
        translated = translate_gspread_error(SpreadsheetNotFound("no está"))
        assert isinstance(translated, SpreadsheetNotFoundError)

    def test_worksheet_not_found_includes_title(self):
        translated = translate_gspread_error(WorksheetNotFound("Hoja99"))
        assert isinstance(translated, WorksheetNotFoundError)
        assert "Hoja99" in str(translated)

    def test_api_error_429_is_quota(self):
        translated = translate_gspread_error(make_gspread_api_error(429))
        assert isinstance(translated, QuotaExceededError)
        assert translated.status_code == 429

    def test_api_error_403_is_permission_denied(self):
        translated = translate_gspread_error(make_gspread_api_error(403))
        assert isinstance(translated, PermissionDeniedError)

    def test_api_error_other_status_keeps_code(self):
        translated = translate_gspread_error(make_gspread_api_error(500))
        assert type(translated) is ApiError
        assert translated.status_code == 500

    def test_unknown_gspread_exception_maps_to_base_error(self):
        translated = translate_gspread_error(GSpreadException("raro"))
        assert type(translated) is GSpreadManagerError


class TestApiErrorFactory:
    def test_unknown_status_builds_plain_api_error(self):
        error = api_error_from_status(None, "sin código")
        assert type(error) is ApiError
        assert error.status_code is None

    def test_quota_and_permission_are_api_errors(self):
        assert isinstance(api_error_from_status(429, "x"), ApiError)
        assert isinstance(api_error_from_status(403, "x"), ApiError)


class TestAdaptersTranslate:
    def test_worksheet_adapter_translates_api_error(self):
        raw = Mock()
        raw.get_all_values.side_effect = make_gspread_api_error(429)
        with pytest.raises(QuotaExceededError):
            GspreadWorksheet(raw).get_all_values()

    def test_worksheet_adapter_translates_in_properties(self):
        raw = Mock()
        type(raw).title = property(Mock(side_effect=make_gspread_api_error(500)))
        with pytest.raises(ApiError):
            _ = GspreadWorksheet(raw).title

    def test_spreadsheet_adapter_translates_worksheet_not_found(self):
        raw = Mock()
        raw.worksheet.side_effect = WorksheetNotFound("Hoja1")
        with pytest.raises(WorksheetNotFoundError):
            GspreadSpreadsheet(raw).worksheet("Hoja1")

    def test_client_adapter_translates_spreadsheet_not_found(self):
        auth = Mock()
        auth.authorize.return_value.open.side_effect = SpreadsheetNotFound("Doc")
        with pytest.raises(SpreadsheetNotFoundError):
            GspreadClientAdapter(auth).open("Doc")

    def test_translated_errors_chain_the_original(self):
        raw = Mock()
        original = make_gspread_api_error(503)
        raw.clear.side_effect = original
        with pytest.raises(ApiError) as exc_info:
            GspreadWorksheet(raw).clear()
        assert exc_info.value.__cause__ is original

    def test_successful_calls_pass_through(self):
        raw = Mock()
        raw.get_all_values.return_value = [["a"]]
        assert GspreadWorksheet(raw).get_all_values() == [["a"]]
