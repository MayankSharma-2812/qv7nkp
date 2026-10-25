"""
tests/services/test_forecast_selection.py

Unit tests for day-ahead forecast selection and temporal anti-leakage:
1. The newest forecast before the cutoff is selected.
2. A forecast exactly at the cutoff is eligible.
3. A forecast one second after the cutoff is ineligible.
4. A much later forecast is never selected accidentally.
5. Multiple forecast versions are selected independently for each target startTime.
6. No eligible forecast is handled correctly.
7. UTC cutoff conversion for Europe/London (GMT vs BST).
8. Conversion of decision dates and delivery dates.
9. Inclusive decision-date range boundaries.
19. Consistent UTC-aware timestamps.
20. Duplicate and conflicting forecast keys.
"""

from datetime import date, datetime, time, timedelta, timezone
import pytest

from app.schemas.elexon import WindforRecord
from app.services.forecast_selection import (
    DEFAULT_CUTOFF_TIME,
    compute_cutoff_utc,
    get_delivery_and_decision_dates,
    select_day_ahead_forecasts,
)


# 1, 2, 3, 4: Strict Cutoff Anti-Leakage
def test_cutoff_anti_leakage_and_boundary_conditions():
    """
    Target delivery: 2026-01-05 14:00 Europe/London.
    Decision date: 2026-01-04.
    Cutoff time: 10:00 Europe/London -> 2026-01-04 10:00:00 UTC.
    """
    target_start = datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)
    cutoff_utc = datetime(2026, 1, 4, 10, 0, 0, tzinfo=timezone.utc)

    # Version 1: 08:00 (Eligible, earlier)
    v1 = WindforRecord(
        dataset="WINDFOR",
        publishTime=cutoff_utc - timedelta(hours=2),
        startTime=target_start,
        generation=8000.0,
    )
    # Version 2: Exactly at cutoff 10:00:00 (Eligible, newest)
    v2_at_cutoff = WindforRecord(
        dataset="WINDFOR",
        publishTime=cutoff_utc,
        startTime=target_start,
        generation=8500.0,
    )
    # Version 3: Exactly 1 second after cutoff 10:00:01 (Ineligible!)
    v3_one_sec_after = WindforRecord(
        dataset="WINDFOR",
        publishTime=cutoff_utc + timedelta(seconds=1),
        startTime=target_start,
        generation=9000.0,
    )
    # Version 4: Much later afternoon update (Ineligible!)
    v4_much_later = WindforRecord(
        dataset="WINDFOR",
        publishTime=cutoff_utc + timedelta(hours=6),
        startTime=target_start,
        generation=9500.0,
    )

    records = [v1, v2_at_cutoff, v3_one_sec_after, v4_much_later]

    selected, stats = select_day_ahead_forecasts(
        forecast_records=records,
        decision_date_from=date(2026, 1, 4),
        decision_date_to=date(2026, 1, 4),
        cutoff_time=time(10, 0),
    )

    assert target_start in selected
    chosen = selected[target_start]
    # Invariant: v2_at_cutoff (8500.0) MUST be selected; v3 and v4 MUST NOT be selected
    assert chosen.publish_time_utc == cutoff_utc
    assert chosen.generation_mw == 8500.0
    assert chosen.publish_time_utc <= chosen.cutoff_time_utc


def test_forecast_one_second_after_cutoff_is_excluded():
    target_start = datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)
    cutoff_utc = datetime(2026, 1, 4, 10, 0, 0, tzinfo=timezone.utc)

    v_before = WindforRecord(
        dataset="WINDFOR",
        publishTime=cutoff_utc - timedelta(seconds=1),
        startTime=target_start,
        generation=7500.0,
    )
    v_one_sec_after = WindforRecord(
        dataset="WINDFOR",
        publishTime=cutoff_utc + timedelta(seconds=1),
        startTime=target_start,
        generation=9999.0,
    )

    selected, stats = select_day_ahead_forecasts(
        forecast_records=[v_before, v_one_sec_after],
        decision_date_from=date(2026, 1, 4),
        decision_date_to=date(2026, 1, 4),
        cutoff_time=time(10, 0),
    )

    chosen = selected[target_start]
    assert chosen.publish_time_utc == cutoff_utc - timedelta(seconds=1)
    assert chosen.generation_mw == 7500.0


# 5. Multiple forecast versions selected independently for each target startTime
def test_independent_selection_per_target_hour():
    t1 = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 5, 11, 0, tzinfo=timezone.utc)

    records = [
        # Target 1 publications
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T07:00:00Z", startTime=t1, generation=5000),
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T09:30:00Z", startTime=t1, generation=5500),
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T11:00:00Z", startTime=t1, generation=6000),
        # Target 2 publications
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T08:00:00Z", startTime=t2, generation=7000),
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T09:00:00Z", startTime=t2, generation=7200),
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T12:00:00Z", startTime=t2, generation=7500),
    ]

    selected, stats = select_day_ahead_forecasts(
        forecast_records=records,
        decision_date_from=date(2026, 1, 4),
        decision_date_to=date(2026, 1, 4),
        cutoff_time=time(10, 0),
    )

    assert selected[t1].generation_mw == 5500.0
    assert selected[t1].publish_time_utc == datetime(2026, 1, 4, 9, 30, tzinfo=timezone.utc)
    assert selected[t2].generation_mw == 7200.0
    assert selected[t2].publish_time_utc == datetime(2026, 1, 4, 9, 0, tzinfo=timezone.utc)


