"""Tests del Sprint 9 (v3.0a): cliente nativo async, retry y rate limiting cooperativos.

Espejo de los tests síncronos: una sesión HTTP async falsa valida las llamadas REST del
``AsyncSheetsApiClient``; el contrato de superficie verifica que las implementaciones
async cubren los puertos ``Async*Port``; el retry y el token bucket usan relojes/sleeps
inyectados (sin esperas reales).
"""

import asyncio
from typing import Any

import pytest
from gspreadmanager import (
    GSpreadManagerError,
    QuotaExceededError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
)
from gspreadmanager.domain.errors import ApiError, api_error_from_status
from gspreadmanager.infrastructure.async_rate_limit import AsyncTokenBucketRateLimiter
from gspreadmanager.infrastructure.async_retry import AsyncExponentialBackoffRetry
from gspreadmanager.infrastructure.native.async_client import (
    AsyncNativeSpreadsheet,
    AsyncNativeWorksheet,
    AsyncSheetsApiClient,
)
from gspreadmanager.ports.async_sheets import (
    AsyncClientPort,
    AsyncSpreadsheetPort,
    AsyncWorksheetPort,
)
from gspreadmanager.ports.rate_limit import AsyncRateLimiter
from gspreadmanager.ports.retry import AsyncRetryPolicy
from gspreadmanager.ports.sheets import ClientPort, SpreadsheetPort, WorksheetPort

from .test_native_spike import FakeResponse


