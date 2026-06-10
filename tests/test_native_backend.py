"""Tests del wiring del backend nativo: ``SheetManager(backend="native")``.

Verifican que el facade enchufa el ``SheetsApiClient`` detrás de los mismos puertos
(con sesión HTTP falsa, sin red), el caché de documentos abiertos, el mapeo de 404 a
``SpreadsheetNotFoundError`` y el timeout por petición.
"""

import sys
from typing import Any
from unittest.mock import Mock, patch

import pytest
from gspread.utils import ValueRenderOption
from gspreadmanager import (
    PermissionDeniedError,
    QuotaExceededError,
    SheetManager,
    SpreadsheetNotFoundError,
)
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.infrastructure.gspread_adapters import GspreadWorksheet
from gspreadmanager.infrastructure.gspread_client import GspreadClientAdapter
from gspreadmanager.infrastructure.native import SheetsApiClient, TimeoutHttpSession
from gspreadmanager.infrastructure.native.errors import (
    SheetsApiError,
    SheetsQuotaExceededError,
    build_sheets_api_error,
)
from gspreadmanager.infrastructure.native.http import DEFAULT_HTTP_TIMEOUT
from gspreadmanager.infrastructure.native.sheets_api_client import (
    NativeSpreadsheet,
    NativeWorksheet,
)

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
        session.patch("u", json={"d": 4})
        session.delete("u")

        inner.get.assert_called_once_with("u", params={"a": 1}, timeout=7.5)
        inner.post.assert_called_once_with("u", params=None, json={"b": 2}, timeout=7.5)
        inner.put.assert_called_once_with("u", params=None, json={"c": 3}, timeout=7.5)
        inner.patch.assert_called_once_with("u", params=None, json={"d": 4}, timeout=7.5)
        inner.delete.assert_called_once_with("u", params=None, timeout=7.5)


class TestAutoBackend:
    """``backend="auto"`` (default): gspread si está instalado, si no el nativo."""

    def test_auto_prefers_gspread_when_installed(self):
        # En el entorno de dev gspread está instalado.
        mgr = SheetManager("Doc", credentials=Mock())
        assert isinstance(mgr._client, GspreadClientAdapter)

    def test_auto_falls_back_to_native_without_gspread(self):
        with (
            patch("gspreadmanager.facade.importlib.util.find_spec", return_value=None),
            patch("gspreadmanager.facade.build_authorized_session", return_value=FakeSession()),
        ):
            mgr = SheetManager("Doc", credentials=Mock())
        assert isinstance(mgr._client, SheetsApiClient)

    def test_auto_with_preauthorized_client_uses_gspread(self):
        # Un `client` es un cliente de gspread: auto elige gspread aunque find_spec falle.
        with patch("gspreadmanager.facade.importlib.util.find_spec", return_value=None):
            mgr = SheetManager("Doc", client=Mock())
        assert isinstance(mgr._client, GspreadClientAdapter)

    def test_explicit_gspread_without_package_raises_helpful_error(self):
        with (
            patch.dict(sys.modules, {"gspreadmanager.infrastructure.gspread_client": None}),
            pytest.raises(GSpreadManagerError, match=r"GSpreadManager\[gspread\]"),
        ):
            SheetManager("Doc", backend="gspread", credentials=Mock())


class TestNativeErrorSubclasses:
    """429/403 del nativo heredan de los errores de dominio (mismo catch en ambos backends)."""

    def test_429_is_quota_exceeded(self):
        error = build_sheets_api_error(429, "RESOURCE_EXHAUSTED", "quota")
        assert isinstance(error, SheetsQuotaExceededError)
        assert isinstance(error, QuotaExceededError)
        assert error.status_code == 429

    def test_403_is_permission_denied(self):
        assert isinstance(build_sheets_api_error(403, "PERMISSION_DENIED", "x"), PermissionDeniedError)

    def test_other_codes_build_plain_sheets_api_error(self):
        error = build_sheets_api_error(500, "INTERNAL", "boom")
        assert type(error) is SheetsApiError

    def test_quota_error_raised_from_response(self):
        session = FakeSession()
        session.queue(
            "get",
            {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}},
            ok=False,
            status_code=429,
        )
        with pytest.raises(QuotaExceededError):
            SheetsApiClient(session).open_by_key("k")


class TestNativeCreateInFolder:
    def test_create_without_folder_does_not_patch(self):
        session = FakeSession()
        session.queue("post", {"spreadsheetId": "nuevo123"})
        SheetsApiClient(session).create("Doc", None)
        assert [c[0] for c in session.calls] == ["POST"]

    def test_create_with_folder_moves_via_drive_patch(self):
        session = FakeSession()
        session.queue("post", {"spreadsheetId": "nuevo123"})
        session.queue("patch", {"id": "nuevo123", "parents": ["carpeta9"]})

        SheetsApiClient(session).create("Doc", "carpeta9")

        method, url, params, _ = session.calls[1]
        assert method == "PATCH"
        assert url.endswith("/files/nuevo123")
        assert params["addParents"] == "carpeta9"


class TestNativeParityOperations:
    """Render options y copy_to en el cliente nativo (Sprint 4)."""

    def _worksheet(self, session: FakeSession) -> NativeWorksheet:
        ss = NativeSpreadsheet(session, "doc", [("Hoja1", 7)])
        return NativeWorksheet(ss, session, "doc", "Hoja1", 7)

    def test_get_all_values_passes_render_option(self):
        session = FakeSession()
        session.queue("get", {"values": [["=A1+1"]]})
        ws = self._worksheet(session)

        assert ws.get_all_values("FORMULA") == [["=A1+1"]]
        _, _, params, _ = session.calls[0]
        assert params == {"valueRenderOption": "FORMULA"}

    def test_get_all_values_without_render_sends_no_params(self):
        session = FakeSession()
        session.queue("get", {"values": [["1"]]})
        ws = self._worksheet(session)

        ws.get_all_values()
        assert session.calls[0][2] is None

    def test_copy_to_posts_to_copyto_endpoint(self):
        session = FakeSession()
        session.queue("post", {"sheetId": 99, "title": "Copia de Hoja1"})
        ws = self._worksheet(session)

        result = ws.copy_to("destino123")

        method, url, _, body = session.calls[0]
        assert method == "POST"
        assert url.endswith("/doc/sheets/7:copyTo")
        assert body == {"destinationSpreadsheetId": "destino123"}
        assert result["sheetId"] == 99


class TestGspreadParityOperations:
    def test_get_all_values_maps_render_option_enum(self):
        raw = Mock()
        GspreadWorksheet(raw).get_all_values("UNFORMATTED_VALUE")
        raw.get_all_values.assert_called_once_with(
            value_render_option=ValueRenderOption.unformatted
        )

    def test_get_all_values_without_render_uses_default(self):
        raw = Mock()
        GspreadWorksheet(raw).get_all_values()
        raw.get_all_values.assert_called_once_with()

    def test_copy_to_delegates(self):
        raw = Mock()
        GspreadWorksheet(raw).copy_to("destino")
        raw.copy_to.assert_called_once_with("destino")
