"""
tests/services/test_metrics.py

Unit tests for statistical accuracy metrics using hand-verifiable examples:
13. Correct signed bias, MAE and RMSE using hand-calculated examples.
14. Correct absolute-error percentiles using a hand-calculated example.
15. Correct WAPE and zero-denominator handling.
17. Error grouping by hour of day and forecast horizon.
18. Empty inputs and no matched pairs.
"""

from datetime import datetime, timezone
import math
import pytest

from app.services.metrics import (
    MatchedPair,
    calculate_aggregate_metrics,
    calculate_metrics_by_delivery_hour,
    calculate_metrics_by_horizon,
)


@pytest.fixture
def hand_calculated_pairs():
    """
    4 hand-verifiable pairs:
    Pair 1: Forecast 100, Actual 80  -> Error +20, AbsError 20
    Pair 2: Forecast 150, Actual 160 -> Error -10, AbsError 10
    Pair 3: Forecast 200, Actual 170 -> Error +30, AbsError 30
    Pair 4: Forecast 80,  Actual 120 -> Error -40, AbsError 40

    Hand calculations:
    - Sum Errors = 20 - 10 + 30 - 40 = 0.0
    - Mean Bias = 0.0 / 4 = 0.0 MW
    - Sum Abs Errors = 20 + 10 + 30 + 40 = 100.0
    - MAE = 100.0 / 4 = 25.0 MW
    - Sum Squared Errors = 400 + 100 + 900 + 1600 = 3000.0
    - MSE = 3000.0 / 4 = 750.0
    - RMSE = sqrt(750.0) ~= 27.386127875...
    - Sum Actuals = 80 + 160 + 170 + 120 = 530.0
    - WAPE = 100.0 / 530.0 ~= 0.188679245...
    - Sorted Abs Errors: [10.0, 20.0, 30.0, 40.0]
      P50 = 25.0
      P90 = 30.0 + 0.7 * (40.0 - 30.0) = 37.0
      P95 = 30.0 + 0.85 * (40.0 - 30.0) = 38.5
    """
    pairs = [
        MatchedPair(
            target_start_utc=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
            delivery_hour_local=8,
            publish_time_utc=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
            horizon_hours=22.5,
            forecast_generation_mw=100.0,
            actual_generation_mw=80.0,
            error_mw=20.0,
            absolute_error_mw=20.0,
        ),
        MatchedPair(
            target_start_utc=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
            delivery_hour_local=8,
            publish_time_utc=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
            horizon_hours=22.5,
            forecast_generation_mw=150.0,
            actual_generation_mw=160.0,
            error_mw=-10.0,
            absolute_error_mw=10.0,
        ),
        MatchedPair(
            target_start_utc=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
            delivery_hour_local=14,
            publish_time_utc=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
            horizon_hours=28.5,
            forecast_generation_mw=200.0,
            actual_generation_mw=170.0,
            error_mw=30.0,
            absolute_error_mw=30.0,
        ),
        MatchedPair(
            target_start_utc=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
            delivery_hour_local=14,
            publish_time_utc=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
            horizon_hours=28.5,
            forecast_generation_mw=80.0,
            actual_generation_mw=120.0,
            error_mw=-40.0,
            absolute_error_mw=40.0,
        ),
    ]
    return pairs


# 13. Correct signed bias, MAE and RMSE using hand-calculated examples
def test_hand_calculated_metrics(hand_calculated_pairs):
    m = calculate_aggregate_metrics(hand_calculated_pairs)

    assert m.sample_count == 4
    assert m.mae_mw == 25.0
    assert pytest.approx(m.rmse_mw, abs=1e-5) == math.sqrt(750.0)
    assert m.mean_bias_mw == 0.0
    assert m.total_actual_energy_mwh == 530.0
    assert m.total_forecast_energy_mwh == 530.0
    assert m.total_absolute_error_mwh == 100.0


# 14. Correct absolute-error percentiles using hand-calculated example
def test_hand_calculated_percentiles(hand_calculated_pairs):
    m = calculate_aggregate_metrics(hand_calculated_pairs)

    assert m.p50_absolute_error_mw == 25.0
    assert pytest.approx(m.p90_absolute_error_mw, abs=1e-5) == 37.0
    assert pytest.approx(m.p95_absolute_error_mw, abs=1e-5) == 38.5


# 15. Correct WAPE and zero-denominator handling
def test_wape_calculation_and_zero_denominator(hand_calculated_pairs):
    m = calculate_aggregate_metrics(hand_calculated_pairs)
    assert pytest.approx(m.wape, abs=1e-5) == (100.0 / 530.0)
    assert m.wape_unavailable_reason is None

    # Test zero actual generation (calm day with zero wind)
    zero_actual_pair = [
        MatchedPair(
            target_start_utc=datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc),
            delivery_hour_local=0,
            publish_time_utc=datetime(2026, 1, 9, 9, 30, tzinfo=timezone.utc),
            horizon_hours=14.5,
            forecast_generation_mw=50.0,
            actual_generation_mw=0.0,  # Zero wind
            error_mw=50.0,
            absolute_error_mw=50.0,
        )
    ]
    m_zero = calculate_aggregate_metrics(zero_actual_pair)
    assert m_zero.wape is None
    assert "denominator is undefined" in m_zero.wape_unavailable_reason


# 17. Error grouping by hour of day and forecast horizon
def test_metrics_grouping_by_hour_and_horizon(hand_calculated_pairs):
    hourly = calculate_metrics_by_delivery_hour(hand_calculated_pairs)
    # Hours present: 08:00 and 14:00
    assert len(hourly) == 2
    h08 = next(h for h in hourly if h.group_key == "08:00")
    h14 = next(h for h in hourly if h.group_key == "14:00")

    # Hour 08: Errors +20 and -10 -> Bias: +5.0, MAE: 15.0
    assert h08.sample_count == 2
    assert h08.mean_bias_mw == 5.0
    assert h08.mae_mw == 15.0

    # Hour 14: Errors +30 and -40 -> Bias: -5.0, MAE: 35.0
    assert h14.sample_count == 2
    assert h14.mean_bias_mw == -5.0
    assert h14.mae_mw == 35.0

    horizon = calculate_metrics_by_horizon(hand_calculated_pairs)
    # Horizon 22.5h falls into "18h - 24h", Horizon 28.5h falls into "24h - 30h"
    assert len(horizon) == 2
    b1 = next(b for b in horizon if b.group_key == "18h - 24h")
    b2 = next(b for b in horizon if b.group_key == "24h - 30h")
    assert b1.sample_count == 2
    assert b2.sample_count == 2


# 18. Empty inputs and no matched pairs
def test_empty_inputs_returns_safe_null_metrics():
    m = calculate_aggregate_metrics([])
    assert m.sample_count == 0
    assert m.mae_mw is None
    assert m.rmse_mw is None
    assert m.mean_bias_mw is None
    assert m.p50_absolute_error_mw is None
    assert m.p90_absolute_error_mw is None
    assert m.p95_absolute_error_mw is None
    assert m.wape is None
    assert "No matched pairs" in m.wape_unavailable_reason

    assert calculate_metrics_by_delivery_hour([]) == []
    assert calculate_metrics_by_horizon([]) == []