def run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeAsyncSession:
    """Sesión HTTP async falsa: registra llamadas y devuelve respuestas en cola por verbo."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self._queue: dict[str, list[FakeResponse]] = {}

    def queue(self, method: str, data: Any, **kwargs: Any) -> None:
        self._queue.setdefault(method, []).append(FakeResponse(data, **kwargs))

    def _resp(self, method: str) -> FakeResponse:
        q = self._queue.get(method)
        return q.pop(0) if q else FakeResponse({})

    async def get(self, url: str, *, params: Any = None) -> FakeResponse:
        self.calls.append(("GET", url, params, None))
        return self._resp("get")

    async def post(self, url: str, *, params: Any = None, json: Any = None) -> FakeResponse:
        self.calls.append(("POST", url, params, json))
        return self._resp("post")

    async def put(self, url: str, *, params: Any = None, json: Any = None) -> FakeResponse:
        self.calls.append(("PUT", url, params, json))
        return self._resp("put")

    async def patch(self, url: str, *, params: Any = None, json: Any = None) -> FakeResponse:
        self.calls.append(("PATCH", url, params, json))
        return self._resp("patch")

    async def delete(self, url: str, *, params: Any = None) -> FakeResponse:
        self.calls.append(("DELETE", url, params, None))
        return self._resp("delete")


def _spreadsheet(session: FakeAsyncSession) -> AsyncNativeSpreadsheet:
    return AsyncNativeSpreadsheet(session, "doc", [("Hoja1", 7)])


def _worksheet(session: FakeAsyncSession) -> AsyncNativeWorksheet:
    return AsyncNativeWorksheet(_spreadsheet(session), session, "doc", "Hoja1", 7)


def _port_members(protocol: type) -> list[str]:
    return sorted(name for name in vars(protocol) if not name.startswith("_"))


ASYNC_CONTRACT_CASES = [
    (AsyncWorksheetPort, _worksheet(FakeAsyncSession())),
    (AsyncSpreadsheetPort, _spreadsheet(FakeAsyncSession())),
    (AsyncClientPort, AsyncSheetsApiClient(FakeAsyncSession())),
]


class TestAsyncPortContract:
    """Las implementaciones async exponen la superficie completa de cada puerto."""

    @pytest.mark.parametrize(
        ("port", "implementation"),
        ASYNC_CONTRACT_CASES,
        ids=[impl.__class__.__name__ for _, impl in ASYNC_CONTRACT_CASES],
    )
    def test_full_surface(self, port, implementation):
        missing = [m for m in _port_members(port) if not hasattr(implementation, m)]
        assert not missing, f"{implementation.__class__.__name__} no implementa: {missing}"

    def test_async_mirrors_sync_surface(self):
        assert _port_members(AsyncWorksheetPort) == _port_members(WorksheetPort)
        assert _port_members(AsyncSpreadsheetPort) == _port_members(SpreadsheetPort)
        assert _port_members(AsyncClientPort) == _port_members(ClientPort)

    def test_assignable_to_ports(self):
        ws: AsyncWorksheetPort = _worksheet(FakeAsyncSession())
        ss: AsyncSpreadsheetPort = _spreadsheet(FakeAsyncSession())
        client: AsyncClientPort = AsyncSheetsApiClient(FakeAsyncSession())
        assert ws is not None
        assert ss is not None
        assert client is not None


class TestAsyncClient:
    def test_open_by_name_searches_drive_and_caches(self):
        session = FakeAsyncSession()
        session.queue("get", {"files": [{"id": "k1", "name": "Doc"}]})
        session.queue("get", {"sheets": [{"properties": {"title": "Hoja1", "sheetId": 0}}]})
        client = AsyncSheetsApiClient(session)

        ss = run(client.open("Doc"))
        assert isinstance(ss, AsyncNativeSpreadsheet)
        run(client.open("Doc"))  # cacheado: sin nuevas llamadas
        assert len(session.calls) == 2

    def test_open_missing_document_raises(self):
        session = FakeAsyncSession()
        session.queue("get", {"files": []})
        with pytest.raises(SpreadsheetNotFoundError):
            run(AsyncSheetsApiClient(session).open("Nada"))

    def test_open_by_key_404(self):
        session = FakeAsyncSession()
        session.queue(
            "get",
            {"error": {"code": 404, "status": "NOT_FOUND", "message": "x"}},
            ok=False,
            status_code=404,
        )
        with pytest.raises(SpreadsheetNotFoundError):
            run(AsyncSheetsApiClient(session).open_by_key("nope"))

    def test_create_in_folder_patches_drive(self):
        session = FakeAsyncSession()
        session.queue("post", {"spreadsheetId": "nuevo"})
        run(AsyncSheetsApiClient(session).create("Doc", "carpeta"))
        assert session.calls[1][0] == "PATCH"
        assert session.calls[1][2]["addParents"] == "carpeta"

    def test_quota_error_is_domain_error(self):
        session = FakeAsyncSession()
        session.queue(
            "get",
            {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "q"}},
            ok=False,
            status_code=429,
        )
        with pytest.raises(QuotaExceededError):
            run(AsyncSheetsApiClient(session).open_by_key("k"))


class TestAsyncWorksheet:
    def test_get_all_values_pads_and_passes_render(self):
        session = FakeAsyncSession()
        session.queue("get", {"values": [["a", "b"], ["1"]]})
        ws = _worksheet(session)
        assert run(ws.get_all_values("FORMULA")) == [["a", "b"], ["1", ""]]
        assert session.calls[0][2] == {"valueRenderOption": "FORMULA"}

    def test_update_and_append(self):
        session = FakeAsyncSession()
        ws = _worksheet(session)
        run(ws.update_cell(2, 3, "x"))
        run(ws.append_rows([["a"]], "RAW"))
        assert session.calls[0][0] == "PUT"
        assert "C2" in session.calls[0][1]
        assert session.calls[1][0] == "POST"
        assert session.calls[1][1].endswith(":append")

    def test_copy_to(self):
        session = FakeAsyncSession()
        session.queue("post", {"sheetId": 9})
        result = run(_worksheet(session).copy_to("dest"))
        assert result == {"sheetId": 9}
        assert session.calls[0][1].endswith("/sheets/7:copyTo")

    def test_missing_worksheet_raises(self):
        with pytest.raises(WorksheetNotFoundError):
            _spreadsheet(FakeAsyncSession()).worksheet("Otra")


class TestAsyncRetry:
    def test_satisfies_port(self):
        policy: AsyncRetryPolicy = AsyncExponentialBackoffRetry()
        assert callable(policy.run)

    def test_retries_transient_then_succeeds(self, monkeypatch):
        sleeps: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        calls = [api_error_from_status(429, "q"), api_error_from_status(503, "s"), "ok"]

        async def operation() -> Any:
            result = calls.pop(0)
            if isinstance(result, ApiError):
                raise result
            return result

        policy = AsyncExponentialBackoffRetry(max_retries=2, backoff=1.0)
        assert run(policy.run(operation)) == "ok"
        assert sleeps == [1.0, 2.0]

    def test_non_retryable_propagates(self, monkeypatch):
        async def fake_sleep(seconds: float) -> None:  # pragma: no cover - no debe llamarse
            raise AssertionError("no debería dormir")

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        async def operation() -> Any:
            raise api_error_from_status(404, "nf")

        with pytest.raises(ApiError):
            run(AsyncExponentialBackoffRetry(max_retries=3).run(operation))


class TestAsyncRateLimiter:
    def test_satisfies_port(self):
        limiter: AsyncRateLimiter = AsyncTokenBucketRateLimiter(10)
        assert callable(limiter.acquire)

    def test_burst_then_waits(self):
        clock = {"now": 0.0}
        waits: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            waits.append(seconds)
            clock["now"] += seconds  # el tiempo avanza lo que se durmió

        limiter = AsyncTokenBucketRateLimiter(
            rate=2, capacity=2, clock=lambda: clock["now"], sleep=fake_sleep
        )

        async def scenario() -> None:
            await limiter.acquire()  # ráfaga 1
            await limiter.acquire()  # ráfaga 2 (bucket vacío)
            await limiter.acquire()  # debe esperar ~0.5s (rate=2/s)

        run(scenario())
        assert waits == [pytest.approx(0.5)]

    def test_invalid_rate_raises(self):
        with pytest.raises(GSpreadManagerError):
            AsyncTokenBucketRateLimiter(0)
