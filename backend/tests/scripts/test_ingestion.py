"""
tests/scripts/test_ingestion.py

Deterministic automated tests for the historical ingestion script:
- Date-chunk boundaries and complete range coverage without gaps.
- Repeat ingestion without duplicate records.
- Partial or failed API chunks handling.
- End-to-end mocked ingestion execution.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import pytest

from app.clients.elexon import ElexonClient
from app.db.session import get_engine, get_session_factory
from app.repositories.elexon_repository import ElexonRepository
from app.schemas.elexon import FuelHHRecord, WindforRecord
from scripts.ingest_elexon import (
    generate_date_chunks,
    generate_datetime_chunks,
    run_ingestion,
)


# 1. Date chunk boundaries and complete range coverage
def test_generate_date_chunks_coverage():
    start = date(2026, 1, 2)
    end = date(2026, 2, 1)  # 31 days total
    chunks = list(generate_date_chunks(start, end, chunk_size_days=7))

    assert len(chunks) == 5
    # First chunk starts on Jan 2
    assert chunks[0][0] == date(2026, 1, 2)
    assert chunks[0][1] == date(2026, 1, 8)

    # Check contiguous coverage without gaps or overlaps
    for i in range(len(chunks) - 1):
        assert chunks[i][1] + timedelta(days=1) == chunks[i + 1][0]

    # Final chunk ends on Feb 1
    assert chunks[-1][1] == date(2026, 2, 1)


# 2. Datetime chunk boundaries and complete range coverage
def test_generate_datetime_chunks_coverage():
    start = datetime(2025, 12, 30, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, 23, 59, 59, tzinfo=timezone.utc)
    chunks = list(generate_datetime_chunks(start, end, chunk_size_days=7))

    assert len(chunks) == 5
    assert chunks[0][0] == start

    # Check contiguous second-level coverage
    for i in range(len(chunks) - 1):
        assert chunks[i][1] + timedelta(seconds=1) == chunks[i + 1][0]

    assert chunks[-1][1] == end


# Mock client for deterministic end-to-end tests
class MockElexonClient(ElexonClient):
    def __init__(self, fail_fuel_chunk_index: int | None = None):
        self.fail_fuel_chunk_index = fail_fuel_chunk_index
        self.call_fuel_count = 0
        self.call_wind_count = 0

    async def fetch_fuelhh(self, settlement_date_from, settlement_date_to, fuel_type="WIND"):
        self.call_fuel_count += 1
        if self.fail_fuel_chunk_index == self.call_fuel_count:
            raise RuntimeError(f"Simulated network error on chunk {self.call_fuel_count}")

        # Return 2 records per call
        st_from = date.fromisoformat(str(settlement_date_from))
        dt = datetime(st_from.year, st_from.month, st_from.day, 12, 0, tzinfo=timezone.utc)
        return [
            FuelHHRecord(
                dataset="FUELHH",
                publishTime=dt + timedelta(minutes=30),
                startTime=dt,
                settlementDate=str(settlement_date_from),
                settlementPeriod=24,
                fuelType=fuel_type,
                generation=5000.0,
            )
        ]

    async def fetch_windfor(self, publish_datetime_from, publish_datetime_to):
        self.call_wind_count += 1
        # Return 1 record inside target window and 1 outside
        return [
            WindforRecord(
                dataset="WINDFOR",
                publishTime=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),  # Inside target window
                generation=8888.0,
            ),
            WindforRecord(
                dataset="WINDFOR",
                publishTime=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
                startTime=datetime(2025, 12, 31, 12, 0, tzinfo=timezone.utc),  # Outside target window
                generation=4444.0,
            ),
        ]

    async def aclose(self):
        pass


# 3. Partial or failed API chunks handling
@pytest.mark.asyncio
async def test_partial_failed_chunks_handling():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_partial.db")
        mock_client = MockElexonClient(fail_fuel_chunk_index=2)

        report = await run_ingestion(
            db_path=db_path,
            fuelhh_start=date(2026, 1, 2),
            fuelhh_end=date(2026, 1, 15),  # 2 chunks of 7 days
            windfor_pub_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            windfor_pub_end=datetime(2026, 1, 8, 23, 59, 59, tzinfo=timezone.utc),
            target_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            target_end=datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc),
            chunk_days=7,
            client=mock_client,
        )

        assert report["status"] == "COMPLETED_WITH_FAILURES"
        assert report["fuelhh"]["chunks_failed"] == 1
        assert report["fuelhh"]["chunks_successful"] == 1
        assert len(report["fuelhh"]["failed_chunks"]) == 1
        assert "Simulated network error" in report["fuelhh"]["failed_chunks"][0]["error"]
        # Forecasts still succeeded
        assert report["windfor"]["chunks_successful"] == 1


# 4. Repeat ingestion without duplicate records
@pytest.mark.asyncio
async def test_repeat_ingestion_idempotency():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_idempotent.db")
        mock_client = MockElexonClient()

        # Run 1
        report1 = await run_ingestion(
            db_path=db_path,
            fuelhh_start=date(2026, 1, 2),
            fuelhh_end=date(2026, 1, 8),
            windfor_pub_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            windfor_pub_end=datetime(2026, 1, 8, 23, 59, 59, tzinfo=timezone.utc),
            target_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            target_end=datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc),
            chunk_days=7,
            client=mock_client,
        )
        assert report1["status"] == "SUCCESS"
        initial_actuals = report1["final_database_stats"]["actuals"]["total_rows"]
        initial_forecasts = report1["final_database_stats"]["forecasts"]["total_rows"]

        # Run 2 (exact same date ranges)
        report2 = await run_ingestion(
            db_path=db_path,
            fuelhh_start=date(2026, 1, 2),
            fuelhh_end=date(2026, 1, 8),
            windfor_pub_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            windfor_pub_end=datetime(2026, 1, 8, 23, 59, 59, tzinfo=timezone.utc),
            target_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            target_end=datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc),
            chunk_days=7,
            client=mock_client,
        )
        assert report2["status"] == "SUCCESS"
        assert report2["final_database_stats"]["actuals"]["total_rows"] == initial_actuals
        assert report2["final_database_stats"]["forecasts"]["total_rows"] == initial_forecasts
