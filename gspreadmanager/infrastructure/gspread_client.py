"""Adaptador del cliente de gspread: autentica (vía ``AuthStrategy``), cachea y opera Drive.

Implementa ``ClientPort``: encapsula el caché de cliente y de documentos abiertos por
nombre (pedir otra pestaña no vuelve a autenticar ni a reabrir el documento) y expone las
operaciones a nivel Drive. ``open`` devuelve un ``SpreadsheetPort`` (adaptador).
"""

from __future__ import annotations

import logging
from typing import Any

from gspreadmanager.ports.auth import AuthStrategy
from gspreadmanager.ports.sheets import SpreadsheetPort

from .gspread_adapters import GspreadSpreadsheet
from .gspread_errors import translates_gspread_errors

logger = logging.getLogger(__name__)


@translates_gspread_errors
class GspreadClientAdapter:
    """Cliente de gspread con caché perezoso de autorización y de documentos."""

    def __init__(self, auth: AuthStrategy) -> None:
        """Recibe la estrategia de autenticación; no autentica hasta el primer uso."""
        self._auth = auth
        self._client: Any = None
        self._spreadsheets: dict[str, Any] = {}

    def _raw_client(self) -> Any:
        """Devuelve el cliente de gspread, autorizándolo (y cacheándolo) la primera vez."""
        if self._client is None:
            logger.debug("Autenticando cliente de gspread.")
            self._client = self._auth.authorize()
        return self._client

    def open(self, doc_name: str) -> SpreadsheetPort:
        """Devuelve el documento (adaptado), cacheándolo por nombre para no reabrirlo."""
        if doc_name not in self._spreadsheets:
            logger.debug("Abriendo documento por nombre: %r.", doc_name)
            self._spreadsheets[doc_name] = self._raw_client().open(doc_name)
        return GspreadSpreadsheet(self._spreadsheets[doc_name])

    def open_by_key(self, key: str) -> SpreadsheetPort:
        """Devuelve el documento por su key (id de Drive), cacheándolo."""
        if key not in self._spreadsheets:
            logger.debug("Abriendo documento por key: %r.", key)
            self._spreadsheets[key] = self._raw_client().open_by_key(key)
        return GspreadSpreadsheet(self._spreadsheets[key])

    def create(self, title: str, folder_id: str | None) -> Any:
        """Crea un nuevo documento."""
        return self._raw_client().create(title, folder_id=folder_id)

    def del_spreadsheet(self, file_id: str) -> None:
        """Elimina un documento por su ID."""
        self._raw_client().del_spreadsheet(file_id)

    def copy(
        self, file_id: str, title: str | None, copy_permissions: bool, folder_id: str | None
    ) -> Any:
        """Copia un documento."""
        return self._raw_client().copy(
            file_id, title=title, copy_permissions=copy_permissions, folder_id=folder_id
        )

    def list_spreadsheet_files(
        self, title: str | None, folder_id: str | None
    ) -> list[dict[str, Any]]:
        """Lista documentos accesibles."""
        result: list[dict[str, Any]] = self._raw_client().list_spreadsheet_files(
            title=title, folder_id=folder_id
        )
        return result
