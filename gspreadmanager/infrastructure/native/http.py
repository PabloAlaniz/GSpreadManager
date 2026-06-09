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

    def delete(self, url: str, *, params: dict[str, Any] | None = None) -> HttpResponse:
        """DELETE."""
        ...


def build_authorized_session(credentials: Any) -> HttpSession:
    """Construye una ``AuthorizedSession`` de google-auth (import diferido de ``requests``)."""
    from google.auth.transport.requests import AuthorizedSession  # noqa: PLC0415

    return AuthorizedSession(credentials)
