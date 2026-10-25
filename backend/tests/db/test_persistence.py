"""
tests/db/test_persistence.py

Deterministic automated tests for database persistence and repository operations:
- Database initialization.
- Actual-observation persistence.
- Forecast-version persistence.
- Unique constraints and idempotent upserts.
- Updated values replacing existing rows correctly.
- Null generation preservation.
- Timestamp round-tripping with timezone awareness.
- Forecast target-date filtering.
- Transaction rollback on failure.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db.models import ActualObservation, Base, ForecastObservation
from app.db.session import init_db
from app.repositories.elexon_repository import ElexonRepository
from app.schemas.elexon import FuelHHRecord, WindforRecord


@pytest.fixture
def memory_db():
    """In-memory SQLite database for deterministic, fast testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    repo = ElexonRepository()
    return {"engine": engine, "session_factory": session_factory, "repo": repo}


# 1. Database initialization
def test_database_initialization(memory_db):
    engine = memory_db["engine"]
    with engine.connect() as conn:
        # Check that tables exist in SQLite sqlite_master
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).scalars().all()
        assert "actual_observations" in result
        assert "forecast_observations" in result


# 2. Actual-observation persistence
def test_actual_observation_persistence(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    record = FuelHHRecord(
        dataset="FUELHH",
        publishTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10",
        settlementPeriod=24,
        fuelType="WIND",
        generation=8120.0,
    )

    with session_factory() as session:
        with session.begin():
            res = repo.upsert_actuals(session, [record])
        assert res["upserted"] == 1

    with session_factory() as session:
        results = repo.get_actuals(session)
        assert len(results) == 1
        obs = results[0]
        assert obs.dataset == "FUELHH"
        assert obs.fuel_type == "WIND"
        assert obs.settlement_date == "2026-01-10"
        assert obs.settlement_period == 24
        assert obs.generation_mw == 8120.0
        assert obs.start_time_utc == datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc)
        assert obs.publish_time_utc == datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


