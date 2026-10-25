"""
app/clients/elexon.py

Asynchronous HTTP client for Elexon BMRS API endpoints:
- /datasets/FUELHH/stream
- /datasets/WINDFOR/stream
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx
from pydantic import ValidationError

from app.schemas.elexon import FuelHHRecord, WindforRecord, ensure_utc_datetime

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DEFAULT_TIMEOUT = httpx.Timeout(timeout=15.0, connect=5.0)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ElexonClientError(Exception):
    """Base exception for all Elexon client errors."""
    pass


class ElexonHttpError(ElexonClientError):
    """Raised when an HTTP error status is received from Elexon API."""
    def __init__(self, status_code: int, message: str, response_text: str = ""):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response_text = response_text


class ElexonTimeoutError(ElexonClientError):
    """Raised when an upstream request times out."""
    pass


class ElexonConnectionError(ElexonClientError):
    """Raised on network connection / transport failures."""
    pass


class ElexonResponseValidationError(ElexonClientError):
    """Raised when the upstream response cannot be parsed or validated against schemas."""
    pass


def format_date(d: date | str) -> str:
    """Format date to YYYY-MM-DD string."""
    if isinstance(d, date):
        return d.isoformat()
    if isinstance(d, str):
        # Validate format
        date.fromisoformat(d)
        return d
    raise ValueError(f"Expected date or YYYY-MM-DD string, got {type(d)}")


def format_utc_timestamp(dt: datetime | str) -> str:
    """Format datetime as ISO 8601 UTC string with trailing 'Z'."""
    utc_dt = ensure_utc_datetime(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    """
    Asynchronous client for interacting with Elexon BMRS streaming APIs.
    Supports client injection, connection pooling, backoff with jitter,
    and Retry-After compliance.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        client: Optional[httpx.AsyncClient] = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        jitter: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self._injected_client = client
        self._client = client or httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    async def __aenter__(self) -> ElexonClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client if not externally injected."""
        if self._injected_client is None and not self._client.is_closed:
            await self._client.aclose()

    def _calculate_backoff(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        """
        Calculate backoff delay using exponential backoff with jitter,
        respecting Retry-After header if present.
        """
        if response is not None and "retry-after" in response.headers:
            retry_after_raw = response.headers.get("retry-after", "")
            try:
                # Try parsing as integer seconds
                seconds = float(retry_after_raw)
                return min(max(0.0, seconds), self.max_delay)
            except ValueError:
                # If date format or unparseable, fall back to standard backoff
                pass

        # Exponential backoff: base_delay * 2^attempt
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay

    async def _request_stream(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute HTTP GET with bounded retries for 429, 5xx, and transient network errors.
        """
        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt <= self.max_retries:
            try:
                response = await self._client.get(path, params=params)

                # Check if successful
                if response.status_code == 200:
                    try:
                        raw_json = response.json()
                    except Exception as e:
                        raise ElexonResponseValidationError(
                            f"Response is not valid JSON from {path}: {e}"
                        ) from e

                    if not isinstance(raw_json, list):
                        raise ElexonResponseValidationError(
                            f"Expected JSON array from {path}, got {type(raw_json).__name__}: {str(raw_json)[:200]}"
                        )
                    return raw_json

                # Non-200 response handling
                status_code = response.status_code

                # Non-retryable 4xx client errors
                if 400 <= status_code < 500 and status_code != 429:
                    raise ElexonHttpError(
                        status_code=status_code,
                        message=f"Non-retryable client error on {path}",
                        response_text=response.text,
                    )

                # Retryable status codes: 429, 500, 502, 503, 504
                if status_code in RETRYABLE_STATUS_CODES:
                    if attempt == self.max_retries:
                        raise ElexonHttpError(
                            status_code=status_code,
                            message=f"Retries exhausted ({self.max_retries}) on {path}",
                            response_text=response.text,
                        )

                    delay = self._calculate_backoff(attempt, response)
                    logger.warning(
                        f"Retryable status {status_code} on {path}. Attempt {attempt + 1}/{self.max_retries}. Backoff: {delay:.3f}s"
                    )
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue

                # Any other unexpected HTTP status
                raise ElexonHttpError(
                    status_code=status_code,
                    message=f"Unexpected status code on {path}",
                    response_text=response.text,
                )

            except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_exception = e
                if attempt == self.max_retries:
                    raise ElexonTimeoutError(
                        f"Request timeout on {path} after {self.max_retries} retries: {e}"
                    ) from e

                delay = self._calculate_backoff(attempt)
                logger.warning(
                    f"Timeout on {path}. Attempt {attempt + 1}/{self.max_retries}. Retrying in {delay:.3f}s: {e}"
                )
                await asyncio.sleep(delay)
                attempt += 1

            except (httpx.NetworkError, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    raise ElexonConnectionError(
                        f"Network connection failure on {path} after {self.max_retries} retries: {e}"
                    ) from e

                delay = self._calculate_backoff(attempt)
                logger.warning(
                    f"Connection error on {path}. Attempt {attempt + 1}/{self.max_retries}. Retrying in {delay:.3f}s: {e}"
                )
                await asyncio.sleep(delay)
                attempt += 1

        if last_exception:
            raise ElexonConnectionError(f"Request failed on {path}: {last_exception}") from last_exception
        raise ElexonClientError(f"Request failed on {path} after {attempt} attempts")

    async def fetch_fuelhh(
        self,
        settlement_date_from: date | str,
        settlement_date_to: date | str,
        fuel_type: str = "WIND",
    ) -> list[FuelHHRecord]:
        """
        Fetch half-hourly generation outturn from /datasets/FUELHH/stream.
        """
        params = {
            "settlementDateFrom": format_date(settlement_date_from),
            "settlementDateTo": format_date(settlement_date_to),
            "fuelType": fuel_type,
        }

        records_json = await self._request_stream("/datasets/FUELHH/stream", params)

        validated: list[FuelHHRecord] = []
        for i, item in enumerate(records_json):
            try:
                validated.append(FuelHHRecord.model_validate(item))
            except ValidationError as e:
                raise ElexonResponseValidationError(
                    f"Invalid FUELHH record at index {i}: {e}. Record: {item}"
                ) from e

        return validated

    async def fetch_windfor(
        self,
        publish_datetime_from: datetime | str,
        publish_datetime_to: datetime | str,
    ) -> list[WindforRecord]:
        """
        Fetch wind generation forecast from /datasets/WINDFOR/stream.
        """
        params = {
            "publishDateTimeFrom": format_utc_timestamp(publish_datetime_from),
            "publishDateTimeTo": format_utc_timestamp(publish_datetime_to),
        }

        records_json = await self._request_stream("/datasets/WINDFOR/stream", params)

        validated: list[WindforRecord] = []
        for i, item in enumerate(records_json):
            try:
                validated.append(WindforRecord.model_validate(item))
            except ValidationError as e:
                raise ElexonResponseValidationError(
                    f"Invalid WINDFOR record at index {i}: {e}. Record: {item}"
                ) from e

        return validated
