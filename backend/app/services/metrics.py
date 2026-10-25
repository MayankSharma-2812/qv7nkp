"""
app/services/metrics.py

Domain service for calculating statistical forecast accuracy metrics.
Uses NumPy and pandas for deterministic vector calculations.

Error Definition:
    error_mw = forecast_generation_mw - actual_generation_mw

Interpretation:
- Positive error (error_mw > 0): OVER-FORECAST. Expected wind exceeds reality,
  leaving the utility short on physical volume and exposed to prompt market or imbalance costs.
- Negative error (error_mw < 0): UNDER-FORECAST. Actual wind exceeds forecast,
  potentially causing over-procurement from thermal plants.

Quantile Method:
- Uses numpy.quantile(..., method='linear') for reproducible percentile values (P50, P90, P95).

WAPE Handling:
- WAPE = sum(|error_mw|) / sum(actual_generation_mw)
- If sum(actual_generation_mw) == 0, WAPE is returned as None (undefined denominator).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.schemas.elexon import ensure_utc_datetime

LONDON_TZ = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class MatchedPair:
    """Represents a validated pair of day-ahead cutoff forecast and outturn hourly actual."""
    target_start_utc: datetime
    delivery_hour_local: int  # 0 to 23 in Europe/London
    publish_time_utc: datetime
    horizon_hours: float
    forecast_generation_mw: float
    actual_generation_mw: float
    error_mw: float  # forecast - actual
    absolute_error_mw: float  # |forecast - actual|


@dataclass(frozen=True)
class AggregateMetrics:
    """Statistical summary metrics for a collection of matched pairs."""
    sample_count: int
    mae_mw: Optional[float]
    rmse_mw: Optional[float]
    mean_bias_mw: Optional[float]
    p50_absolute_error_mw: Optional[float]
    p90_absolute_error_mw: Optional[float]
    p95_absolute_error_mw: Optional[float]
    wape: Optional[float]  # Weighted Absolute Percentage Error (fraction, e.g. 0.125 = 12.5%)
    total_forecast_energy_mwh: Optional[float]
    total_actual_energy_mwh: Optional[float]
    total_absolute_error_mwh: Optional[float]
    wape_unavailable_reason: Optional[str] = None


@dataclass(frozen=True)
class GroupedMetricRow:
    """Metrics calculated for a sub-group (e.g. delivery hour or horizon bucket)."""
    group_key: str
    sample_count: int
    mae_mw: Optional[float]
    rmse_mw: Optional[float]
    mean_bias_mw: Optional[float]
    wape: Optional[float]
    mean_forecast_mw: Optional[float]
    mean_actual_mw: Optional[float]


def calculate_aggregate_metrics(pairs: list[MatchedPair]) -> AggregateMetrics:
    """
    Calculate summary accuracy metrics from a list of MatchedPairs.
    Returns None for statistical metrics if pairs is empty.
    """
    if not pairs:
        return AggregateMetrics(
            sample_count=0,
            mae_mw=None,
            rmse_mw=None,
            mean_bias_mw=None,
            p50_absolute_error_mw=None,
            p90_absolute_error_mw=None,
            p95_absolute_error_mw=None,
            wape=None,
            total_forecast_energy_mwh=None,
            total_actual_energy_mwh=None,
            total_absolute_error_mwh=None,
            wape_unavailable_reason="No matched pairs available",
        )

    errors = np.array([p.error_mw for p in pairs], dtype=np.float64)
    abs_errors = np.array([p.absolute_error_mw for p in pairs], dtype=np.float64)
    actuals = np.array([p.actual_generation_mw for p in pairs], dtype=np.float64)
    forecasts = np.array([p.forecast_generation_mw for p in pairs], dtype=np.float64)

    n = len(pairs)
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    bias = float(np.mean(errors))

    # Quantiles using linear interpolation (NumPy default)
    quantiles = np.quantile(abs_errors, [0.50, 0.90, 0.95], method="linear")
    p50, p90, p95 = float(quantiles[0]), float(quantiles[1]), float(quantiles[2])

    sum_actuals = float(np.sum(actuals))
    sum_abs_errors = float(np.sum(abs_errors))
    sum_forecasts = float(np.sum(forecasts))

    if sum_actuals > 0.0:
        wape = sum_abs_errors / sum_actuals
        wape_reason = None
    else:
        wape = None
        wape_reason = "Sum of actual generation is zero; WAPE denominator is undefined"

    return AggregateMetrics(
        sample_count=n,
        mae_mw=mae,
        rmse_mw=rmse,
        mean_bias_mw=bias,
        p50_absolute_error_mw=p50,
        p90_absolute_error_mw=p90,
        p95_absolute_error_mw=p95,
        wape=wape,
        total_forecast_energy_mwh=sum_forecasts,
        total_actual_energy_mwh=sum_actuals,
        total_absolute_error_mwh=sum_abs_errors,
        wape_unavailable_reason=wape_reason,
    )


def calculate_metrics_by_delivery_hour(pairs: list[MatchedPair]) -> list[GroupedMetricRow]:
    """Group matched pairs by Europe/London delivery hour of day (0 to 23)."""
    if not pairs:
        return []

    df = pd.DataFrame([
        {
            "hour": p.delivery_hour_local,
            "error": p.error_mw,
            "abs_error": p.absolute_error_mw,
            "forecast": p.forecast_generation_mw,
            "actual": p.actual_generation_mw,
        }
        for p in pairs
    ])

    grouped = []
    for hour in range(24):
        sub = df[df["hour"] == hour]
        if sub.empty:
            continue
        n = len(sub)
        mae = float(sub["abs_error"].mean())
        rmse = float(np.sqrt((sub["error"] ** 2).mean()))
        bias = float(sub["error"].mean())
        sum_act = float(sub["actual"].sum())
        sum_abs = float(sub["abs_error"].sum())
        wape = (sum_abs / sum_act) if sum_act > 0 else None

        grouped.append(
            GroupedMetricRow(
                group_key=f"{hour:02d}:00",
                sample_count=n,
                mae_mw=mae,
                rmse_mw=rmse,
                mean_bias_mw=bias,
                wape=wape,
                mean_forecast_mw=float(sub["forecast"].mean()),
                mean_actual_mw=float(sub["actual"].mean()),
            )
        )

    return grouped


def assign_horizon_bucket(hours: float) -> str:
    """Categorize forecast lead time into standard operational buckets."""
    if hours < 14.0:
        return "< 14h"
    elif hours < 18.0:
        return "14h - 18h"
    elif hours < 24.0:
        return "18h - 24h"
    elif hours < 30.0:
        return "24h - 30h"
    elif hours < 36.0:
        return "30h - 36h"
    else:
        return ">= 36h"


def calculate_metrics_by_horizon(pairs: list[MatchedPair]) -> list[GroupedMetricRow]:
    """Group matched pairs by forecast horizon buckets."""
    if not pairs:
        return []

    bucket_order = ["< 14h", "14h - 18h", "18h - 24h", "24h - 30h", "30h - 36h", ">= 36h"]
    df = pd.DataFrame([
        {
            "bucket": assign_horizon_bucket(p.horizon_hours),
            "error": p.error_mw,
            "abs_error": p.absolute_error_mw,
            "forecast": p.forecast_generation_mw,
            "actual": p.actual_generation_mw,
        }
        for p in pairs
    ])

    grouped = []
    for bucket in bucket_order:
        sub = df[df["bucket"] == bucket]
        if sub.empty:
            continue
        n = len(sub)
        mae = float(sub["abs_error"].mean())
        rmse = float(np.sqrt((sub["error"] ** 2).mean()))
        bias = float(sub["error"].mean())
        sum_act = float(sub["actual"].sum())
        sum_abs = float(sub["abs_error"].sum())
        wape = (sum_abs / sum_act) if sum_act > 0 else None

        grouped.append(
            GroupedMetricRow(
                group_key=bucket,
                sample_count=n,
                mae_mw=mae,
                rmse_mw=rmse,
                mean_bias_mw=bias,
                wape=wape,
                mean_forecast_mw=float(sub["forecast"].mean()),
                mean_actual_mw=float(sub["actual"].mean()),
            )
        )

    return grouped
