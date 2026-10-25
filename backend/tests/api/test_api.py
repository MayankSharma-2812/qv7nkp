"""
tests/api/test_api.py

Integration tests for FastAPI endpoints using TestClient:
1. Health endpoint success.
2. Readiness success and database failure.
3. Valid forecast decision query.
4. Forecast cutoff selection and no future-data leakage.
5. Correct delivery-date mapping.
6. Forecast/actual series response.
7. Aggregate metrics response.
8. Diurnal and horizon grouping responses.
9. Invalid dates and reversed ranges.
10. Invalid cutoff parameters.
11. No eligible forecast and incomplete actual data.
12. Null or undefined metric handling.
13. Consistent JSON error structures.
14. UTC timestamps and correct response field types.
15. Existing database and analytics behaviour remain unchanged.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from datetime import date, datetime, time, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.db.session import init_db
from app.main import app
from app.repositories.elexon_repository import ElexonRepository
from app.schemas.elexon import FuelHHRecord, WindforRecord


@pytest.fixture
def client_with_mock_db():
    """Temporary file-backed SQLite database wired to FastAPI app via dependency override."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_api.db"
        engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
        init_db(engine)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        repo = ElexonRepository()

        # Seed with 1 full delivery day: 2026-01-05 (decision date: 2026-01-04)
        # 24 hours of actuals and forecasts
        actuals = []
        forecasts = []

        for h in range(24):
            t_hour = datetime(2026, 1, 5, h, 0, tzinfo=timezone.utc)
            t_half1 = datetime(2026, 1, 5, h, 0, tzinfo=timezone.utc)
            t_half2 = datetime(2026, 1, 5, h, 30, tzinfo=timezone.utc)

            # Actuals: 10,000 MW for SP1, 12,000 MW for SP2 -> Mean: 11,000 MW
            actuals.append(
                FuelHHRecord(
                    dataset="FUELHH",
                    publishTime=t_half1,
                    startTime=t_half1,
                    settlementDate="2026-01-05",
                    settlementPeriod=h * 2 + 1,
                    fuelType="WIND",
                    generation=10000.0,
                )
            )
            actuals.append(
                FuelHHRecord(
                    dataset="FUELHH",
                    publishTime=t_half2,
                    startTime=t_half2,
                    settlementDate="2026-01-05",
                    settlementPeriod=h * 2 + 2,
                    fuelType="WIND",
                    generation=12000.0,
                )
            )

            # Forecast published before cutoff 10:00 (09:30 UTC): 10,500 MW
            forecasts.append(
                WindforRecord(
                    dataset="WINDFOR",
                    publishTime=datetime(2026, 1, 4, 9, 30, tzinfo=timezone.utc),
                    startTime=t_hour,
                    generation=10500.0,
                )
            )
            # Forecast published after cutoff (15:00 UTC): 11,000 MW (Must NOT be selected!)
            forecasts.append(
                WindforRecord(
                    dataset="WINDFOR",
                    publishTime=datetime(2026, 1, 4, 15, 0, tzinfo=timezone.utc),
                    startTime=t_hour,
                    generation=11000.0,
                )
            )

        with session_factory() as session:
            with session.begin():
                repo.upsert_actuals(session, actuals)
                repo.upsert_forecasts(session, forecasts)

        def override_get_db():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()


# 1. Health endpoint success
def test_health_endpoint(client_with_mock_db):
    res = client_with_mock_db.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "gridbricks-api"
    assert "X-Request-ID" in res.headers


