"""Adaptador del cliente de gspread: autentica (vía ``AuthStrategy``) y cachea.

Encapsula el caché de cliente y de documentos abiertos por nombre que antes vivía en
``GoogleSheetConector._get_client`` / ``_get_spreadsheet``. Cambiar de pestaña no
vuelve a autenticar ni a reabrir el documento.
"""

from __future__ import annotations

from typing import Any

from gspreadmanager.ports.auth import AuthStrategy


class GspreadClientAdapter:
    """Cliente de gspread con caché perezoso de autorización y de documentos."""

    def __init__(self, auth: AuthStrategy) -> None:
        """Recibe la estrategia de autenticación; no autentica hasta el primer uso."""
        self._auth = auth
        self._client: Any = None
        self._spreadsheets: dict[str, Any] = {}

    def client(self) -> Any:
        """Devuelve el cliente de gspread, autorizándolo (y cacheándolo) la primera vez."""
        if self._client is None:
            self._client = self._auth.authorize()
        return self._client

    def open(self, doc_name: str) -> Any:
        """Devuelve el documento abierto, cacheándolo por nombre para no reabrirlo."""
        if doc_name not in self._spreadsheets:
            self._spreadsheets[doc_name] = self.client().open(doc_name)
        return self._spreadsheets[doc_name]
