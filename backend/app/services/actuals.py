"""
app/services/actuals.py

Domain service for aligning half-hourly actual generation observations (FUELHH)
with hourly forecast target intervals (WINDFOR).

Aggregation Convention:
- WINDFOR forecasts represent expected wind generation over 60-minute target intervals.
- FUELHH actuals report average generation (MW) over 30-minute settlement periods.
- For each target hour starting at timestamp t, the hourly actual generation is computed
  as the arithmetic mean of the two consecutive 30-minute settlement periods:
      Actual_hour(t) = (Actual(t) + Actual(t + 30min)) / 2.0
- Because both settlement periods represent equal 30-minute intervals, the arithmetic mean
  preserves both average power (MW) and total energy volume (MWh).

Integrity Rules:
- Both observations must exist and have fuelType == 'WIND'.
- If either 30-minute observation is missing or has null generation, the hour is marked
  incomplete and excluded from metric calculations.
- Missing values are never imputed with zero or synthetically filled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from app.schemas.elexon import ensure_utc_datetime


@dataclass(frozen=True)
class HourlyActual:
    """Represents an aggregated hourly actual generation observation."""
    target_start_utc: datetime
    generation_mw: Optional[float]
    first_half_mw: Optional[float]
    second_half_mw: Optional[float]
    is_complete: bool
    interval_count: int  # Must be 2 for a complete hourly actual
    missing_reason: Optional[str] = None


@dataclass(frozen=True)
class ActualsAlignmentStats:
    """Coverage statistics for actual generation alignment."""
    total_target_hours_evaluated: int
    complete_hourly_actuals: int
    incomplete_hourly_actuals: int
    missing_both_intervals: int
    missing_first_interval: int
    missing_second_interval: int
    has_null_generation: int


def aggregate_hourly_actuals(
    target_hours: list[datetime],
    actual_records: list[Any],
    fuel_type: str = "WIND",
) -> tuple[dict[datetime, HourlyActual], ActualsAlignmentStats]:
    """
    Given a list of hourly target start times and a list of half-hourly actual records,
    aggregate the two half-hours into an hourly average generation value.
    
    Parameters:
        target_hours: List of hourly target start timestamps (UTC).
        actual_records: Iterable of ActualObservation or FuelHHRecord objects.
        fuel_type: Target fuel type filter (default: "WIND").
        
    Returns:
        tuple of (hourly_actuals_by_target, alignment_stats)
    """
    # Index actual records by (start_time_utc, fuel_type)
    actuals_by_key: dict[tuple[datetime, str], Any] = {}
    for rec in actual_records:
        st = getattr(rec, "start_time_utc", None) or getattr(rec, "startTime", None)
        ft = getattr(rec, "fuel_type", None) or getattr(rec, "fuelType", None)
        if st is None or ft != fuel_type:
            continue
        st_utc = ensure_utc_datetime(st)
        actuals_by_key[(st_utc, fuel_type)] = rec

    hourly_actuals: dict[datetime, HourlyActual] = {}
    complete_count = 0
    incomplete_count = 0
    missing_both_count = 0
    missing_first_count = 0
    missing_second_count = 0
    null_gen_count = 0

    for t_hour in sorted(set(ensure_utc_datetime(t) for t in target_hours)):
        t_first = t_hour
        t_second = t_hour + timedelta(minutes=30)

        rec_first = actuals_by_key.get((t_first, fuel_type))
        rec_second = actuals_by_key.get((t_second, fuel_type))

        # Check existence
        if rec_first is None and rec_second is None:
            missing_both_count += 1
            incomplete_count += 1
            hourly_actuals[t_hour] = HourlyActual(
                target_start_utc=t_hour,
                generation_mw=None,
                first_half_mw=None,
                second_half_mw=None,
                is_complete=False,
                interval_count=0,
                missing_reason="Both half-hour settlement periods are missing from actuals",
            )
            continue

        if rec_first is None:
            missing_first_count += 1
            incomplete_count += 1
            gen_sec = getattr(rec_second, "generation_mw", getattr(rec_second, "generation", None))
            hourly_actuals[t_hour] = HourlyActual(
                target_start_utc=t_hour,
                generation_mw=None,
                first_half_mw=None,
                second_half_mw=float(gen_sec) if gen_sec is not None else None,
                is_complete=False,
                interval_count=1,
                missing_reason="First half-hour settlement period (t+00m) is missing",
            )
            continue

        if rec_second is None:
            missing_second_count += 1
            incomplete_count += 1
            gen_fst = getattr(rec_first, "generation_mw", getattr(rec_first, "generation", None))
            hourly_actuals[t_hour] = HourlyActual(
                target_start_utc=t_hour,
                generation_mw=None,
                first_half_mw=float(gen_fst) if gen_fst is not None else None,
                second_half_mw=None,
                is_complete=False,
                interval_count=1,
                missing_reason="Second half-hour settlement period (t+30m) is missing",
            )
            continue

        # Both records exist, check for null generation values
        gen_1 = getattr(rec_first, "generation_mw", getattr(rec_first, "generation", None))
        gen_2 = getattr(rec_second, "generation_mw", getattr(rec_second, "generation", None))

        if gen_1 is None or gen_2 is None:
            null_gen_count += 1
            incomplete_count += 1
            hourly_actuals[t_hour] = HourlyActual(
                target_start_utc=t_hour,
                generation_mw=None,
                first_half_mw=float(gen_1) if gen_1 is not None else None,
                second_half_mw=float(gen_2) if gen_2 is not None else None,
                is_complete=False,
                interval_count=2,
                missing_reason="One or both half-hour settlement periods contain null generation",
            )
            continue

        # Complete and valid: compute arithmetic mean
        val_1 = float(gen_1)
        val_2 = float(gen_2)
        mean_generation = (val_1 + val_2) / 2.0
        complete_count += 1

        hourly_actuals[t_hour] = HourlyActual(
            target_start_utc=t_hour,
            generation_mw=mean_generation,
            first_half_mw=val_1,
            second_half_mw=val_2,
            is_complete=True,
            interval_count=2,
            missing_reason=None,
        )

    stats = ActualsAlignmentStats(
        total_target_hours_evaluated=len(target_hours),
        complete_hourly_actuals=complete_count,
        incomplete_hourly_actuals=incomplete_count,
        missing_both_intervals=missing_both_count,
        missing_first_interval=missing_first_count,
        missing_second_interval=missing_second_count,
        has_null_generation=null_gen_count,
    )

    return hourly_actuals, stats
