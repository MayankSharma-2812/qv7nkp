"""
qv7nkp/backend/tests/clients/test_elexon.py

Comprehensive tests for ElexonClient covering all 12 required test conditions:
1. Successful FUELHH response.
2. Successful WINDFOR response.
3. Correct endpoint paths and query parameters.
4. Multiple records and timestamp parsing (timezone-aware UTC).
5. Empty response arrays.
6. Missing or null generation.
7. Malformed JSON and unexpected response shapes.
8. HTTP 429 followed by success.
9. HTTP 5xx followed by success.
10. Non-retryable HTTP 4xx.
11. Exhausted retries and timeout/connection failures.
12. Repeated calls without unintended client/resource leaks.
"""

from datetime import date, datetime, timezone
import httpx
import pytest
import respx

from app.clients.elexon import (
    DEFAULT_BASE_URL,
    ElexonClient,
    ElexonClientError,
    ElexonConnectionError,
    ElexonHttpError,
    ElexonResponseValidationError,
    ElexonTimeoutError,
)
from app.schemas.elexon import FuelHHRecord, WindforRecord


@pytest.fixture
def mock_elexon():
    with respx.mock(base_url=DEFAULT_BASE_URL, assert_all_called=False) as respx_mock:
        yield respx_mock


@pytest.fixture
def fast_client():
    """Client with near-instant retry backoff for deterministic, fast tests."""
    return ElexonClient(
        base_url=DEFAULT_BASE_URL,
        max_retries=2,
        base_delay=0.001,
        max_delay=0.01,
        jitter=False,
    )


# 1. Successful FUELHH response
@pytest.mark.asyncio
async def test_fetch_fuelhh_success(mock_elexon, fast_client):
    mock_data = [
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-10T12:00:00Z",
            "startTime": "2026-01-10T11:30:00Z",
            "settlementDate": "2026-01-10",
            "settlementPeriod": 24,
            "fuelType": "WIND",
            "generation": 7520.5,
        }
    ]
    route = mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    records = await fast_client.fetch_fuelhh(
        settlement_date_from=date(2026, 1, 10),
        settlement_date_to=date(2026, 1, 10),
        fuel_type="WIND",
    )

    assert route.called
    assert len(records) == 1
    assert isinstance(records[0], FuelHHRecord)
    assert records[0].dataset == "FUELHH"
    assert records[0].settlementDate == "2026-01-10"
    assert records[0].settlementPeriod == 24
    assert records[0].fuelType == "WIND"
    assert records[0].generation == 7520.5
    assert records[0].startTime == datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc)
    assert records[0].publishTime == datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    await fast_client.aclose()


# 2. Successful WINDFOR response
@pytest.mark.asyncio
async def test_fetch_windfor_success(mock_elexon, fast_client):
    mock_data = [
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-09T09:30:00Z",
            "startTime": "2026-01-10T14:00:00Z",
            "generation": 11400.0,
        }
    ]
    route = mock_elexon.get("/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    from_dt = datetime(2026, 1, 9, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 1, 9, 23, 59, 59, tzinfo=timezone.utc)

    records = await fast_client.fetch_windfor(
        publish_datetime_from=from_dt,
        publish_datetime_to=to_dt,
    )

    assert route.called
    assert len(records) == 1
    assert isinstance(records[0], WindforRecord)
    assert records[0].dataset == "WINDFOR"
    assert records[0].generation == 11400.0
    assert records[0].publishTime == datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc)
    assert records[0].startTime == datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    await fast_client.aclose()


