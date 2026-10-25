"""
app/schemas/elexon.py

Pydantic models for upstream Elexon data streams:
- FUELHH (Half-hourly generation outturn by fuel type)
- WINDFOR (Wind generation forecast)
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


def ensure_utc_datetime(v: datetime | str) -> datetime:
    """
    Ensure datetimes are parsed as timezone-aware UTC.
    If string is passed, parse via datetime.fromisoformat.
    If naive datetime is passed, attach UTC.
    If aware datetime is passed, convert to UTC.
    """
    if isinstance(v, str):
        # Handle trailing 'Z' if present for older Python or ISO compliance
        clean_str = v.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
    elif isinstance(v, datetime):
        dt = v
    else:
        raise ValueError(f"Expected datetime or ISO string, got {type(v)}")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class FuelHHRecord(BaseModel):
    """
    Half-hourly generation outturn record from /datasets/FUELHH/stream.
    Preserves missing generation as None (never converts to zero).
    """
    model_config = ConfigDict(extra="ignore")

    dataset: str = "FUELHH"
    publishTime: datetime
    startTime: datetime
    settlementDate: str
    settlementPeriod: int
    fuelType: str
    generation: Optional[float] = None

    @field_validator("publishTime", "startTime", mode="before")
    @classmethod
    def validate_utc_timestamps(cls, v: datetime | str) -> datetime:
        return ensure_utc_datetime(v)

    @field_validator("generation", mode="before")
    @classmethod
    def validate_generation(cls, v: Optional[float | int]) -> Optional[float]:
        if v is None:
            return None
        return float(v)


class WindforRecord(BaseModel):
    """
    Wind generation forecast record from /datasets/WINDFOR/stream.
    Preserves missing generation as None (never converts to zero).
    """
    model_config = ConfigDict(extra="ignore")

    dataset: str = "WINDFOR"
    publishTime: datetime
    startTime: datetime
    generation: Optional[float] = None

    @field_validator("publishTime", "startTime", mode="before")
    @classmethod
    def validate_utc_timestamps(cls, v: datetime | str) -> datetime:
        return ensure_utc_datetime(v)

    @field_validator("generation", mode="before")
    @classmethod
    def validate_generation(cls, v: Optional[float | int]) -> Optional[float]:
        if v is None:
            return None
        return float(v)
