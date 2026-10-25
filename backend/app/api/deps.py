"""
app/api/deps.py

FastAPI dependencies and input validation helpers.
"""

from __future__ import annotations

from datetime import date, time
from typing import Generator, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_engine, get_session_factory
from app.schemas.api import JAN_2026_END, JAN_2026_START

DEFAULT_CUTOFF_STR = "10:00:00"


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session for request lifecycle."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        yield session


def parse_and_validate_cutoff(cutoff_str: Optional[str] = None) -> time:
    """Validate and parse cutoff time string (HH:MM or HH:MM:SS)."""
    raw = cutoff_str or DEFAULT_CUTOFF_STR
    try:
        # Support both HH:MM and HH:MM:SS
        parts = raw.split(":")
        if len(parts) == 2:
            return time(int(parts[0]), int(parts[1]))
        elif len(parts) == 3:
            return time(int(parts[0]), int(parts[1]), int(parts[2]))
        return time.fromisoformat(raw)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cutoff time format '{raw}'. Expected HH:MM or HH:MM:SS (e.g. 10:00).",
        )


def validate_decision_date_in_scope(d: date, field_name: str = "decision_date") -> None:
    """Ensure date is within the documented January 2026 decision scope."""
    if not (JAN_2026_START <= d <= JAN_2026_END):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{field_name} '{d.isoformat()}' is out of scope. "
                f"Purchase decisions must fall within January 2026 ({JAN_2026_START.isoformat()} to {JAN_2026_END.isoformat()})."
            ),
        )


def parse_and_validate_decision_range(
    date_from_str: Optional[str], date_to_str: Optional[str]
) -> tuple[date, date]:
    """Validate date range ordering and bounds."""
    try:
        start_date = (
            date.fromisoformat(date_from_str) if date_from_str else JAN_2026_START
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision_date_from format '{date_from_str}'. Expected YYYY-MM-DD.",
        )

    try:
        end_date = date.fromisoformat(date_to_str) if date_to_str else JAN_2026_END
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision_date_to format '{date_to_str}'. Expected YYYY-MM-DD.",
        )

    validate_decision_date_in_scope(start_date, "decision_date_from")
    validate_decision_date_in_scope(end_date, "decision_date_to")

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"decision_date_from ({start_date.isoformat()}) cannot be after "
                f"decision_date_to ({end_date.isoformat()})."
            ),
        )

    return start_date, end_date
