"""
tests/services/test_evaluation_integration.py

Integration tests for ForecastEvaluationService using in-memory SQLite database.
Tests complete pipeline from database query to selected forecasts, aligned actuals,
and final metrics.
"""

from datetime import date, datetime, time, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import init_db
from app.repositories.elexon_repository import ElexonRepository
from app.schemas.elexon import FuelHHRecord, WindforRecord
from app.services.evaluation import ForecastEvaluationService


@pytest.fixture
def test_evaluation_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    repo = ElexonRepository()

    # Populate 1 target day: delivery 2026-01-05 (decision date: 2026-01-04)
    # Target hours: 00:00 to 23:00 (24 hours)
    target_delivery = date(2026, 1, 5)
    decision_date = date(2026, 1, 4)

    actuals = []
    forecasts = []

    for h in range(24):
        t_hour = datetime(2026, 1, 5, h, 0, tzinfo=timezone.utc)
        t_half1 = datetime(2026, 1, 5, h, 0, tzinfo=timezone.utc)
        t_half2 = datetime(2026, 1, 5, h, 30, tzinfo=timezone.utc)

        # Actuals: 10,000 MW for first half, 12,000 MW for second half -> Hourly Mean: 11,000 MW
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

        # Forecast published before cutoff (09:30 UTC): 10,500 MW (Error = 10,500 - 11,000 = -500 MW)
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

    return {"session_factory": session_factory, "repo": repo}


def test_forecast_evaluation_service_end_to_end(test_evaluation_db):
    session_factory = test_evaluation_db["session_factory"]
    repo = test_evaluation_db["repo"]
    service = ForecastEvaluationService(repo=repo)

    with session_factory() as session:
        res = service.evaluate(
            session=session,
            decision_date_from=date(2026, 1, 4),
            decision_date_to=date(2026, 1, 4),
            cutoff_time=time(10, 0),
        )

    assert res.decision_date_from == date(2026, 1, 4)
    assert res.decision_date_to == date(2026, 1, 4)
    assert res.delivery_date_from == date(2026, 1, 5)
    assert res.delivery_date_to == date(2026, 1, 5)

    # Coverage checks
    cov = res.coverage
    assert cov.total_expected_target_hours == 24
    assert cov.matched_pairs_evaluated == 24
    assert cov.coverage_percentage == 100.0
    assert cov.excluded_targets_count == 0

    # Metric checks: All 24 hours have forecast 10,500 MW and actual 11,000 MW
    # Error = 10,500 - 11,000 = -500 MW
    # MAE = 500.0 MW
    # RMSE = 500.0 MW
    # Bias = -500.0 MW
    # WAPE = (24 * 500) / (24 * 11000) = 500 / 11000 ~= 0.0454545...
    m = res.metrics
    assert m.sample_count == 24
    assert m.mae_mw == 500.0
    assert m.rmse_mw == 500.0
    assert m.mean_bias_mw == -500.0
    assert pytest.approx(m.wape, abs=1e-5) == (500.0 / 11000.0)
    assert m.p50_absolute_error_mw == 500.0
    assert m.p90_absolute_error_mw == 500.0

    # Hourly metrics: 24 hourly rows
    assert len(res.hourly_metrics) == 24
    for row in res.hourly_metrics:
        assert row.sample_count == 1
        assert row.mae_mw == 500.0
        assert row.mean_bias_mw == -500.0
        assert row.mean_forecast_mw == 10500.0
        assert row.mean_actual_mw == 11000.0