# 3. Correct endpoint paths and query parameters
@pytest.mark.asyncio
async def test_endpoint_paths_and_query_parameters(mock_elexon, fast_client):
    fuelhh_route = mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=[])
    )
    windfor_route = mock_elexon.get("/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json=[])
    )

    # FUELHH parameter verification
    await fast_client.fetch_fuelhh(
        settlement_date_from="2026-01-05",
        settlement_date_to="2026-01-07",
        fuel_type="WIND",
    )
    fuelhh_req = fuelhh_route.calls.last.request
    assert fuelhh_req.url.path == "/bmrs/api/v1/datasets/FUELHH/stream"
    assert fuelhh_req.url.params["settlementDateFrom"] == "2026-01-05"
    assert fuelhh_req.url.params["settlementDateTo"] == "2026-01-07"
    assert fuelhh_req.url.params["fuelType"] == "WIND"

    # WINDFOR parameter verification
    start_utc = datetime(2026, 1, 5, 8, 30, tzinfo=timezone.utc)
    end_utc = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    await fast_client.fetch_windfor(
        publish_datetime_from=start_utc,
        publish_datetime_to=end_utc,
    )
    windfor_req = windfor_route.calls.last.request
    assert windfor_req.url.path == "/bmrs/api/v1/datasets/WINDFOR/stream"
    assert windfor_req.url.params["publishDateTimeFrom"] == "2026-01-05T08:30:00Z"
    assert windfor_req.url.params["publishDateTimeTo"] == "2026-01-05T12:00:00Z"

    await fast_client.aclose()


# 4. Multiple records and timestamp parsing (timezone-aware UTC)
@pytest.mark.asyncio
async def test_multiple_records_and_timezone_awareness(mock_elexon, fast_client):
    mock_data = [
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-09T02:30:00Z",
            "startTime": "2026-01-10T00:00:00Z",
            "generation": 5000,
        },
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-09T04:30:00+00:00",
            "startTime": "2026-01-10T01:00:00+00:00",
            "generation": 5200,
        },
    ]
    mock_elexon.get("/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    records = await fast_client.fetch_windfor("2026-01-09T00:00:00Z", "2026-01-09T23:59:59Z")
    assert len(records) == 2
    for r in records:
        assert r.startTime.tzinfo == timezone.utc
        assert r.publishTime.tzinfo == timezone.utc

    assert records[0].publishTime == datetime(2026, 1, 9, 2, 30, tzinfo=timezone.utc)
    assert records[1].publishTime == datetime(2026, 1, 9, 4, 30, tzinfo=timezone.utc)
    await fast_client.aclose()


# 5. Empty response arrays
@pytest.mark.asyncio
async def test_empty_response_arrays(mock_elexon, fast_client):
    mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=[])
    )
    records = await fast_client.fetch_fuelhh("2026-01-01", "2026-01-01")
    assert records == []
    await fast_client.aclose()


# 6. Missing or null generation (preserved as None, never 0)
@pytest.mark.asyncio
async def test_missing_or_null_generation_preserved(mock_elexon, fast_client):
    mock_fuelhh = [
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-10T12:00:00Z",
            "startTime": "2026-01-10T11:30:00Z",
            "settlementDate": "2026-01-10",
            "settlementPeriod": 24,
            "fuelType": "WIND",
            "generation": None,
        }
    ]
    mock_windfor = [
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-09T09:30:00Z",
            "startTime": "2026-01-10T14:00:00Z",
            # generation field completely omitted
        }
    ]

    mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=mock_fuelhh)
    )
    mock_elexon.get("/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json=mock_windfor)
    )

    fuel_records = await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")
    wind_records = await fast_client.fetch_windfor("2026-01-09T00:00:00Z", "2026-01-09T23:59:59Z")

    assert fuel_records[0].generation is None
    assert fuel_records[0].generation != 0
    assert wind_records[0].generation is None
    assert wind_records[0].generation != 0
    await fast_client.aclose()


# 7. Malformed JSON and unexpected response shapes
@pytest.mark.asyncio
async def test_malformed_json_and_unexpected_shapes(mock_elexon, fast_client):
    # Non-JSON content
    mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, content=b"INVALID HTML NOT JSON")
    )
    with pytest.raises(ElexonResponseValidationError, match="not valid JSON"):
        await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")

    # JSON object instead of JSON list
    mock_elexon.get("/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json={"error": "Not an array"})
    )
    with pytest.raises(ElexonResponseValidationError, match="Expected JSON array"):
        await fast_client.fetch_windfor("2026-01-09T00:00:00Z", "2026-01-09T23:59:59Z")

    # Record missing required fields
    mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=[{"invalid": "record"}])
    )
    with pytest.raises(ElexonResponseValidationError, match="Invalid FUELHH record"):
        await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")

    await fast_client.aclose()


