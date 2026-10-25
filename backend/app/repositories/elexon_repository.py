"""
app/repositories/elexon_repository.py

Repository for idempotent persistence and retrieval of Elexon actuals and forecasts.
Uses SQLite-native atomic upserts (ON CONFLICT DO UPDATE) to prevent duplicates
and support upstream corrections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.orm import Session

from app.db.models import ActualObservation, ForecastObservation
from app.schemas.elexon import FuelHHRecord, WindforRecord, ensure_utc_datetime


class ElexonRepository:
    """Data access repository for ActualObservation and ForecastObservation."""

    def upsert_actuals(
        self, session: Session, records: list[FuelHHRecord]
    ) -> dict[str, int]:
        """
        Atomically upsert FUELHH actual observations using unique key (start_time_utc, fuel_type).
        Preserves null generation values as None.
        """
        if not records:
            return {"retrieved": 0, "upserted": 0, "null_generation": 0}

        null_count = 0
        raw_rows = []
        for r in records:
            if r.generation is None:
                null_count += 1
            raw_rows.append(
                {
                    "dataset": r.dataset,
                    "publish_time_utc": r.publishTime,
                    "start_time_utc": r.startTime,
                    "settlement_date": r.settlementDate,
                    "settlement_period": r.settlementPeriod,
                    "fuel_type": r.fuelType,
                    "generation_mw": r.generation,
                }
            )

        stmt = sqlite_upsert(ActualObservation).values(raw_rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["start_time_utc", "fuel_type"],
            set_={
                "generation_mw": stmt.excluded.generation_mw,
                "publish_time_utc": stmt.excluded.publish_time_utc,
                "settlement_date": stmt.excluded.settlement_date,
                "settlement_period": stmt.excluded.settlement_period,
            },
        )
        session.execute(stmt)

        return {
            "retrieved": len(records),
            "upserted": len(raw_rows),
            "null_generation": null_count,
        }

    def upsert_forecasts(
        self,
        session: Session,
        records: list[WindforRecord],
        target_start: Optional[datetime] = None,
        target_end: Optional[datetime] = None,
    ) -> dict[str, int]:
        """
        Atomically upsert WINDFOR forecast observations using unique key (publish_time_utc, start_time_utc).
        Optionally filters records to target window: [target_start, target_end).
        Preserves all publication versions per target start time.
        """
        if not records:
            return {
                "retrieved": 0,
                "filtered_out": 0,
                "upserted": 0,
                "null_generation": 0,
            }

        target_start_utc = (
            ensure_utc_datetime(target_start) if target_start else None
        )
        target_end_utc = ensure_utc_datetime(target_end) if target_end else None

        filtered_rows = []
        null_count = 0
        filtered_out_count = 0

        for r in records:
            # Check target delivery window filter
            if target_start_utc and r.startTime < target_start_utc:
                filtered_out_count += 1
                continue
            if target_end_utc and r.startTime >= target_end_utc:
                filtered_out_count += 1
                continue

            if r.generation is None:
                null_count += 1

            filtered_rows.append(
                {
                    "dataset": r.dataset,
                    "publish_time_utc": r.publishTime,
                    "start_time_utc": r.startTime,
                    "generation_mw": r.generation,
                }
            )

        if filtered_rows:
            stmt = sqlite_upsert(ForecastObservation).values(filtered_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["publish_time_utc", "start_time_utc"],
                set_={
                    "generation_mw": stmt.excluded.generation_mw,
                    "dataset": stmt.excluded.dataset,
                },
            )
            session.execute(stmt)

        return {
            "retrieved": len(records),
            "filtered_out": filtered_out_count,
            "upserted": len(filtered_rows),
            "null_generation": null_count,
        }

    def get_actuals(
        self,
        session: Session,
        start_time_from: Optional[datetime] = None,
        start_time_to: Optional[datetime] = None,
        fuel_type: str = "WIND",
    ) -> list[ActualObservation]:
        """Query actual observations ordered by start_time_utc ascending."""
        query = select(ActualObservation).where(
            ActualObservation.fuel_type == fuel_type
        )
        if start_time_from:
            query = query.where(
                ActualObservation.start_time_utc >= ensure_utc_datetime(start_time_from)
            )
        if start_time_to:
            query = query.where(
                ActualObservation.start_time_utc <= ensure_utc_datetime(start_time_to)
            )
        query = query.order_by(ActualObservation.start_time_utc.asc())
        return list(session.scalars(query).all())

    def get_forecasts(
        self,
        session: Session,
        start_time_from: Optional[datetime] = None,
        start_time_to: Optional[datetime] = None,
        publish_cutoff: Optional[datetime] = None,
    ) -> list[ForecastObservation]:
        """Query forecast observations with optional cutoff and target window filters."""
        query = select(ForecastObservation)
        if start_time_from:
            query = query.where(
                ForecastObservation.start_time_utc >= ensure_utc_datetime(start_time_from)
            )
        if start_time_to:
            query = query.where(
                ForecastObservation.start_time_utc <= ensure_utc_datetime(start_time_to)
            )
        if publish_cutoff:
            query = query.where(
                ForecastObservation.publish_time_utc <= ensure_utc_datetime(publish_cutoff)
            )
        query = query.order_by(
            ForecastObservation.start_time_utc.asc(),
            ForecastObservation.publish_time_utc.desc(),
        )
        return list(session.scalars(query).all())

    def get_database_stats(self, session: Session) -> dict[str, Any]:
        """Compute coverage and aggregate statistics for stored data."""
        actuals_count = session.scalar(
            select(func.count(ActualObservation.id))
        ) or 0
        forecasts_count = session.scalar(
            select(func.count(ForecastObservation.id))
        ) or 0

        actuals_null = session.scalar(
            select(func.count(ActualObservation.id)).where(
                ActualObservation.generation_mw.is_(None)
            )
        ) or 0
        forecasts_null = session.scalar(
            select(func.count(ForecastObservation.id)).where(
                ForecastObservation.generation_mw.is_(None)
            )
        ) or 0

        actuals_min_start = session.scalar(
            select(func.min(ActualObservation.start_time_utc))
        )
        actuals_max_start = session.scalar(
            select(func.max(ActualObservation.start_time_utc))
        )

        forecasts_min_start = session.scalar(
            select(func.min(ForecastObservation.start_time_utc))
        )
        forecasts_max_start = session.scalar(
            select(func.max(ForecastObservation.start_time_utc))
        )
        forecasts_min_pub = session.scalar(
            select(func.min(ForecastObservation.publish_time_utc))
        )
        forecasts_max_pub = session.scalar(
            select(func.max(ForecastObservation.publish_time_utc))
        )

        return {
            "actuals": {
                "total_rows": actuals_count,
                "null_generation_count": actuals_null,
                "min_start_time": actuals_min_start,
                "max_start_time": actuals_max_start,
            },
            "forecasts": {
                "total_rows": forecasts_count,
                "null_generation_count": forecasts_null,
                "min_start_time": forecasts_min_start,
                "max_start_time": forecasts_max_start,
                "min_publish_time": forecasts_min_pub,
                "max_publish_time": forecasts_max_pub,
            },
        }
