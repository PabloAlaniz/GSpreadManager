"""Sesión HTTP async para el cliente nativo (httpx como extra opcional).

Define el puerto ``AsyncHttpSession`` (espejo de ``HttpSession`` con corrutinas) y una
sesión autorizada sobre ``httpx.AsyncClient``: agrega el token Bearer de google-auth a
cada petición, refrescándolo fuera del event loop (``asyncio.to_thread``) cuando expira.
En tests se inyecta una sesión falsa, igual que en el cliente síncrono.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from gspreadmanager.domain.errors import GSpreadManagerError

from .http import DEFAULT_HTTP_TIMEOUT, HttpResponse

HTTPX_MISSING_MESSAGE = (
    "El cliente nativo async requiere el paquete 'httpx' (es un extra opcional). "
    'Instalalo con pip install "GSpreadManager[async]".'
)


class AsyncHttpSession(Protocol):
    """Sesión HTTP async mínima que necesita el cliente nativo."""

    async def get(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """GET."""
        ...

    async def post(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """POST con cuerpo JSON."""
        ...

    async def put(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PUT con cuerpo JSON."""
        ...

    async def patch(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PATCH con cuerpo JSON."""
        ...

    async def delete(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """DELETE."""
        ...


class _HttpxResponse:
    """Adapta ``httpx.Response`` al shape de ``HttpResponse`` (expone ``ok``)."""

    def __init__(self, response: Any) -> None:
        self._response = response

    @property
    def ok(self) -> bool:
        """True si el status HTTP es exitoso (< 400)."""
        return bool(self._response.is_success)

    @property
    def status_code(self) -> int:
        """Código de estado HTTP."""
        return int(self._response.status_code)

    @property
    def text(self) -> str:
        """Cuerpo como texto."""
        return str(self._response.text)

    @property
    def content(self) -> bytes:
        """Cuerpo como bytes."""
        return bytes(self._response.content)

    def json(self) -> Any:
        """Cuerpo deserializado como JSON."""
        return self._response.json()


class AuthorizedAsyncSession:
    """``AsyncHttpSession`` sobre ``httpx.AsyncClient`` con token Bearer de google-auth.

    El refresh de credenciales de google-auth es síncrono (usa ``requests``): se ejecuta
    en un thread (``asyncio.to_thread``) para no bloquear el event loop. Usable como
    async context manager (``async with``) para cerrar el cliente httpx.
    """

    def __init__(
        self, credentials: Any, client: Any, timeout: float | None = DEFAULT_HTTP_TIMEOUT
    ) -> None:
        """Recibe credenciales de google-auth y un ``httpx.AsyncClient`` ya construido."""
        self._credentials = credentials
        self._client = client
        self._timeout = timeout

    async def __aenter__(self) -> AuthorizedAsyncSession:
        """Entra al contexto (el cliente httpx ya está abierto)."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Cierra el cliente httpx subyacente."""
        await self._client.aclose()

    async def _headers(self) -> dict[str, str]:
        if not getattr(self._credentials, "valid", False):
            from google.auth.transport.requests import Request  # noqa: PLC0415

            await asyncio.to_thread(self._credentials.refresh, Request())
        return {"Authorization": f"Bearer {self._credentials.token}"}

    async def _request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        response = await self._client.request(
            method, url, headers=await self._headers(), timeout=self._timeout, **kwargs
        )
        return _HttpxResponse(response)

    async def get(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """GET autorizado."""
        return await self._request("GET", url, params=params)

    async def post(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """POST autorizado con cuerpo JSON."""
        return await self._request("POST", url, params=params, json=json)

    async def put(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PUT autorizado con cuerpo JSON."""
        return await self._request("PUT", url, params=params, json=json)

    async def patch(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PATCH autorizado con cuerpo JSON."""
        return await self._request("PATCH", url, params=params, json=json)

    async def delete(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """DELETE autorizado."""
        return await self._request("DELETE", url, params=params)


def build_async_session(
    credentials: Any, timeout: float | None = DEFAULT_HTTP_TIMEOUT
) -> AuthorizedAsyncSession:
    """Construye la sesión async autorizada (import diferido de httpx, extra ``[async]``)."""
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:
        raise GSpreadManagerError(HTTPX_MISSING_MESSAGE) from exc
    return AuthorizedAsyncSession(credentials, httpx.AsyncClient(), timeout)
