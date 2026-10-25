"""
app/services/evaluation.py

End-to-end evaluation orchestration service.
Integrates database reading with pure domain logic (forecast selection,
hourly actual alignment, and metric calculations) for any configurable
decision-date range and cutoff time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.session import DEFAULT_DB_URL, get_engine, get_session_factory
from app.repositories.elexon_repository import ElexonRepository
from app.services.actuals import (
    ActualsAlignmentStats,
    HourlyActual,
    aggregate_hourly_actuals,
)
from app.services.forecast_selection import (
    DEFAULT_CUTOFF_TIME,
    ForecastSelectionStats,
    LONDON_TZ,
    SelectedForecast,
    select_day_ahead_forecasts,
)
from app.services.metrics import (
    AggregateMetrics,
    GroupedMetricRow,
    MatchedPair,
    calculate_aggregate_metrics,
    calculate_metrics_by_delivery_hour,
    calculate_metrics_by_horizon,
)


@dataclass(frozen=True)
class OverallCoverageDiagnostics:
    """Comprehensive data quality and coverage audit for the evaluation window."""
    total_expected_target_hours: int
    targets_with_eligible_forecast: int
    targets_missing_eligible_forecast: int
    targets_with_complete_actual: int
    targets_missing_or_incomplete_actual: int
    matched_pairs_evaluated: int
    coverage_percentage: float  # (matched_pairs / total_expected_target_hours) * 100
    excluded_targets_count: int


@dataclass(frozen=True)
class EvaluationResult:
    """Complete evaluation response structure."""
    decision_date_from: date
    decision_date_to: date
    delivery_date_from: date
    delivery_date_to: date
    cutoff_time: time
    cutoff_timezone: str
    metrics: AggregateMetrics
    hourly_metrics: list[GroupedMetricRow]
    horizon_metrics: list[GroupedMetricRow]
    coverage: OverallCoverageDiagnostics
    selected_forecasts_sample: list[SelectedForecast]  # First few records for preview
    matched_pairs_sample: list[MatchedPair]


class ForecastEvaluationService:
    """Service orchestrating day-ahead forecast evaluation."""

    def __init__(self, repo: Optional[ElexonRepository] = None):
        self.repo = repo or ElexonRepository()

    def evaluate(
        self,
        session: Session,
        decision_date_from: date,
        decision_date_to: date,
        cutoff_time: time = DEFAULT_CUTOFF_TIME,
    ) -> EvaluationResult:
        """
        Evaluate forecast accuracy for an inclusive decision-date range.
        
        Parameters:
            session: Active SQLAlchemy database session.
            decision_date_from: Inclusive start date of decision period.
            decision_date_to: Inclusive end date of decision period.
            cutoff_time: Evaluation cutoff time in Europe/London.
        """
        if decision_date_from > decision_date_to:
            raise ValueError(
                f"decision_date_from ({decision_date_from}) cannot be after decision_date_to ({decision_date_to})"
            )

        # 1. Determine corresponding delivery dates in Europe/London
        delivery_date_from = decision_date_from + timedelta(days=1)
        delivery_date_to = decision_date_to + timedelta(days=1)

        # Calculate total calendar days and expected target hours
        num_delivery_days = (delivery_date_to - delivery_date_from).days + 1
        expected_total_hours = num_delivery_days * 24

        # Convert delivery window to UTC bounds for repository querying
        start_min_utc = datetime.combine(
            delivery_date_from, time(0, 0), tzinfo=LONDON_TZ
        ).astimezone(timezone.utc)
        # End at 23:30 of the last day to capture the second half-hour for 23:00
        start_max_utc = datetime.combine(
            delivery_date_to, time(23, 30), tzinfo=LONDON_TZ
        ).astimezone(timezone.utc)

        # 2. Query raw forecasts and actuals from repository
        raw_forecasts = self.repo.get_forecasts(
            session, start_time_from=start_min_utc, start_time_to=start_max_utc
        )
        raw_actuals = self.repo.get_actuals(
            session, start_time_from=start_min_utc, start_time_to=start_max_utc
        )

        # 3. Select eligible forecasts as of decision cutoff (strict temporal anti-leakage)
        selected_by_target, f_stats = select_day_ahead_forecasts(
            forecast_records=raw_forecasts,
            decision_date_from=decision_date_from,
            decision_date_to=decision_date_to,
            cutoff_time=cutoff_time,
        )

        # 4. Generate all expected hourly target timestamps in UTC
        all_expected_targets: list[datetime] = []
        curr_delivery = delivery_date_from
        while curr_delivery <= delivery_date_to:
            for h in range(24):
                dt_local = datetime.combine(curr_delivery, time(h, 0), tzinfo=LONDON_TZ)
                all_expected_targets.append(dt_local.astimezone(timezone.utc))
            curr_delivery += timedelta(days=1)

        # 5. Align hourly actuals
        hourly_actuals, a_stats = aggregate_hourly_actuals(
            target_hours=all_expected_targets,
            actual_records=raw_actuals,
            fuel_type="WIND",
        )

        # 6. Pair eligible forecasts with complete actuals
        matched_pairs: list[MatchedPair] = []
        excluded_count = 0

        for t_utc in all_expected_targets:
            f_record = selected_by_target.get(t_utc)
            a_record = hourly_actuals.get(t_utc)

            # Check if both are present and valid
            if (
                f_record is not None
                and f_record.generation_mw is not None
                and a_record is not None
                and a_record.is_complete
                and a_record.generation_mw is not None
            ):
                local_hour = t_utc.astimezone(LONDON_TZ).hour
                f_gen = f_record.generation_mw
                a_gen = a_record.generation_mw
                err = f_gen - a_gen
                matched_pairs.append(
                    MatchedPair(
                        target_start_utc=t_utc,
                        delivery_hour_local=local_hour,
                        publish_time_utc=f_record.publish_time_utc,
                        horizon_hours=f_record.horizon_hours,
                        forecast_generation_mw=f_gen,
                        actual_generation_mw=a_gen,
                        error_mw=err,
                        absolute_error_mw=abs(err),
                    )
                )
            else:
                excluded_count += 1

        # 7. Calculate aggregate and grouped metrics
        agg_metrics = calculate_aggregate_metrics(matched_pairs)
        hourly_metrics = calculate_metrics_by_delivery_hour(matched_pairs)
        horizon_metrics = calculate_metrics_by_horizon(matched_pairs)

        # 8. Compute overall coverage diagnostics
        cov_pct = (
            (len(matched_pairs) / expected_total_hours * 100.0)
            if expected_total_hours > 0
            else 0.0
        )
        coverage_diag = OverallCoverageDiagnostics(
            total_expected_target_hours=expected_total_hours,
            targets_with_eligible_forecast=len(selected_by_target),
            targets_missing_eligible_forecast=f_stats.targets_missing_eligible_forecast,
            targets_with_complete_actual=a_stats.complete_hourly_actuals,
            targets_missing_or_incomplete_actual=a_stats.incomplete_hourly_actuals,
            matched_pairs_evaluated=len(matched_pairs),
            coverage_percentage=round(cov_pct, 2),
            excluded_targets_count=excluded_count,
        )

        return EvaluationResult(
            decision_date_from=decision_date_from,
            decision_date_to=decision_date_to,
            delivery_date_from=delivery_date_from,
            delivery_date_to=delivery_date_to,
            cutoff_time=cutoff_time,
            cutoff_timezone="Europe/London",
            metrics=agg_metrics,
            hourly_metrics=hourly_metrics,
            horizon_metrics=horizon_metrics,
            coverage=coverage_diag,
            selected_forecasts_sample=list(selected_by_target.values())[:10],
            matched_pairs_sample=matched_pairs[:10],
        )