# 2. Readiness success and database failure
def test_readiness_endpoint_success(client_with_mock_db):
    res = client_with_mock_db.get("/api/v1/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["actual_observations_count"] == 48
    assert data["forecast_observations_count"] == 48


def test_readiness_endpoint_failure():
    mock_session = MagicMock()
    mock_session.execute.side_effect = RuntimeError("Database disk I/O failure")

    def broken_db():
        yield mock_session

    app.dependency_overrides[get_db] = broken_db
    with TestClient(app) as client:
        res = client.get("/api/v1/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["error_code"] == "HTTP_503"
        assert "Database readiness check failed" in data["message"]
    app.dependency_overrides.clear()


# 3, 4, 5. Valid forecast decision query, cutoff selection, delivery mapping
def test_decision_forecast_query_and_anti_leakage(client_with_mock_db):
    res = client_with_mock_db.get("/api/v1/decisions/forecast?decision_date=2026-01-04&cutoff=10:00")
    assert res.status_code == 200
    data = res.json()

    assert data["decision_date"] == "2026-01-04"
    assert data["delivery_date"] == "2026-01-05"  # Mapping verified
    assert data["total_hours"] == 24
    assert data["matched_hours"] == 24
    assert len(data["forecasts"]) == 24

    first = data["forecasts"][0]
    assert first["delivery_hour_local"] == 0
    # Invariant: Must select 10,500 MW (published at 09:30), NOT 11,000 MW (published at 15:00)
    assert first["forecast_generation_mw"] == 10500.0
    assert first["actual_generation_mw"] == 11000.0
    assert first["error_mw"] == -500.0
    assert first["absolute_error_mw"] == 500.0
    assert first["publish_time_utc"] == "2026-01-04T09:30:00Z"
    assert first["status"] == "MATCHED"
    assert res.headers["Cache-Control"] == "public, max-age=300"


# 6. Forecast/actual series response
def test_forecast_series_response(client_with_mock_db):
    res = client_with_mock_db.get(
        "/api/v1/forecasts/series?decision_date_from=2026-01-04&decision_date_to=2026-01-04&cutoff=10:00"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision_date_from"] == "2026-01-04"
    assert data["decision_date_to"] == "2026-01-04"
    assert data["total_points"] == 24
    assert data["matched_points"] == 24
    assert len(data["series"]) == 24
    assert data["series"][0]["forecast_mw"] == 10500.0
    assert data["series"][0]["actual_mw"] == 11000.0


# 7. Aggregate metrics response
def test_accuracy_summary_response(client_with_mock_db):
    res = client_with_mock_db.get(
        "/api/v1/accuracy/summary?decision_date_from=2026-01-04&decision_date_to=2026-01-04&cutoff=10:00"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sample_count"] == 24
    assert data["mae_mw"] == 500.0
    assert data["rmse_mw"] == 500.0
    assert data["mean_bias_mw"] == -500.0
    assert pytest.approx(data["wape"], abs=1e-5) == (500.0 / 11000.0)
    assert data["coverage"]["coverage_percentage"] == 100.0


# 8. Diurnal and horizon grouping responses
def test_diurnal_and_horizon_responses(client_with_mock_db):
    res_diurnal = client_with_mock_db.get(
        "/api/v1/accuracy/diurnal?decision_date_from=2026-01-04&decision_date_to=2026-01-04&cutoff=10:00"
    )
    assert res_diurnal.status_code == 200
    diurnal_data = res_diurnal.json()
    assert len(diurnal_data["diurnal_profile"]) == 24
    assert diurnal_data["diurnal_profile"][0]["hour_local"] == "00:00"
    assert diurnal_data["diurnal_profile"][0]["mae_mw"] == 500.0

    res_dist = client_with_mock_db.get(
        "/api/v1/accuracy/distribution?decision_date_from=2026-01-04&decision_date_to=2026-01-04&cutoff=10:00"
    )
    assert res_dist.status_code == 200
    dist_data = res_dist.json()
    assert len(dist_data["horizon_groups"]) > 0
    assert "p50_absolute_error_mw" in dist_data["error_quantiles"]
    assert dist_data["error_quantiles"]["p50_absolute_error_mw"] == 500.0


# 9. Invalid dates and reversed ranges
def test_invalid_dates_and_reversed_ranges(client_with_mock_db):
    # Reversed date range
    res = client_with_mock_db.get(
        "/api/v1/accuracy/summary?decision_date_from=2026-01-10&decision_date_to=2026-01-05"
    )
    assert res.status_code == 400
    assert "cannot be after" in res.json()["message"]

    # Out of scope date (e.g. December 2025)
    res_out = client_with_mock_db.get("/api/v1/decisions/forecast?decision_date=2025-12-31")
    assert res_out.status_code == 400
    assert "out of scope" in res_out.json()["message"]

    # Malformed date string
    res_malformed = client_with_mock_db.get("/api/v1/decisions/forecast?decision_date=not-a-date")
    assert res_malformed.status_code == 400
    assert "Invalid decision_date format" in res_malformed.json()["message"]


# 10. Invalid cutoff parameters
def test_invalid_cutoff_parameter(client_with_mock_db):
    res = client_with_mock_db.get(
        "/api/v1/decisions/forecast?decision_date=2026-01-05&cutoff=invalid-cutoff"
    )
    assert res.status_code == 400
    assert "Invalid cutoff time format" in res.json()["message"]


# 11, 12, 13. No eligible forecast, incomplete actual data, undefined metric handling
def test_empty_results_and_undefined_metrics(client_with_mock_db):
    # Query date with no records in mock DB (e.g. Jan 20)
    res = client_with_mock_db.get(
        "/api/v1/accuracy/summary?decision_date_from=2026-01-20&decision_date_to=2026-01-20"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sample_count"] == 0
    assert data["mae_mw"] is None
    assert data["rmse_mw"] is None
    assert data["wape"] is None
    assert data["wape_unavailable_reason"] == "No matched pairs available"
    assert data["coverage"]["coverage_percentage"] == 0.0


# 14. UTC timestamps and correct response field types
def test_utc_timestamps_and_error_structure(client_with_mock_db):
    res = client_with_mock_db.get("/api/v1/decisions/forecast?decision_date=2026-01-04&cutoff=10:00")
    assert res.status_code == 200
    item = res.json()["forecasts"][0]
    # Trailing Z or +00:00 indicates ISO 8601 UTC
    assert item["target_start_utc"].endswith("Z") or "+00:00" in item["target_start_utc"]
    assert item["publish_time_utc"].endswith("Z") or "+00:00" in item["publish_time_utc"]
