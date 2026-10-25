"""
tests/services/test_actuals.py

Unit tests for half-hourly FUELHH actuals alignment and aggregation:
10. Two half-hour actuals correctly aggregate to hourly actual generation.
11. Missing first or second half-hour actuals.
12. Null generation handling in actuals.
16. Missing observations and coverage counts.
"""

from datetime import datetime, timezone
import pytest

from app.schemas.elexon import FuelHHRecord
from app.services.actuals import aggregate_hourly_actuals


# 10. Two half-hour actuals correctly aggregate to hourly actual generation
def test_two_half_hours_aggregate_correctly():
    t_hour = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    t_half1 = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    t_half2 = datetime(2026, 1, 10, 14, 30, tzinfo=timezone.utc)

    # 8,000 MW and 10,000 MW -> Mean: 9,000 MW
    rec1 = FuelHHRecord(
        dataset="FUELHH",
        publishTime="2026-01-10T14:30:00Z",
        startTime=t_half1,
        settlementDate="2026-01-10",
        settlementPeriod=29,
        fuelType="WIND",
        generation=8000.0,
    )
    rec2 = FuelHHRecord(
        dataset="FUELHH",
        publishTime="2026-01-10T15:00:00Z",
        startTime=t_half2,
        settlementDate="2026-01-10",
        settlementPeriod=30,
        fuelType="WIND",
        generation=10000.0,
    )

    actuals, stats = aggregate_hourly_actuals(
        target_hours=[t_hour],
        actual_records=[rec1, rec2],
        fuel_type="WIND",
    )

    assert t_hour in actuals
    res = actuals[t_hour]
    assert res.is_complete is True
    assert res.interval_count == 2
    assert res.first_half_mw == 8000.0
    assert res.second_half_mw == 10000.0
    assert res.generation_mw == 9000.0
    assert stats.complete_hourly_actuals == 1
    assert stats.incomplete_hourly_actuals == 0


# 11. Missing first or second half-hour actuals
def test_missing_half_hour_actuals_marked_incomplete():
    t_hour1 = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    t_hour2 = datetime(2026, 1, 10, 15, 0, tzinfo=timezone.utc)
    t_hour3 = datetime(2026, 1, 10, 16, 0, tzinfo=timezone.utc)

    # Hour 1: Only first half exists
    rec_h1_first = FuelHHRecord(
        dataset="FUELHH", publishTime="2026-01-10T14:30:00Z",
        startTime=t_hour1, settlementDate="2026-01-10",
        settlementPeriod=29, fuelType="WIND", generation=5000.0,
    )
    # Hour 2: Only second half exists
    rec_h2_second = FuelHHRecord(
        dataset="FUELHH", publishTime="2026-01-10T16:00:00Z",
        startTime=datetime(2026, 1, 10, 15, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10", settlementPeriod=32,
        fuelType="WIND", generation=6000.0,
    )
    # Hour 3: Neither half exists

    actuals, stats = aggregate_hourly_actuals(
        target_hours=[t_hour1, t_hour2, t_hour3],
        actual_records=[rec_h1_first, rec_h2_second],
    )

    assert actuals[t_hour1].is_complete is False
    assert actuals[t_hour1].generation_mw is None
    assert "Second half-hour" in actuals[t_hour1].missing_reason

    assert actuals[t_hour2].is_complete is False
    assert actuals[t_hour2].generation_mw is None
    assert "First half-hour" in actuals[t_hour2].missing_reason

    assert actuals[t_hour3].is_complete is False
    assert actuals[t_hour3].generation_mw is None
    assert "Both half-hour" in actuals[t_hour3].missing_reason

    assert stats.incomplete_hourly_actuals == 3
    assert stats.complete_hourly_actuals == 0
    assert stats.missing_first_interval == 1
    assert stats.missing_second_interval == 1
    assert stats.missing_both_intervals == 1


# 12. Null generation handling in actuals
def test_null_generation_handled_safely():
    t_hour = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)

    # One period has null generation
    rec1 = FuelHHRecord(
        dataset="FUELHH", publishTime="2026-01-10T14:30:00Z",
        startTime=t_hour, settlementDate="2026-01-10",
        settlementPeriod=29, fuelType="WIND", generation=None,
    )
    rec2 = FuelHHRecord(
        dataset="FUELHH", publishTime="2026-01-10T15:00:00Z",
        startTime=datetime(2026, 1, 10, 14, 30, tzinfo=timezone.utc),
        settlementDate="2026-01-10", settlementPeriod=30,
        fuelType="WIND", generation=7000.0,
    )

    actuals, stats = aggregate_hourly_actuals(
        target_hours=[t_hour],
        actual_records=[rec1, rec2],
    )

    # Invariant: Never replace None with 0.0; mark as incomplete
    assert actuals[t_hour].is_complete is False
    assert actuals[t_hour].generation_mw is None
    assert stats.has_null_generation == 1


# Non-wind fuel types ignored
def test_non_wind_fuel_type_ignored():
    t_hour = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    rec_ccgt = FuelHHRecord(
        dataset="FUELHH", publishTime="2026-01-10T14:30:00Z",
        startTime=t_hour, settlementDate="2026-01-10",
        settlementPeriod=29, fuelType="CCGT", generation=15000.0,
    )

    actuals, stats = aggregate_hourly_actuals(
        target_hours=[t_hour],
        actual_records=[rec_ccgt],
        fuel_type="WIND",
    )

    assert actuals[t_hour].is_complete is False
    assert stats.complete_hourly_actuals == 0
