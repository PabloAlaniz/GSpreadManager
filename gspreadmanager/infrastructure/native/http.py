"""Sesión HTTP para el cliente nativo.

Define un puerto mínimo ``HttpSession`` (lo que el cliente nativo necesita de un cliente
HTTP) y una factory que construye una ``AuthorizedSession`` de google-auth a partir de
credenciales. El cliente nativo depende del puerto, no de ``requests``, así que en tests se
inyecta una sesión falsa.
"""

from __future__ import annotations

from typing import Any, Protocol


class HttpResponse(Protocol):
    """Respuesta HTTP mínima (la satisface ``requests.Response``)."""

    @property
    def ok(self) -> bool:
        """True si el status HTTP es exitoso (< 400)."""
        ...

    @property
    def status_code(self) -> int:
        """Código de estado HTTP."""
        ...

    @property
    def text(self) -> str:
        """Cuerpo de la respuesta como texto."""
        ...

    @property
    def content(self) -> bytes:
        """Cuerpo de la respuesta como bytes (para descargas/export)."""
        ...

    def json(self) -> Any:
        """Cuerpo deserializado como JSON."""
        ...


class HttpSession(Protocol):
    """Sesión HTTP mínima (la satisface ``google.auth.transport.requests.AuthorizedSession``)."""

    def get(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """GET."""
        ...

    def post(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """POST con cuerpo JSON."""
        ...

    def put(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PUT con cuerpo JSON."""
        ...

    def patch(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PATCH con cuerpo JSON (Drive ``files.update``)."""
        ...

    def delete(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """DELETE."""
        ...


# Timeout por defecto (segundos) para cada petición del backend nativo.
DEFAULT_HTTP_TIMEOUT = 60.0


class TimeoutHttpSession:
    """``HttpSession`` que aplica un timeout por defecto a cada petición de la sesión envuelta.

    La ``AuthorizedSession`` de google-auth (como ``requests``) no aplica timeout salvo que
    se pase por llamada; este wrapper lo fija una sola vez para todo el backend nativo.
    """

    def __init__(self, inner: Any, timeout: float) -> None:
        """Envuelve ``inner`` (una sesión estilo requests) con el ``timeout`` en segundos."""
        self._inner = inner
        self._timeout = timeout

    def get(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """GET con timeout."""
        return self._inner.get(url, params=params, timeout=self._timeout)

    def post(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """POST con timeout."""
        return self._inner.post(url, params=params, json=json, timeout=self._timeout)

    def put(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PUT con timeout."""
        return self._inner.put(url, params=params, json=json, timeout=self._timeout)

    def patch(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """PATCH con timeout."""
        return self._inner.patch(url, params=params, json=json, timeout=self._timeout)

    def delete(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """DELETE con timeout."""
        return self._inner.delete(url, params=params, timeout=self._timeout)


def build_authorized_session(
    credentials: Any, timeout: float | None = DEFAULT_HTTP_TIMEOUT
) -> HttpSession:
    """Construye una ``AuthorizedSession`` de google-auth (import diferido de ``requests``).

    Con ``timeout`` (por defecto 60s) cada petición lo aplica; ``None`` lo desactiva.
    """
    from google.auth.transport.requests import AuthorizedSession  # noqa: PLC0415

    session = AuthorizedSession(credentials)
    if timeout is None:
        return session
    return TimeoutHttpSession(session, timeout)