# 3. Forecast-version persistence (multiple publications preserved for same startTime)
def test_forecast_multiple_publication_versions(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    target_start = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    rec1 = WindforRecord(
        dataset="WINDFOR",
        publishTime=datetime(2026, 1, 9, 2, 30, tzinfo=timezone.utc),
        startTime=target_start,
        generation=9000.0,
    )
    rec2 = WindforRecord(
        dataset="WINDFOR",
        publishTime=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
        startTime=target_start,
        generation=9500.0,
    )
    rec3 = WindforRecord(
        dataset="WINDFOR",
        publishTime=datetime(2026, 1, 9, 15, 30, tzinfo=timezone.utc),
        startTime=target_start,
        generation=9800.0,
    )

    with session_factory() as session:
        with session.begin():
            repo.upsert_forecasts(session, [rec1, rec2, rec3])

    with session_factory() as session:
        results = repo.get_forecasts(session)
        # All 3 publication versions must be preserved
        assert len(results) == 3
        pub_times = [r.publish_time_utc for r in results]
        assert pub_times == [
            datetime(2026, 1, 9, 15, 30, tzinfo=timezone.utc),
            datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
            datetime(2026, 1, 9, 2, 30, tzinfo=timezone.utc),
        ]


# 4. Unique constraints and idempotent upserts (no duplicate rows on replay)
def test_idempotent_upsert(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    actual_rec = FuelHHRecord(
        dataset="FUELHH",
        publishTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10",
        settlementPeriod=24,
        fuelType="WIND",
        generation=8000.0,
    )
    forecast_rec = WindforRecord(
        dataset="WINDFOR",
        publishTime=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        generation=9200.0,
    )

    # Ingest once
    with session_factory() as session:
        with session.begin():
            repo.upsert_actuals(session, [actual_rec])
            repo.upsert_forecasts(session, [forecast_rec])

    # Ingest duplicate records a second and third time
    for _ in range(2):
        with session_factory() as session:
            with session.begin():
                repo.upsert_actuals(session, [actual_rec])
                repo.upsert_forecasts(session, [forecast_rec])

    with session_factory() as session:
        stats = repo.get_database_stats(session)
        assert stats["actuals"]["total_rows"] == 1
        assert stats["forecasts"]["total_rows"] == 1


# 5. Updated values replacing existing rows correctly
def test_updated_values_replacement(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    rec_v1 = FuelHHRecord(
        dataset="FUELHH",
        publishTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10",
        settlementPeriod=24,
        fuelType="WIND",
        generation=8000.0,
    )
    rec_v2 = FuelHHRecord(
        dataset="FUELHH",
        publishTime=datetime(2026, 1, 10, 13, 0, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10",
        settlementPeriod=24,
        fuelType="WIND",
        generation=8250.0,  # Corrected outturn
    )

    with session_factory() as session:
        with session.begin():
            repo.upsert_actuals(session, [rec_v1])

    with session_factory() as session:
        with session.begin():
            repo.upsert_actuals(session, [rec_v2])

    with session_factory() as session:
        results = repo.get_actuals(session)
        assert len(results) == 1
        assert results[0].generation_mw == 8250.0
        assert results[0].publish_time_utc == datetime(2026, 1, 10, 13, 0, tzinfo=timezone.utc)


# 6. Null generation preservation (never replaced with 0.0)
def test_null_generation_preservation(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    null_actual = FuelHHRecord(
        dataset="FUELHH",
        publishTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10",
        settlementPeriod=24,
        fuelType="WIND",
        generation=None,
    )
    null_forecast = WindforRecord(
        dataset="WINDFOR",
        publishTime=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        generation=None,
    )

    with session_factory() as session:
        with session.begin():
            repo.upsert_actuals(session, [null_actual])
            repo.upsert_forecasts(session, [null_forecast])

    with session_factory() as session:
        actual = repo.get_actuals(session)[0]
        forecast = repo.get_forecasts(session)[0]
        assert actual.generation_mw is None
        assert actual.generation_mw != 0.0
        assert forecast.generation_mw is None
        assert forecast.generation_mw != 0.0


# 7. Timestamp round-tripping with timezone awareness
def test_timestamp_round_tripping(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    dt_start = datetime(2026, 1, 15, 8, 30, 0, tzinfo=timezone.utc)
    dt_pub = datetime(2026, 1, 14, 10, 0, 0, tzinfo=timezone.utc)

    rec = WindforRecord(
        dataset="WINDFOR",
        publishTime=dt_pub,
        startTime=dt_start,
        generation=7777.0,
    )

    with session_factory() as session:
        with session.begin():
            repo.upsert_forecasts(session, [rec])

    with session_factory() as session:
        loaded = repo.get_forecasts(session)[0]
        assert loaded.start_time_utc.tzinfo == timezone.utc
        assert loaded.publish_time_utc.tzinfo == timezone.utc
        assert loaded.start_time_utc == dt_start
        assert loaded.publish_time_utc == dt_pub


# 8. Forecast target-date filtering
def test_forecast_target_date_filtering(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    pub_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    rec_before = WindforRecord(
        dataset="WINDFOR",
        publishTime=pub_time,
        startTime=datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc),  # Target < Jan 2
        generation=5000.0,
    )
    rec_inside = WindforRecord(
        dataset="WINDFOR",
        publishTime=pub_time,
        startTime=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),  # Target = Jan 2 (keep)
        generation=6000.0,
    )
    rec_after = WindforRecord(
        dataset="WINDFOR",
        publishTime=pub_time,
        startTime=datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc),  # Target = Feb 2 (exclude)
        generation=7000.0,
    )

    with session_factory() as session:
        with session.begin():
            res = repo.upsert_forecasts(
                session,
                [rec_before, rec_inside, rec_after],
                target_start=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
                target_end=datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc),
            )
        assert res["retrieved"] == 3
        assert res["filtered_out"] == 2
        assert res["upserted"] == 1

    with session_factory() as session:
        results = repo.get_forecasts(session)
        assert len(results) == 1
        assert results[0].start_time_utc == datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)


# 9. Transaction rollback on failure
def test_transaction_rollback(memory_db):
    session_factory = memory_db["session_factory"]
    repo = memory_db["repo"]

    valid_record = FuelHHRecord(
        dataset="FUELHH",
        publishTime=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        startTime=datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10",
        settlementPeriod=24,
        fuelType="WIND",
        generation=5000.0,
    )

    # Verify that an unhandled exception inside transaction rolls back all changes
    try:
        with session_factory() as session:
            with session.begin():
                repo.upsert_actuals(session, [valid_record])
                raise RuntimeError("Simulated failure before transaction commit")
    except RuntimeError:
        pass

    with session_factory() as session:
        count = session.scalar(select(ActualObservation.id))
        assert count is None  # Table remains empty
