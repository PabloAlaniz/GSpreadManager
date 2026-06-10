"""Tests de la política de reintentos (``infrastructure.retry``).

Prueban ``ExponentialBackoffRetry.run`` de forma aislada. Desde la v2.2 la política opera
sobre los ``ApiError`` del dominio (los adaptadores traducen antes), así que no conoce
gspread ni ningún transporte concreto.
"""

from unittest.mock import patch

import pytest
from gspreadmanager.domain.errors import (
    ApiError,
    QuotaExceededError,
    api_error_from_status,
)
from gspreadmanager.infrastructure.native.errors import SheetsApiError
from gspreadmanager.infrastructure.retry import RETRYABLE_STATUS, ExponentialBackoffRetry
from gspreadmanager.ports.retry import RetryPolicy


def make_api_error(status_code: int) -> ApiError:
    """Construye el ApiError de dominio para el código de estado HTTP dado."""
    return api_error_from_status(status_code, "boom")


def test_exponential_backoff_satisfies_retry_policy_port():
    # Conformidad estructural con el puerto (verificado por mypy y en runtime).
    policy: RetryPolicy = ExponentialBackoffRetry()
    assert callable(policy.run)


def test_success_on_first_try_does_not_sleep():
    policy = ExponentialBackoffRetry(max_retries=3, backoff=0)
    with patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep:
        assert policy.run(lambda: 42) == 42
    mock_sleep.assert_not_called()


def test_retries_then_succeeds():
    calls = [make_api_error(429), make_api_error(503), "ok"]

    def operation():
        result = calls.pop(0)
        if isinstance(result, ApiError):
            raise result
        return result

    policy = ExponentialBackoffRetry(max_retries=2, backoff=0)
    with patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep:
        assert policy.run(operation) == "ok"
    assert mock_sleep.call_count == 2


def test_exhausted_retries_raises():
    policy = ExponentialBackoffRetry(max_retries=1, backoff=0)

    def operation():
        raise make_api_error(429)

    with (
        patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep,
        pytest.raises(QuotaExceededError),
    ):
        policy.run(operation)
    assert mock_sleep.call_count == 1


@pytest.mark.parametrize("status", [403, 404, 400])
def test_non_retryable_status_propagates_immediately(status):
    policy = ExponentialBackoffRetry(max_retries=5, backoff=0)

    def operation():
        raise make_api_error(status)

    with (
        patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep,
        pytest.raises(ApiError),
    ):
        policy.run(operation)
    mock_sleep.assert_not_called()


def test_error_without_status_code_propagates_immediately():
    policy = ExponentialBackoffRetry(max_retries=5, backoff=0)

    def operation():
        raise ApiError("sin código")

    with (
        patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep,
        pytest.raises(ApiError),
    ):
        policy.run(operation)
    mock_sleep.assert_not_called()


def test_backoff_grows_exponentially():
    policy = ExponentialBackoffRetry(max_retries=3, backoff=1.5)
    attempts = [make_api_error(500)] * 3 + ["done"]

    def operation():
        result = attempts.pop(0)
        if isinstance(result, ApiError):
            raise result
        return result

    with patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep:
        assert policy.run(operation) == "done"
    # backoff * 2**intento => 1.5, 3.0, 6.0
    assert [c.args[0] for c in mock_sleep.call_args_list] == [1.5, 3.0, 6.0]


def test_retryable_status_set():
    assert {429, 500, 503} == RETRYABLE_STATUS


def test_native_sheets_api_error_is_retryable():
    # El error del cliente nativo entra por la misma jerarquía (ApiError del dominio).
    calls = [SheetsApiError(429, "RESOURCE_EXHAUSTED", "quota"), "ok"]

    def operation():
        result = calls.pop(0)
        if isinstance(result, ApiError):
            raise result
        return result

    policy = ExponentialBackoffRetry(max_retries=1, backoff=0)
    with patch("gspreadmanager.infrastructure.retry.time.sleep"):
        assert policy.run(operation) == "ok"