# 6. No eligible forecast handled correctly
def test_missing_eligible_forecast_handling():
    target_start = datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)
    # Only a post-cutoff publication exists
    v_late = WindforRecord(
        dataset="WINDFOR",
        publishTime="2026-01-04T15:00:00Z",
        startTime=target_start,
        generation=9000.0,
    )

    selected, stats = select_day_ahead_forecasts(
        forecast_records=[v_late],
        decision_date_from=date(2026, 1, 4),
        decision_date_to=date(2026, 1, 4),
        cutoff_time=time(10, 0),
    )

    assert target_start not in selected
    assert stats.targets_missing_eligible_forecast == 1
    assert stats.missing_target_hours == [target_start]


# 7. UTC cutoff conversion for Europe/London (GMT vs BST)
def test_cutoff_timezone_conversion_gmt_and_bst():
    # Winter (GMT: Europe/London is UTC+0)
    winter_date = date(2026, 1, 15)
    cutoff_winter = compute_cutoff_utc(winter_date, time(10, 0))
    assert cutoff_winter == datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)

    # Summer (BST: Europe/London is UTC+1)
    summer_date = date(2026, 7, 15)
    cutoff_summer = compute_cutoff_utc(summer_date, time(10, 0))
    # 10:00 BST == 09:00 UTC
    assert cutoff_summer == datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)


# 8. Conversion of decision dates and delivery dates
def test_delivery_and_decision_date_derivation():
    # Target delivery in winter (GMT)
    st1 = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
    del_d, dec_d = get_delivery_and_decision_dates(st1)
    assert del_d == date(2026, 1, 10)
    assert dec_d == date(2026, 1, 9)

    # Late night delivery (23:00 GMT)
    st2 = datetime(2026, 1, 10, 23, 0, tzinfo=timezone.utc)
    del_d, dec_d = get_delivery_and_decision_dates(st2)
    assert del_d == date(2026, 1, 10)
    assert dec_d == date(2026, 1, 9)


# 9. Inclusive decision-date range boundaries
def test_inclusive_decision_date_boundaries():
    t_jan1_decision = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)  # Decision Jan 1
    t_jan31_decision = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc) # Decision Jan 31
    t_feb1_decision = datetime(2026, 2, 2, 12, 0, tzinfo=timezone.utc)  # Decision Feb 1 (excluded)

    records = [
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-01T09:00:00Z", startTime=t_jan1_decision, generation=1000),
        WindforRecord(dataset="WINDFOR", publishTime="2026-01-31T09:00:00Z", startTime=t_jan31_decision, generation=2000),
        WindforRecord(dataset="WINDFOR", publishTime="2026-02-01T09:00:00Z", startTime=t_feb1_decision, generation=3000),
    ]

    selected, stats = select_day_ahead_forecasts(
        forecast_records=records,
        decision_date_from=date(2026, 1, 1),
        decision_date_to=date(2026, 1, 31),
        cutoff_time=time(10, 0),
    )

    assert t_jan1_decision in selected
    assert t_jan31_decision in selected
    assert t_feb1_decision not in selected
    assert stats.targets_in_decision_range == 2


# 19. Consistent UTC-aware timestamps
def test_consistent_utc_aware_timestamps():
    target = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    rec = WindforRecord(dataset="WINDFOR", publishTime="2026-01-04T09:00:00Z", startTime=target, generation=5000)

    selected, stats = select_day_ahead_forecasts(
        forecast_records=[rec],
        decision_date_from=date(2026, 1, 4),
        decision_date_to=date(2026, 1, 4),
    )

    chosen = selected[target]
    assert chosen.target_start_utc.tzinfo == timezone.utc
    assert chosen.publish_time_utc.tzinfo == timezone.utc
    assert chosen.cutoff_time_utc.tzinfo == timezone.utc


# 20. Duplicate and conflicting forecast keys
def test_conflicting_duplicate_forecast_keys_raises_error():
    target = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    pub_time = datetime(2026, 1, 4, 9, 0, tzinfo=timezone.utc)

    # Identical publish time and start time, but conflicting generation values
    r1 = WindforRecord(dataset="WINDFOR", publishTime=pub_time, startTime=target, generation=5000)
    r2 = WindforRecord(dataset="WINDFOR", publishTime=pub_time, startTime=target, generation=6000)

    with pytest.raises(ValueError, match="Conflicting generation values"):
        select_day_ahead_forecasts(
            forecast_records=[r1, r2],
            decision_date_from=date(2026, 1, 4),
            decision_date_to=date(2026, 1, 4),
        )
