"""Tests del wiring del backend nativo: ``SheetManager(backend="native")``.

Verifican que el facade enchufa el ``SheetsApiClient`` detrás de los mismos puertos
(con sesión HTTP falsa, sin red), el caché de documentos abiertos, el mapeo de 404 a
``SpreadsheetNotFoundError`` y el timeout por petición.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from gspreadmanager import SheetManager, SpreadsheetNotFoundError
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.infrastructure.gspread_client import GspreadClientAdapter
from gspreadmanager.infrastructure.native import SheetsApiClient, TimeoutHttpSession
from gspreadmanager.infrastructure.native.errors import SheetsApiError
from gspreadmanager.infrastructure.native.http import DEFAULT_HTTP_TIMEOUT

from .test_native_spike import FakeSession

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"


def queue_open(session: FakeSession, key: str = "key123") -> None:
    """Encola las respuestas de abrir 'Doc' por nombre: búsqueda en Drive + metadata."""
    session.queue("get", {"files": [{"id": key, "name": "Doc"}]})
    session.queue(
        "get", {"sheets": [{"properties": {"title": "Hoja1", "sheetId": 0}}]}
    )


def native_manager(session: FakeSession, **kwargs: Any) -> SheetManager:
    """Construye un SheetManager con backend nativo y la sesión falsa inyectada."""
    with patch(
        "gspreadmanager.facade.build_authorized_session", return_value=session
    ) as mock_build:
        mgr = SheetManager("Doc", backend="native", credentials=Mock(), **kwargs)
    assert mock_build.call_count == 1
    return mgr


class TestNativeBackendWiring:
    def test_backend_native_uses_sheets_api_client(self):
        mgr = native_manager(FakeSession())
        assert isinstance(mgr._client, SheetsApiClient)

    def test_read_flows_through_rest(self):
        session = FakeSession()
        queue_open(session)
        session.queue("get", {"values": [["nombre"], ["Ana"]]})

        mgr = native_manager(session)
        assert mgr.worksheet("Hoja1").read() == [["nombre"], ["Ana"]]

        methods_and_urls = [(c[0], c[1]) for c in session.calls]
        assert methods_and_urls[0][0] == "GET"
        assert methods_and_urls[0][1] == DRIVE_FILES  # búsqueda por nombre
        assert "key123" in methods_and_urls[1][1]  # metadata del documento
        assert "values" in methods_and_urls[2][1]  # lectura de valores

    def test_open_is_cached_per_document(self):
        session = FakeSession()
        queue_open(session)
        session.queue("get", {"values": [["a"]]})
        session.queue("get", {"values": [["a"]]})

        mgr = native_manager(session)
        mgr.worksheet("Hoja1").read()
        mgr.worksheet("Hoja1").read()

        drive_searches = [c for c in session.calls if c[1] == DRIVE_FILES]
        assert len(drive_searches) == 1

    def test_default_timeout_applied_to_session(self):
        creds = Mock()
        with patch(
            "gspreadmanager.facade.build_authorized_session"
        ) as mock_build:
            SheetManager("Doc", backend="native", credentials=creds)
        mock_build.assert_called_once_with(creds, timeout=DEFAULT_HTTP_TIMEOUT)

    def test_custom_timeout_applied_to_session(self):
        with patch("gspreadmanager.facade.build_authorized_session") as mock_build:
            SheetManager("Doc", backend="native", credentials=Mock(), http_timeout=5.0)
        assert mock_build.call_args.kwargs["timeout"] == 5.0

    def test_unknown_backend_raises(self):
        with pytest.raises(GSpreadManagerError, match="Backend desconocido"):
            SheetManager("Doc", backend="rest", credentials=Mock())

    def test_preauthorized_gspread_client_incompatible_with_native(self):
        with pytest.raises(GSpreadManagerError, match="no aplica"):
            SheetManager("Doc", backend="native", client=Mock())

    def test_native_backend_requires_credentials(self):
        with pytest.raises(GSpreadManagerError, match="No se proporcionaron credenciales"):
            SheetManager("Doc", backend="native")

    def test_gspread_remains_default_backend(self):
        mgr = SheetManager("Doc", credentials=Mock())
        assert isinstance(mgr._client, GspreadClientAdapter)


class TestNativeClientErrors:
    def test_open_by_key_404_raises_spreadsheet_not_found(self):
        session = FakeSession()
        session.queue(
            "get",
            {"error": {"code": 404, "status": "NOT_FOUND", "message": "Requested entity"}},
            ok=False,
            status_code=404,
        )
        with pytest.raises(SpreadsheetNotFoundError, match="key 'nope'"):
            SheetsApiClient(session).open_by_key("nope")

    def test_open_by_key_other_error_propagates_as_api_error(self):
        session = FakeSession()
        session.queue(
            "get",
            {"error": {"code": 500, "status": "INTERNAL", "message": "boom"}},
            ok=False,
            status_code=500,
        )
        with pytest.raises(SheetsApiError):
            SheetsApiClient(session).open_by_key("k")


class TestTimeoutHttpSession:
    def test_applies_timeout_to_every_verb(self):
        inner = Mock()
        session = TimeoutHttpSession(inner, 7.5)

        session.get("u", params={"a": 1})
        session.post("u", json={"b": 2})
        session.put("u", json={"c": 3})
        session.delete("u")

        inner.get.assert_called_once_with("u", params={"a": 1}, timeout=7.5)
        inner.post.assert_called_once_with("u", params=None, json={"b": 2}, timeout=7.5)
        inner.put.assert_called_once_with("u", params=None, json={"c": 3}, timeout=7.5)
        inner.delete.assert_called_once_with("u", params=None, timeout=7.5)
