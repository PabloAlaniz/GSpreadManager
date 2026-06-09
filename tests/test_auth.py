"""Tests de las estrategias de autenticación, su factory y el adaptador con caché.

Aíslan la autenticación del conector: prueban ``build_auth_strategy`` (selección y
precedencia), cada estrategia y el caché de ``GspreadClientAdapter`` (este último con
un ``AuthStrategy`` falso, sin gspread, demostrando el desacople vía el puerto).
"""

from unittest.mock import Mock, patch

import pytest
from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.infrastructure.auth import (
    ADCAuth,
    CredentialsAuth,
    PreauthorizedClientAuth,
    ServiceAccountFileAuth,
    ServiceAccountInfoAuth,
    build_auth_strategy,
)
from gspreadmanager.infrastructure.gspread_adapters import GspreadSpreadsheet
from gspreadmanager.infrastructure.gspread_client import GspreadClientAdapter
from gspreadmanager.ports.auth import AuthStrategy


class TestBuildAuthStrategy:
    def test_selects_strategy_per_method(self):
        assert isinstance(build_auth_strategy(client=Mock()), PreauthorizedClientAuth)
        assert isinstance(build_auth_strategy(credentials=Mock()), CredentialsAuth)
        assert isinstance(
            build_auth_strategy(service_account_info={"a": 1}), ServiceAccountInfoAuth
        )
        assert isinstance(build_auth_strategy(json_google_file="x.json"), ServiceAccountFileAuth)
        assert isinstance(build_auth_strategy(use_adc=True), ADCAuth)

    def test_precedence_client_over_everything(self):
        strategy = build_auth_strategy(
            client=Mock(), credentials=Mock(), json_google_file="x.json", use_adc=True
        )
        assert isinstance(strategy, PreauthorizedClientAuth)

    def test_precedence_credentials_over_file(self):
        strategy = build_auth_strategy(credentials=Mock(), json_google_file="x.json")
        assert isinstance(strategy, CredentialsAuth)

    def test_no_credentials_raises(self):
        with pytest.raises(GSpreadManagerError, match="No se proporcionaron credenciales"):
            build_auth_strategy()

    def test_strategies_satisfy_port(self):
        strategy: AuthStrategy = build_auth_strategy(client=Mock())
        assert callable(strategy.authorize)


class TestStrategies:
    def test_preauthorized_client_returns_client_without_authorizing(self):
        client = Mock()
        with patch("gspreadmanager.infrastructure.auth.gspread") as mock_gs:
            assert PreauthorizedClientAuth(client).authorize() is client
        mock_gs.authorize.assert_not_called()

    def test_credentials_auth(self):
        creds = Mock()
        with patch("gspreadmanager.infrastructure.auth.gspread") as mock_gs:
            CredentialsAuth(creds).authorize()
        mock_gs.authorize.assert_called_once_with(creds)

    def test_service_account_info_auth(self):
        info = {"type": "service_account"}
        with (
            patch("gspreadmanager.infrastructure.auth.service_account.Credentials") as mock_creds,
            patch("gspreadmanager.infrastructure.auth.gspread") as mock_gs,
        ):
            ServiceAccountInfoAuth(info).authorize()
        mock_creds.from_service_account_info.assert_called_once()
        mock_gs.authorize.assert_called_once()

    def test_service_account_file_auth(self):
        with (
            patch("gspreadmanager.infrastructure.auth.service_account.Credentials") as mock_creds,
            patch("gspreadmanager.infrastructure.auth.gspread") as mock_gs,
        ):
            ServiceAccountFileAuth("creds.json").authorize()
        mock_creds.from_service_account_file.assert_called_once()
        mock_gs.authorize.assert_called_once()

    def test_adc_auth(self):
        with (
            patch("google.auth.default", return_value=(Mock(), "proj")) as mock_default,
            patch("gspreadmanager.infrastructure.auth.gspread") as mock_gs,
        ):
            ADCAuth().authorize()
        mock_default.assert_called_once()
        mock_gs.authorize.assert_called_once()


class TestGspreadClientAdapter:
    """El adaptador (ClientPort) se prueba con un AuthStrategy falso: sin gspread real."""

    def test_authorizes_lazily(self):
        auth = Mock()
        auth.authorize.return_value = Mock()
        adapter = GspreadClientAdapter(auth)

        # No autoriza hasta el primer uso
        auth.authorize.assert_not_called()

        adapter.open("Doc")
        auth.authorize.assert_called_once()

    def test_caches_spreadsheets_by_name(self):
        client = Mock()
        auth = Mock()
        auth.authorize.return_value = client
        adapter = GspreadClientAdapter(auth)

        adapter.open("Doc")
        adapter.open("Doc")

        # El documento se abre una vez y la autorización ocurre una vez (caché)
        client.open.assert_called_once_with("Doc")
        auth.authorize.assert_called_once()

    def test_opens_distinct_documents_independently(self):
        client = Mock()
        auth = Mock()
        auth.authorize.return_value = client
        adapter = GspreadClientAdapter(auth)

        adapter.open("A")
        adapter.open("B")

        assert client.open.call_count == 2

    def test_open_returns_spreadsheet_port_wrapping_raw(self):
        client = Mock()
        raw_ss = Mock()
        client.open.return_value = raw_ss
        auth = Mock()
        auth.authorize.return_value = client

        port = GspreadClientAdapter(auth).open("Doc")
        assert isinstance(port, GspreadSpreadsheet)
        assert port.raw is raw_ss


def test_client_adapter_open_by_key():
    client = Mock()
    raw_ss = Mock()
    client.open_by_key.return_value = raw_ss
    auth = Mock()
    auth.authorize.return_value = client

    adapter = GspreadClientAdapter(auth)
    port = adapter.open_by_key("KEY123")
    client.open_by_key.assert_called_once_with("KEY123")
    assert isinstance(port, GspreadSpreadsheet)
    # cacheado: segunda vez no reabre
    adapter.open_by_key("KEY123")
    client.open_by_key.assert_called_once()