# 8. HTTP 429 followed by success (respecting Retry-After)
@pytest.mark.asyncio
async def test_http_429_retry_after_success(mock_elexon, fast_client):
    route = mock_elexon.get("/datasets/FUELHH/stream")
    route.side_effect = [
        httpx.Response(429, headers={"retry-after": "0.005"}, text="Rate Limit Exceeded"),
        httpx.Response(200, json=[]),
    ]

    records = await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")
    assert records == []
    assert route.call_count == 2
    await fast_client.aclose()


# 9. HTTP 5xx followed by success
@pytest.mark.asyncio
async def test_http_5xx_retry_success(mock_elexon, fast_client):
    route = mock_elexon.get("/datasets/WINDFOR/stream")
    route.side_effect = [
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(200, json=[]),
    ]

    records = await fast_client.fetch_windfor("2026-01-09T00:00:00Z", "2026-01-09T23:59:59Z")
    assert records == []
    assert route.call_count == 3
    await fast_client.aclose()


# 10. Non-retryable HTTP 4xx
@pytest.mark.asyncio
async def test_non_retryable_http_4xx(mock_elexon, fast_client):
    route = mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(400, text="Bad Request: upstream rejected parameter")
    )

    with pytest.raises(ElexonHttpError) as exc_info:
        await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")

    assert exc_info.value.status_code == 400
    assert route.call_count == 1  # Did NOT retry
    await fast_client.aclose()


# 11. Exhausted retries and timeout/connection failures
@pytest.mark.asyncio
async def test_exhausted_retries_500(mock_elexon, fast_client):
    route_500 = mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(500, text="Persistent Internal Server Error")
    )
    with pytest.raises(ElexonHttpError) as exc_info:
        await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")
    assert exc_info.value.status_code == 500
    assert route_500.call_count == 3  # 1 initial + 2 retries
    await fast_client.aclose()


@pytest.mark.asyncio
async def test_exhausted_retries_timeout(mock_elexon, fast_client):
    route_timeout = mock_elexon.get("/datasets/WINDFOR/stream").mock(
        side_effect=httpx.ReadTimeout("Read timed out")
    )
    with pytest.raises(ElexonTimeoutError):
        await fast_client.fetch_windfor("2026-01-09T00:00:00Z", "2026-01-09T23:59:59Z")
    assert route_timeout.call_count == 3
    await fast_client.aclose()


@pytest.mark.asyncio
async def test_exhausted_retries_connection_error(mock_elexon, fast_client):
    route_conn = mock_elexon.get("/datasets/FUELHH/stream").mock(
        side_effect=httpx.ConnectError("Failed to connect")
    )
    with pytest.raises(ElexonConnectionError):
        await fast_client.fetch_fuelhh("2026-01-10", "2026-01-10")
    assert route_conn.call_count == 3
    await fast_client.aclose()


# 12. Repeated calls without unintended client/resource leaks
@pytest.mark.asyncio
async def test_repeated_calls_and_context_manager(mock_elexon):
    mock_elexon.get("/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=[])
    )
    mock_elexon.get("/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json=[])
    )

    # Injected client pattern
    async with httpx.AsyncClient(base_url=DEFAULT_BASE_URL) as injected_http:
        client = ElexonClient(client=injected_http)
        for _ in range(5):
            await client.fetch_fuelhh("2026-01-10", "2026-01-10")
            await client.fetch_windfor("2026-01-09T00:00:00Z", "2026-01-09T23:59:59Z")
        # Ensure injected client is still open
        assert not injected_http.is_closed

    # Standalone async context manager pattern
    async with ElexonClient() as client:
        await client.fetch_fuelhh("2026-01-10", "2026-01-10")
    # Underlying client closed cleanly
    assert client._client.is_closed
