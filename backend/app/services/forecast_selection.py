"""
app/services/forecast_selection.py

Domain service for selecting the operational day-ahead wind generation forecast
for each target delivery interval without future data leakage.

Key Invariants:
1. Target start time is interpreted in Europe/London to derive the local delivery date.
2. The decision date is strictly defined as (delivery_date - 1 day) in Europe/London.
3. The cutoff timestamp is constructed on the decision date at cutoff_time in Europe/London,
   then converted to UTC for strict comparison: publish_time_utc <= cutoff_utc.
4. The latest eligible published version (max publish_time_utc <= cutoff_utc) is selected.
5. Post-cutoff forecasts (publish_time_utc > cutoff_utc) are strictly ineligible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.schemas.elexon import ensure_utc_datetime

LONDON_TZ = ZoneInfo("Europe/London")
DEFAULT_CUTOFF_TIME = time(10, 0)


@dataclass(frozen=True)
class SelectedForecast:
    """Represents a validated, cutoff-filtered forecast for an hourly target interval."""
    target_start_utc: datetime
    publish_time_utc: datetime
    cutoff_time_utc: datetime
    decision_date: date
    delivery_date: date
    generation_mw: Optional[float]
    horizon_hours: float  # Elapsed time: (target_start_utc - publish_time_utc) in hours
    dataset: str = "WINDFOR"


@dataclass(frozen=True)
class ForecastSelectionStats:
    """Diagnostic coverage statistics for the forecast selection process."""
    requested_decision_start: date
    requested_decision_end: date
    cutoff_time: time
    total_candidate_records: int
    unique_target_hours: int
    targets_in_decision_range: int
    targets_with_eligible_forecast: int
    targets_missing_eligible_forecast: int
    missing_target_hours: list[datetime]


def get_delivery_and_decision_dates(target_start_utc: datetime) -> tuple[date, date]:
    """
    Given a UTC target start time, convert to Europe/London local time:
    - delivery_date is the calendar date of target delivery in Europe/London.
    - decision_date is (delivery_date - 1 day) in Europe/London.
    """
    utc_dt = ensure_utc_datetime(target_start_utc)
    local_dt = utc_dt.astimezone(LONDON_TZ)
    delivery_date = local_dt.date()
    decision_date = delivery_date - timedelta(days=1)
    return delivery_date, decision_date


def compute_cutoff_utc(decision_date: date, cutoff_time: time = DEFAULT_CUTOFF_TIME) -> datetime:
    """
    Construct the market decision cutoff in Europe/London and convert to UTC.
    Handles BST/GMT transitions seamlessly via zoneinfo.
    """
    cutoff_local = datetime.combine(decision_date, cutoff_time, tzinfo=LONDON_TZ)
    return cutoff_local.astimezone(timezone.utc)


def select_day_ahead_forecasts(
    forecast_records: list[Any],
    decision_date_from: date,
    decision_date_to: date,
    cutoff_time: time = DEFAULT_CUTOFF_TIME,
) -> tuple[dict[datetime, SelectedForecast], ForecastSelectionStats]:
    """
    Pure domain function to select the day-ahead forecast for each target hour.
    
    Parameters:
        forecast_records: Iterable of objects with attributes (start_time_utc/startTime,
                          publish_time_utc/publishTime, generation_mw/generation).
        decision_date_from: Inclusive start of decision-date evaluation range.
        decision_date_to: Inclusive end of decision-date evaluation range.
        cutoff_time: Cutoff time in Europe/London (default: 10:00).
        
    Returns:
        tuple of (selected_forecasts_by_target_start, stats)
    """
    if decision_date_from > decision_date_to:
        raise ValueError(
            f"decision_date_from ({decision_date_from}) cannot be after decision_date_to ({decision_date_to})"
        )

    # 1. Group candidate versions by target start time
    versions_by_target: dict[datetime, list[Any]] = {}
    total_candidates = len(forecast_records)

    for rec in forecast_records:
        st = getattr(rec, "start_time_utc", None) or getattr(rec, "startTime", None)
        if st is None:
            continue
        st_utc = ensure_utc_datetime(st)
        if st_utc not in versions_by_target:
            versions_by_target[st_utc] = []
        versions_by_target[st_utc].append(rec)

    # 2. Iterate through each target hour and select latest version prior to cutoff
    selected_by_target: dict[datetime, SelectedForecast] = {}
    missing_targets: list[datetime] = []
    targets_in_range_count = 0

    for st_utc in sorted(versions_by_target.keys()):
        delivery_date, decision_date = get_delivery_and_decision_dates(st_utc)

        # Filter by decision-date range (inclusive)
        if not (decision_date_from <= decision_date <= decision_date_to):
            continue

        targets_in_range_count += 1
        cutoff_utc = compute_cutoff_utc(decision_date, cutoff_time)

        # Candidate versions with publish_time <= cutoff_utc
        eligible_versions = []
        for rec in versions_by_target[st_utc]:
            pub = getattr(rec, "publish_time_utc", None) or getattr(rec, "publishTime", None)
            if pub is None:
                continue
            pub_utc = ensure_utc_datetime(pub)
            if pub_utc <= cutoff_utc:
                eligible_versions.append((pub_utc, rec))

        if not eligible_versions:
            missing_targets.append(st_utc)
            continue

        # Sort candidate versions by publish_time_utc descending
        eligible_versions.sort(key=lambda x: x[0], reverse=True)
        latest_pub_utc, latest_rec = eligible_versions[0]

        # Check for conflicting duplicate records at the exact same latest publish timestamp
        same_latest = [v for v in eligible_versions if v[0] == latest_pub_utc]
        if len(same_latest) > 1:
            gen_vals = {
                getattr(v[1], "generation_mw", getattr(v[1], "generation", None))
                for v in same_latest
            }
            if len(gen_vals) > 1:
                raise ValueError(
                    f"Conflicting generation values for target {st_utc} at publish time {latest_pub_utc}: {gen_vals}"
                )

        gen_mw = getattr(latest_rec, "generation_mw", getattr(latest_rec, "generation", None))
        horizon = (st_utc - latest_pub_utc).total_seconds() / 3600.0

        selected_by_target[st_utc] = SelectedForecast(
            target_start_utc=st_utc,
            publish_time_utc=latest_pub_utc,
            cutoff_time_utc=cutoff_utc,
            decision_date=decision_date,
            delivery_date=delivery_date,
            generation_mw=float(gen_mw) if gen_mw is not None else None,
            horizon_hours=horizon,
            dataset=getattr(latest_rec, "dataset", "WINDFOR"),
        )

    stats = ForecastSelectionStats(
        requested_decision_start=decision_date_from,
        requested_decision_end=decision_date_to,
        cutoff_time=cutoff_time,
        total_candidate_records=total_candidates,
        unique_target_hours=len(versions_by_target),
        targets_in_decision_range=targets_in_range_count,
        targets_with_eligible_forecast=len(selected_by_target),
        targets_missing_eligible_forecast=len(missing_targets),
        missing_target_hours=missing_targets,
    )

    return selected_by_target, stats
