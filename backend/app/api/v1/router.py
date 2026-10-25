"""
app/api/v1/router.py

Version 1 API routes for Gridbricks Wind Day-Ahead Forecast Evaluation Portal.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import (
    DEFAULT_CUTOFF_STR,
    get_db,
    parse_and_validate_cutoff,
    parse_and_validate_decision_range,
    validate_decision_date_in_scope,
)
from app.db.session import get_default_db_url
from app.repositories.elexon_repository import ElexonRepository
from app.schemas.api import (
    AccuracySummaryResponse,
    CoverageStats,
    DecisionForecastResponse,
    DiurnalMetricItem,
    DiurnalResponse,
    DistributionResponse,
    ForecastDecisionItem,
    ForecastSeriesResponse,
    HealthResponse,
    HorizonMetricItem,
    ReadyResponse,
    SeriesDataPoint,
)
from app.services.actuals import aggregate_hourly_actuals
from app.services.evaluation import ForecastEvaluationService
from app.services.forecast_selection import (
    LONDON_TZ,
    compute_cutoff_utc,
    select_day_ahead_forecasts,
)

api_router = APIRouter()
eval_service = ForecastEvaluationService()
repo = ElexonRepository()

# 5 minutes cache header for historical immutable responses
CACHE_CONTROL_HISTORICAL = "public, max-age=300"


@api_router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health() -> HealthResponse:
    """Liveness probe. Does not depend on database availability."""
    return HealthResponse(status="ok", service="gridbricks-api", version="1.0.0")


@api_router.get("/ready", response_model=ReadyResponse, tags=["System"])
def get_ready(db: Session = Depends(get_db)) -> ReadyResponse:
    """Readiness probe. Verifies database connectivity and required tables."""
    try:
        # Check actual table counts
        actuals_count = db.execute(text("SELECT COUNT(*) FROM actual_observations")).scalar()
        forecasts_count = db.execute(text("SELECT COUNT(*) FROM forecast_observations")).scalar()

        if actuals_count is None or forecasts_count is None:
            raise RuntimeError("Database queries returned null counts")

        return ReadyResponse(
            status="ready",
            database=get_default_db_url(),
            actual_observations_count=int(actuals_count),
            forecast_observations_count=int(forecasts_count),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database readiness check failed: {e}",
        )


@api_router.get(
    "/decisions/forecast",
    response_model=DecisionForecastResponse,
    tags=["Decisions"],
)
def get_decision_forecast(
    response: Response,
    decision_date: str = Query(
        ...,
        description="Decision date in YYYY-MM-DD format (must be within Jan 2026)",
        examples=["2026-01-05"],
    ),
    cutoff: str = Query(
        DEFAULT_CUTOFF_STR,
        description="Cutoff time in Europe/London (HH:MM or HH:MM:SS)",
        examples=["10:00"],
    ),
    db: Session = Depends(get_db),
) -> DecisionForecastResponse:
    """
    Get day-ahead operational forecasts and actuals for the delivery day following decision_date.
    Strictly filters out any forecast published after cutoff on the decision date.
    """
    try:
        parsed_date = date.fromisoformat(decision_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision_date format '{decision_date}'. Expected YYYY-MM-DD.",
        )

    validate_decision_date_in_scope(parsed_date, "decision_date")
    cutoff_time = parse_and_validate_cutoff(cutoff)
    delivery_date = parsed_date + timedelta(days=1)
    cutoff_utc = compute_cutoff_utc(parsed_date, cutoff_time)

    # Delivery day hours: 00:00 to 23:00 in Europe/London
    target_hours: list[datetime] = [
        datetime.combine(delivery_date, time(h, 0), tzinfo=LONDON_TZ).astimezone(timezone.utc)
        for h in range(24)
    ]

    start_min_utc = target_hours[0]
    start_max_utc = datetime.combine(delivery_date, time(23, 30), tzinfo=LONDON_TZ).astimezone(timezone.utc)

    raw_forecasts = repo.get_forecasts(db, start_time_from=start_min_utc, start_time_to=start_max_utc)
    raw_actuals = repo.get_actuals(db, start_time_from=start_min_utc, start_time_to=start_max_utc)

    selected_by_target, _ = select_day_ahead_forecasts(
        forecast_records=raw_forecasts,
        decision_date_from=parsed_date,
        decision_date_to=parsed_date,
        cutoff_time=cutoff_time,
    )

    hourly_actuals, _ = aggregate_hourly_actuals(
        target_hours=target_hours,
        actual_records=raw_actuals,
        fuel_type="WIND",
    )

    items: list[ForecastDecisionItem] = []
    matched_count = 0

    for t_utc in target_hours:
        local_hour = t_utc.astimezone(LONDON_TZ).hour
        f_rec = selected_by_target.get(t_utc)
        a_rec = hourly_actuals.get(t_utc)

        f_gen = f_rec.generation_mw if f_rec else None
        a_gen = a_rec.generation_mw if a_rec and a_rec.is_complete else None
        is_complete = a_rec.is_complete if a_rec else False

        err = (f_gen - a_gen) if (f_gen is not None and a_gen is not None) else None
        abs_err = abs(err) if err is not None else None

        if f_rec is None:
            item_status = "MISSING_FORECAST"
        elif not is_complete:
            item_status = "MISSING_ACTUAL"
        else:
            item_status = "MATCHED"
            matched_count += 1

        items.append(
            ForecastDecisionItem(
                target_start_utc=t_utc,
                delivery_hour_local=local_hour,
                publish_time_utc=f_rec.publish_time_utc if f_rec else None,
                horizon_hours=f_rec.horizon_hours if f_rec else None,
                forecast_generation_mw=f_gen,
                actual_generation_mw=a_gen,
                error_mw=err,
                absolute_error_mw=abs_err,
                is_actual_complete=is_complete,
                status=item_status,
            )
        )

    response.headers["Cache-Control"] = CACHE_CONTROL_HISTORICAL

    return DecisionForecastResponse(
        decision_date=parsed_date,
        delivery_date=delivery_date,
        cutoff_time=cutoff_time.isoformat(),
        cutoff_timezone="Europe/London",
        cutoff_time_utc=cutoff_utc,
        total_hours=24,
        matched_hours=matched_count,
        forecasts=items,
    )


@api_router.get(
    "/forecasts/series",
    response_model=ForecastSeriesResponse,
    tags=["Series"],
)
def get_forecast_series(
    response: Response,
    decision_date_from: Optional[str] = Query(None, description="Start decision date (YYYY-MM-DD)"),
    decision_date_to: Optional[str] = Query(None, description="End decision date (YYYY-MM-DD)"),
    cutoff: str = Query(DEFAULT_CUTOFF_STR, description="Cutoff time in Europe/London (HH:MM or HH:MM:SS)"),
    db: Session = Depends(get_db),
) -> ForecastSeriesResponse:
    """Time-series of cutoff forecasts and actuals across the decision date range."""
    d_from, d_to = parse_and_validate_decision_range(decision_date_from, decision_date_to)
    cutoff_time = parse_and_validate_cutoff(cutoff)

    result = eval_service.evaluate(
        session=db,
        decision_date_from=d_from,
        decision_date_to=d_to,
        cutoff_time=cutoff_time,
    )

    # Generate series points for all evaluated targets
    delivery_date_from = d_from + timedelta(days=1)
    delivery_date_to = d_to + timedelta(days=1)

    all_targets: list[datetime] = []
    curr = delivery_date_from
    while curr <= delivery_date_to:
        for h in range(24):
            dt_local = datetime.combine(curr, time(h, 0), tzinfo=LONDON_TZ)
            all_targets.append(dt_local.astimezone(timezone.utc))
        curr += timedelta(days=1)

    start_min_utc = all_targets[0]
    start_max_utc = datetime.combine(delivery_date_to, time(23, 30), tzinfo=LONDON_TZ).astimezone(timezone.utc)

    raw_forecasts = repo.get_forecasts(db, start_time_from=start_min_utc, start_time_to=start_max_utc)
    raw_actuals = repo.get_actuals(db, start_time_from=start_min_utc, start_time_to=start_max_utc)

    selected_by_target, _ = select_day_ahead_forecasts(
        forecast_records=raw_forecasts,
        decision_date_from=d_from,
        decision_date_to=d_to,
        cutoff_time=cutoff_time,
    )
    hourly_actuals, _ = aggregate_hourly_actuals(
        target_hours=all_targets,
        actual_records=raw_actuals,
        fuel_type="WIND",
    )

    points: list[SeriesDataPoint] = []
    matched_count = 0

    for t_utc in all_targets:
        local_dt = t_utc.astimezone(LONDON_TZ)
        f_rec = selected_by_target.get(t_utc)
        a_rec = hourly_actuals.get(t_utc)

        f_gen = f_rec.generation_mw if f_rec else None
        a_gen = a_rec.generation_mw if a_rec and a_rec.is_complete else None
        err = (f_gen - a_gen) if (f_gen is not None and a_gen is not None) else None

        if f_gen is not None and a_gen is not None:
            matched_count += 1

        points.append(
            SeriesDataPoint(
                target_start_utc=t_utc,
                delivery_date=local_dt.date(),
                delivery_hour_local=local_dt.hour,
                publish_time_utc=f_rec.publish_time_utc if f_rec else None,
                forecast_mw=f_gen,
                actual_mw=a_gen,
                error_mw=err,
            )
        )

    response.headers["Cache-Control"] = CACHE_CONTROL_HISTORICAL

    return ForecastSeriesResponse(
        decision_date_from=d_from,
        decision_date_to=d_to,
        delivery_date_from=delivery_date_from,
        delivery_date_to=delivery_date_to,
        cutoff_time=cutoff_time.isoformat(),
        cutoff_timezone="Europe/London",
        total_points=len(points),
        matched_points=matched_count,
        series=points,
    )


@api_router.get(
    "/accuracy/summary",
    response_model=AccuracySummaryResponse,
    tags=["Accuracy"],
)
def get_accuracy_summary(
    response: Response,
    decision_date_from: Optional[str] = Query(None, description="Start decision date (YYYY-MM-DD)"),
    decision_date_to: Optional[str] = Query(None, description="End decision date (YYYY-MM-DD)"),
    cutoff: str = Query(DEFAULT_CUTOFF_STR, description="Cutoff time in Europe/London (HH:MM or HH:MM:SS)"),
    db: Session = Depends(get_db),
) -> AccuracySummaryResponse:
    """Summary error statistics and coverage diagnostics."""
    d_from, d_to = parse_and_validate_decision_range(decision_date_from, decision_date_to)
    cutoff_time = parse_and_validate_cutoff(cutoff)

    res = eval_service.evaluate(
        session=db,
        decision_date_from=d_from,
        decision_date_to=d_to,
        cutoff_time=cutoff_time,
    )

    m = res.metrics
    cov = res.coverage
    wape_pct = (m.wape * 100.0) if m.wape is not None else None

    response.headers["Cache-Control"] = CACHE_CONTROL_HISTORICAL

    return AccuracySummaryResponse(
        decision_date_from=res.decision_date_from,
        decision_date_to=res.decision_date_to,
        delivery_date_from=res.delivery_date_from,
        delivery_date_to=res.delivery_date_to,
        cutoff_time=res.cutoff_time.isoformat(),
        cutoff_timezone=res.cutoff_timezone,
        sample_count=m.sample_count,
        mae_mw=m.mae_mw,
        rmse_mw=m.rmse_mw,
        mean_bias_mw=m.mean_bias_mw,
        p50_absolute_error_mw=m.p50_absolute_error_mw,
        p90_absolute_error_mw=m.p90_absolute_error_mw,
        p95_absolute_error_mw=m.p95_absolute_error_mw,
        wape=m.wape,
        wape_percentage=wape_pct,
        total_forecast_energy_mwh=m.total_forecast_energy_mwh,
        total_actual_energy_mwh=m.total_actual_energy_mwh,
        total_absolute_error_mwh=m.total_absolute_error_mwh,
        wape_unavailable_reason=m.wape_unavailable_reason,
        coverage=CoverageStats(
            total_expected_target_hours=cov.total_expected_target_hours,
            targets_with_eligible_forecast=cov.targets_with_eligible_forecast,
            targets_missing_eligible_forecast=cov.targets_missing_eligible_forecast,
            targets_with_complete_actual=cov.targets_with_complete_actual,
            targets_missing_or_incomplete_actual=cov.targets_missing_or_incomplete_actual,
            matched_pairs_evaluated=cov.matched_pairs_evaluated,
            coverage_percentage=cov.coverage_percentage,
            excluded_targets_count=cov.excluded_targets_count,
        ),
    )


@api_router.get(
    "/accuracy/diurnal",
    response_model=DiurnalResponse,
    tags=["Accuracy"],
)
def get_accuracy_diurnal(
    response: Response,
    decision_date_from: Optional[str] = Query(None, description="Start decision date (YYYY-MM-DD)"),
    decision_date_to: Optional[str] = Query(None, description="End decision date (YYYY-MM-DD)"),
    cutoff: str = Query(DEFAULT_CUTOFF_STR, description="Cutoff time in Europe/London (HH:MM or HH:MM:SS)"),
    db: Session = Depends(get_db),
) -> DiurnalResponse:
    """Diurnal error profile grouped by hour of the day in Europe/London."""
    d_from, d_to = parse_and_validate_decision_range(decision_date_from, decision_date_to)
    cutoff_time = parse_and_validate_cutoff(cutoff)

    res = eval_service.evaluate(
        session=db,
        decision_date_from=d_from,
        decision_date_to=d_to,
        cutoff_time=cutoff_time,
    )

    items = [
        DiurnalMetricItem(
            hour_local=row.group_key,
            sample_count=row.sample_count,
            mae_mw=row.mae_mw,
            rmse_mw=row.rmse_mw,
            mean_bias_mw=row.mean_bias_mw,
            wape=row.wape,
            mean_forecast_mw=row.mean_forecast_mw,
            mean_actual_mw=row.mean_actual_mw,
        )
        for row in res.hourly_metrics
    ]

    response.headers["Cache-Control"] = CACHE_CONTROL_HISTORICAL

    return DiurnalResponse(
        decision_date_from=res.decision_date_from,
        decision_date_to=res.decision_date_to,
        cutoff_time=res.cutoff_time.isoformat(),
        cutoff_timezone=res.cutoff_timezone,
        diurnal_profile=items,
    )


@api_router.get(
    "/accuracy/distribution",
    response_model=DistributionResponse,
    tags=["Accuracy"],
)
def get_accuracy_distribution(
    response: Response,
    decision_date_from: Optional[str] = Query(None, description="Start decision date (YYYY-MM-DD)"),
    decision_date_to: Optional[str] = Query(None, description="End decision date (YYYY-MM-DD)"),
    cutoff: str = Query(DEFAULT_CUTOFF_STR, description="Cutoff time in Europe/London (HH:MM or HH:MM:SS)"),
    db: Session = Depends(get_db),
) -> DistributionResponse:
    """Forecast-horizon error grouping and percentile quantiles."""
    d_from, d_to = parse_and_validate_decision_range(decision_date_from, decision_date_to)
    cutoff_time = parse_and_validate_cutoff(cutoff)

    res = eval_service.evaluate(
        session=db,
        decision_date_from=d_from,
        decision_date_to=d_to,
        cutoff_time=cutoff_time,
    )

    items = [
        HorizonMetricItem(
            horizon_bucket=row.group_key,
            sample_count=row.sample_count,
            mae_mw=row.mae_mw,
            rmse_mw=row.rmse_mw,
            mean_bias_mw=row.mean_bias_mw,
            wape=row.wape,
            mean_forecast_mw=row.mean_forecast_mw,
            mean_actual_mw=row.mean_actual_mw,
        )
        for row in res.horizon_metrics
    ]

    quantiles = {
        "p50_absolute_error_mw": res.metrics.p50_absolute_error_mw,
        "p90_absolute_error_mw": res.metrics.p90_absolute_error_mw,
        "p95_absolute_error_mw": res.metrics.p95_absolute_error_mw,
    }

    response.headers["Cache-Control"] = CACHE_CONTROL_HISTORICAL

    return DistributionResponse(
        decision_date_from=res.decision_date_from,
        decision_date_to=res.decision_date_to,
        cutoff_time=res.cutoff_time.isoformat(),
        cutoff_timezone=res.cutoff_timezone,
        horizon_groups=items,
        error_quantiles=quantiles,
    )
