"""Estrategias de autenticación concretas (una por método) y su factory.

Cada estrategia sabe construir un cliente de gspread a partir de un método de
credenciales; ``build_auth_strategy`` selecciona la apropiada según los parámetros.
Es de los pocos módulos (con ``facade`` y el resto de ``infrastructure``) que conocen
``gspread`` y ``google-auth``.
"""

from __future__ import annotations

from typing import Any

import gspread
from google.oauth2 import service_account

from gspreadmanager.domain.errors import GSpreadManagerError
from gspreadmanager.ports.auth import AuthStrategy

# Scopes requeridos para Sheets + Drive.
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class PreauthorizedClientAuth:
    """Estrategia trivial: ya se dispone de un cliente de gspread autorizado."""

    def __init__(self, client: Any) -> None:
        """Guarda el cliente ya autorizado."""
        self._client = client

    def authorize(self) -> Any:
        """Devuelve el cliente provisto sin volver a autenticar."""
        return self._client


class CredentialsAuth:
    """Autoriza con un objeto de credenciales de google-auth ya construido."""

    def __init__(self, credentials: Any) -> None:
        """Guarda las credenciales."""
        self._credentials = credentials

    def authorize(self) -> Any:
        """Autoriza un cliente de gspread con las credenciales provistas."""
        return gspread.authorize(self._credentials)


class ServiceAccountInfoAuth:
    """Autoriza con las credenciales de un service account dadas como diccionario."""

    def __init__(self, info: dict[str, Any]) -> None:
        """Guarda el diccionario de credenciales."""
        self._info = info

    def authorize(self) -> Any:
        """Construye credenciales desde el diccionario y autoriza el cliente."""
        creds = service_account.Credentials.from_service_account_info(self._info, scopes=SCOPES)
        return gspread.authorize(creds)


class ServiceAccountFileAuth:
    """Autoriza con un archivo JSON de service account."""

    def __init__(self, path: str) -> None:
        """Guarda la ruta al archivo de credenciales."""
        self._path = path

    def authorize(self) -> Any:
        """Construye credenciales desde el archivo y autoriza el cliente."""
        creds = service_account.Credentials.from_service_account_file(self._path, scopes=SCOPES)
        return gspread.authorize(creds)


class ADCAuth:
    """Autoriza usando Application Default Credentials (ADC)."""

    def authorize(self) -> Any:
        """Resuelve las ADC del entorno y autoriza el cliente."""
        import google.auth  # noqa: PLC0415  (carga diferida: solo si se usa ADC)

        creds, _ = google.auth.default(scopes=SCOPES)
        return gspread.authorize(creds)


def build_auth_strategy(
    *,
    credentials: Any = None,
    service_account_info: dict[str, Any] | None = None,
    json_google_file: str | None = None,
    client: Any = None,
    use_adc: bool = False,
) -> AuthStrategy:
    """Selecciona la estrategia de autenticación según el método provisto.

    Precedencia (se usa el primero presente): ``client`` ya autorizado, ``credentials``,
    ``service_account_info``, ``json_google_file`` y ``use_adc``. Lanza
    ``GSpreadManagerError`` si no se proporciona ninguno.
    """
    if client is not None:
        return PreauthorizedClientAuth(client)
    if credentials is not None:
        return CredentialsAuth(credentials)
    if service_account_info is not None:
        return ServiceAccountInfoAuth(service_account_info)
    if json_google_file is not None:
        return ServiceAccountFileAuth(json_google_file)
    if use_adc:
        return ADCAuth()
    raise GSpreadManagerError(
        "No se proporcionaron credenciales. Pasá uno de: json_google_file, "
        "credentials, service_account_info, client o use_adc=True."
    )
