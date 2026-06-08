"""Tests de la política de reintentos (``infrastructure.retry``) sin pasar por el conector.

Prueban ``ExponentialBackoffRetry.run`` y ``_status_code`` de forma aislada, demostrando
el desacople: la política no depende de ``GoogleSheetConector`` ni de ``self``.
"""

from unittest.mock import Mock, patch

import pytest
from gspread.exceptions import APIError
from gspreadmanager.infrastructure.retry import (
    RETRYABLE_STATUS,
    ExponentialBackoffRetry,
    _status_code,
)
from gspreadmanager.ports.retry import RetryPolicy


def make_api_error(status_code: int) -> APIError:
    """Construye un APIError de gspread con el código de estado HTTP dado."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {
        "error": {"code": status_code, "message": "boom", "status": "ERROR"}
    }
    response.text = "boom"
    return APIError(response)


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
        if isinstance(result, APIError):
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
        pytest.raises(APIError),
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
        pytest.raises(APIError),
    ):
        policy.run(operation)
    mock_sleep.assert_not_called()


def test_backoff_grows_exponentially():
    policy = ExponentialBackoffRetry(max_retries=3, backoff=1.5)
    attempts = [make_api_error(500)] * 3 + ["done"]

    def operation():
        result = attempts.pop(0)
        if isinstance(result, APIError):
            raise result
        return result

    with patch("gspreadmanager.infrastructure.retry.time.sleep") as mock_sleep:
        assert policy.run(operation) == "done"
    # backoff * 2**intento => 1.5, 3.0, 6.0
    assert [c.args[0] for c in mock_sleep.call_args_list] == [1.5, 3.0, 6.0]


class TestStatusCode:
    def test_reads_response_status_code(self):
        assert _status_code(make_api_error(429)) == 429

    def test_falls_back_to_code_attribute(self):
        err = Mock(spec=APIError)
        err.response = None
        err.code = 503
        assert _status_code(err) == 503

    def test_returns_none_when_unknown(self):
        err = Mock(spec=APIError)
        err.response = None
        err.code = None
        assert _status_code(err) is None

    def test_retryable_status_set(self):
        assert {429, 500, 503} == RETRYABLE_STATUS
