"""
app/db/models.py

SQLAlchemy 2.x ORM models for Elexon actuals and forecasts.
Includes timezone-aware UTC datetime storage and SQLite atomic upsert support.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Float,
    Index,
    Integer,
    String,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UTCDateTime(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that guarantees all timestamps are stored and loaded
    as timezone-aware UTC datetimes.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise ValueError(f"Expected datetime object, got {type(value)}")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat()

    def process_result_value(self, value: Optional[str], dialect) -> Optional[datetime]:
        if value is None:
            return None
        clean_str = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class ActualObservation(Base):
    """
    Half-hourly generation outturn observation from FUELHH stream.
    Retains original 30-min resolution without aggregation.
    """
    __tablename__ = "actual_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(32), default="FUELHH", nullable=False)
    publish_time_utc: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    start_time_utc: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    settlement_date: Mapped[str] = mapped_column(String(10), nullable=False)
    settlement_period: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(32), default="WIND", nullable=False)
    generation_mw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("start_time_utc", "fuel_type", name="uq_actuals_start_fuel"),
        Index("idx_actuals_start", "start_time_utc"),
        Index("idx_actuals_date", "settlement_date"),
    )


class ForecastObservation(Base):
    """
    Hourly wind generation forecast observation from WINDFOR stream.
    Preserves all publication versions per target start time.
    """
    __tablename__ = "forecast_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(32), default="WINDFOR", nullable=False)
    publish_time_utc: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    start_time_utc: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    generation_mw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("publish_time_utc", "start_time_utc", name="uq_forecast_pub_start"),
        Index("idx_forecast_start", "start_time_utc"),
        Index("idx_forecast_pub", "publish_time_utc"),
        Index("idx_forecast_start_pub", "start_time_utc", "publish_time_utc"),
    )
