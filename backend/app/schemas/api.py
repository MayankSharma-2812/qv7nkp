"""
app/schemas/api.py

Pydantic v2 schemas for FastAPI request validation and response contracts.
Guarantees consistent JSON serialization, timezone-aware UTC timestamps,
and strict January 2026 decision-date boundaries.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

JAN_2026_START = date(2026, 1, 1)
JAN_2026_END = date(2026, 1, 31)


class HealthResponse(BaseModel):
    """Liveness probe response."""
    status: str = "ok"
    service: str = "gridbricks-api"
    version: str = "1.0.0"


class ReadyResponse(BaseModel):
    """Readiness probe response indicating database health."""
    status: str = "ready"
    database: str
    actual_observations_count: int
    forecast_observations_count: int


class ErrorDetail(BaseModel):
    """Standardized API error response body."""
    error_code: str
    message: str
    request_id: Optional[str] = None


class ForecastDecisionItem(BaseModel):
    """Individual hourly forecast and outturn for a single target interval."""
    model_config = ConfigDict(extra="ignore")

    target_start_utc: datetime
    delivery_hour_local: int
    publish_time_utc: Optional[datetime] = None
    horizon_hours: Optional[float] = None
    forecast_generation_mw: Optional[float] = None
    actual_generation_mw: Optional[float] = None
    error_mw: Optional[float] = None
    absolute_error_mw: Optional[float] = None
    is_actual_complete: bool = False
    status: str = "MATCHED"  # MATCHED, MISSING_FORECAST, MISSING_ACTUAL


class DecisionForecastResponse(BaseModel):
    """Response for GET /api/v1/decisions/forecast."""
    decision_date: date
    delivery_date: date
    cutoff_time: str
    cutoff_timezone: str
    cutoff_time_utc: datetime
    total_hours: int
    matched_hours: int
    forecasts: list[ForecastDecisionItem]


class SeriesDataPoint(BaseModel):
    """Time-series data point for chart visualization."""
    target_start_utc: datetime
    delivery_date: date
    delivery_hour_local: int
    publish_time_utc: Optional[datetime] = None
    forecast_mw: Optional[float] = None
    actual_mw: Optional[float] = None
    error_mw: Optional[float] = None


class ForecastSeriesResponse(BaseModel):
    """Response for GET /api/v1/forecasts/series."""
    decision_date_from: date
    decision_date_to: date
    delivery_date_from: date
    delivery_date_to: date
    cutoff_time: str
    cutoff_timezone: str
    total_points: int
    matched_points: int
    series: list[SeriesDataPoint]


class CoverageStats(BaseModel):
    """Data quality and coverage diagnostics."""
    total_expected_target_hours: int
    targets_with_eligible_forecast: int
    targets_missing_eligible_forecast: int
    targets_with_complete_actual: int
    targets_missing_or_incomplete_actual: int
    matched_pairs_evaluated: int
    coverage_percentage: float
    excluded_targets_count: int


class AccuracySummaryResponse(BaseModel):
    """Response for GET /api/v1/accuracy/summary."""
    decision_date_from: date
    decision_date_to: date
    delivery_date_from: date
    delivery_date_to: date
    cutoff_time: str
    cutoff_timezone: str
    sample_count: int
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    mean_bias_mw: Optional[float] = None
    p50_absolute_error_mw: Optional[float] = None
    p90_absolute_error_mw: Optional[float] = None
    p95_absolute_error_mw: Optional[float] = None
    wape: Optional[float] = None
    wape_percentage: Optional[float] = None
    total_forecast_energy_mwh: Optional[float] = None
    total_actual_energy_mwh: Optional[float] = None
    total_absolute_error_mwh: Optional[float] = None
    wape_unavailable_reason: Optional[str] = None
    coverage: CoverageStats


class DiurnalMetricItem(BaseModel):
    """Diurnal hourly metric item."""
    hour_local: str
    sample_count: int
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    mean_bias_mw: Optional[float] = None
    wape: Optional[float] = None
    mean_forecast_mw: Optional[float] = None
    mean_actual_mw: Optional[float] = None


class DiurnalResponse(BaseModel):
    """Response for GET /api/v1/accuracy/diurnal."""
    decision_date_from: date
    decision_date_to: date
    cutoff_time: str
    cutoff_timezone: str
    diurnal_profile: list[DiurnalMetricItem]


class HorizonMetricItem(BaseModel):
    """Metric item grouped by forecast horizon bucket."""
    horizon_bucket: str
    sample_count: int
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    mean_bias_mw: Optional[float] = None
    wape: Optional[float] = None
    mean_forecast_mw: Optional[float] = None
    mean_actual_mw: Optional[float] = None


class DistributionResponse(BaseModel):
    """Response for GET /api/v1/accuracy/distribution."""
    decision_date_from: date
    decision_date_to: date
    cutoff_time: str
    cutoff_timezone: str
    horizon_groups: list[HorizonMetricItem]
    error_quantiles: dict[str, Optional[float]]
