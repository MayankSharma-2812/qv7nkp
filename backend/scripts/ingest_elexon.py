#!/usr/bin/env python3
"""
backend/scripts/ingest_elexon.py

Historical data ingestion pipeline for Elexon actuals (FUELHH) and forecasts (WINDFOR).
Reuses ElexonClient with exponential backoff and SQLite atomic upserts.

Working Scope Assumptions:
- Decision dates: 2026-01-01 through 2026-01-31 inclusive (Europe/London).
- Delivery dates: 2026-01-02 through 2026-02-01 inclusive (UTC).
- Evaluation cutoff: 10:00 Europe/London on D-1 (evaluated in analytics, NOT filtered here).
- WINDFOR publication window: 2025-12-30T00:00:00Z to 2026-02-01T23:59:59Z to provide buffer.
- WINDFOR target filter: startTime >= 2026-01-02T00:00:00Z and startTime < 2026-02-02T00:00:00Z.
- All versions preserved (including post-cutoff publications).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator

# Add backend directory to sys.path to allow imports from app
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.clients.elexon import ElexonClient
from app.db.session import get_engine, get_session_factory, init_db
from app.repositories.elexon_repository import ElexonRepository
from app.schemas.elexon import ensure_utc_datetime


def generate_date_chunks(
    start_date: date, end_date: date, chunk_size_days: int = 7
) -> Generator[tuple[date, date], None, None]:
    """
    Generate inclusive date intervals of length at most chunk_size_days without gaps.
    """
    curr = start_date
    while curr <= end_date:
        chunk_end = min(curr + timedelta(days=chunk_size_days - 1), end_date)
        yield (curr, chunk_end)
        curr = chunk_end + timedelta(days=1)


def generate_datetime_chunks(
    start_dt: datetime, end_dt: datetime, chunk_size_days: int = 7
) -> Generator[tuple[datetime, datetime], None, None]:
    """
    Generate contiguous, non-overlapping UTC datetime intervals covering [start_dt, end_dt].
    """
    curr_start = ensure_utc_datetime(start_dt)
    target_end = ensure_utc_datetime(end_dt)

    while curr_start <= target_end:
        # End of chunk is start of chunk + days at 23:59:59
        curr_day = curr_start.date()
        chunk_end_day = curr_day + timedelta(days=chunk_size_days - 1)
        chunk_end = datetime(
            chunk_end_day.year,
            chunk_end_day.month,
            chunk_end_day.day,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        )
        if chunk_end > target_end:
            chunk_end = target_end

        yield (curr_start, chunk_end)
        # Advance by 1 second to begin next contiguous interval
        curr_start = chunk_end + timedelta(seconds=1)


async def run_ingestion(
    db_path: str,
    fuelhh_start: date,
    fuelhh_end: date,
    windfor_pub_start: datetime,
    windfor_pub_end: datetime,
    target_start: datetime,
    target_end: datetime,
    chunk_days: int = 7,
    client: ElexonClient | None = None,
) -> dict[str, Any]:
    """Execute complete ingestion pipeline for FUELHH and WINDFOR."""
    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)
    init_db(engine)
    session_factory = get_session_factory(engine)
    repo = ElexonRepository()

    close_client_on_exit = False
    if client is None:
        client = ElexonClient()
        close_client_on_exit = True

    report: dict[str, Any] = {
        "status": "RUNNING",
        "database_path": db_path,
        "fuelhh": {
            "requested_range": f"{fuelhh_start.isoformat()} to {fuelhh_end.isoformat()}",
            "chunks_total": 0,
            "chunks_successful": 0,
            "chunks_failed": 0,
            "records_retrieved": 0,
            "records_upserted": 0,
            "null_generation_count": 0,
            "failed_chunks": [],
        },
        "windfor": {
            "requested_pub_range": f"{windfor_pub_start.isoformat()} to {windfor_pub_end.isoformat()}",
            "target_window": f"{target_start.isoformat()} to {target_end.isoformat()}",
            "chunks_total": 0,
            "chunks_successful": 0,
            "chunks_failed": 0,
            "records_retrieved": 0,
            "records_filtered_out": 0,
            "records_upserted": 0,
            "null_generation_count": 0,
            "failed_chunks": [],
        },
    }

    print("\n" + "=" * 70)
    print("STARTING ELEXON HISTORICAL DATA INGESTION")
    print(f"Target Database: {db_path}")
    print(f"FUELHH Settlement Range: {report['fuelhh']['requested_range']}")
    print(f"WINDFOR Publication Range: {report['windfor']['requested_pub_range']}")
    print(f"WINDFOR Delivery Target: {report['windfor']['target_window']}")
    print("=" * 70)

    try:
        # 1. Ingest FUELHH Actuals in chunks
        print("\n--- Phase 1: Ingesting FUELHH (Actual Wind Generation) ---")
        fuel_chunks = list(generate_date_chunks(fuelhh_start, fuelhh_end, chunk_days))
        report["fuelhh"]["chunks_total"] = len(fuel_chunks)

        for idx, (c_start, c_end) in enumerate(fuel_chunks, 1):
            c_desc = f"{c_start.isoformat()} -> {c_end.isoformat()}"
            print(f"[{idx}/{len(fuel_chunks)}] Fetching FUELHH: {c_desc}...", end=" ", flush=True)
            try:
                records = await client.fetch_fuelhh(c_start, c_end, fuel_type="WIND")
                with session_factory() as session:
                    with session.begin():
                        res = repo.upsert_actuals(session, records)

                report["fuelhh"]["records_retrieved"] += res["retrieved"]
                report["fuelhh"]["records_upserted"] += res["upserted"]
                report["fuelhh"]["null_generation_count"] += res["null_generation"]
                report["fuelhh"]["chunks_successful"] += 1
                print(f"OK ({res['upserted']} records upserted)")
            except Exception as e:
                report["fuelhh"]["chunks_failed"] += 1
                report["fuelhh"]["failed_chunks"].append({"chunk": c_desc, "error": str(e)})
                print(f"FAILED: {e}")

        # 2. Ingest WINDFOR Forecasts in chunks
        print("\n--- Phase 2: Ingesting WINDFOR (Wind Generation Forecasts) ---")
        wind_chunks = list(generate_datetime_chunks(windfor_pub_start, windfor_pub_end, chunk_days))
        report["windfor"]["chunks_total"] = len(wind_chunks)

        for idx, (c_start, c_end) in enumerate(wind_chunks, 1):
            c_desc = f"{c_start.strftime('%Y-%m-%dT%H:%M:%SZ')} -> {c_end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            print(f"[{idx}/{len(wind_chunks)}] Fetching WINDFOR: {c_desc}...", end=" ", flush=True)
            try:
                records = await client.fetch_windfor(c_start, c_end)
                with session_factory() as session:
                    with session.begin():
                        res = repo.upsert_forecasts(
                            session,
                            records,
                            target_start=target_start,
                            target_end=target_end,
                        )

                report["windfor"]["records_retrieved"] += res["retrieved"]
                report["windfor"]["records_filtered_out"] += res["filtered_out"]
                report["windfor"]["records_upserted"] += res["upserted"]
                report["windfor"]["null_generation_count"] += res["null_generation"]
                report["windfor"]["chunks_successful"] += 1
                print(f"OK ({res['retrieved']} received, {res['upserted']} within target window)")
            except Exception as e:
                report["windfor"]["chunks_failed"] += 1
                report["windfor"]["failed_chunks"].append({"chunk": c_desc, "error": str(e)})
                print(f"FAILED: {e}")

        # 3. Final validation and stats
        with session_factory() as session:
            db_stats = repo.get_database_stats(session)
            report["final_database_stats"] = db_stats

        file_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        report["database_file_size_bytes"] = file_size_bytes
        report["database_file_size_mb"] = round(file_size_bytes / (1024 * 1024), 2)

        has_failures = (
            report["fuelhh"]["chunks_failed"] > 0 or report["windfor"]["chunks_failed"] > 0
        )
        report["status"] = "COMPLETED_WITH_FAILURES" if has_failures else "SUCCESS"

    finally:
        if close_client_on_exit:
            await client.aclose()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest historical Elexon FUELHH and WINDFOR data into SQLite."
    )
    parser.add_argument(
        "--db-path",
        default="gridbricks.db",
        help="Path to SQLite database file (default: gridbricks.db)",
    )
    parser.add_argument(
        "--fuelhh-start",
        default="2026-01-02",
        help="Start settlement date for FUELHH (default: 2026-01-02)",
    )
    parser.add_argument(
        "--fuelhh-end",
        default="2026-02-01",
        help="End settlement date for FUELHH (default: 2026-02-01)",
    )
    parser.add_argument(
        "--windfor-pub-start",
        default="2025-12-30T00:00:00Z",
        help="Start publication timestamp for WINDFOR (default: 2025-12-30T00:00:00Z)",
    )
    parser.add_argument(
        "--windfor-pub-end",
        default="2026-02-01T23:59:59Z",
        help="End publication timestamp for WINDFOR (default: 2026-02-01T23:59:59Z)",
    )
    parser.add_argument(
        "--target-start",
        default="2026-01-02T00:00:00Z",
        help="Minimum target startTime to retain (default: 2026-01-02T00:00:00Z)",
    )
    parser.add_argument(
        "--target-end",
        default="2026-02-02T00:00:00Z",
        help="Exclusive maximum target startTime to retain (default: 2026-02-02T00:00:00Z)",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=7,
        help="Chunk size in days for API batch requests (default: 7)",
    )

    args = parser.parse_args()

    fuelhh_start = date.fromisoformat(args.fuelhh_start)
    fuelhh_end = date.fromisoformat(args.fuelhh_end)
    windfor_pub_start = ensure_utc_datetime(args.windfor_pub_start)
    windfor_pub_end = ensure_utc_datetime(args.windfor_pub_end)
    target_start = ensure_utc_datetime(args.target_start)
    target_end = ensure_utc_datetime(args.target_end)

    report = asyncio.run(
        run_ingestion(
            db_path=args.db_path,
            fuelhh_start=fuelhh_start,
            fuelhh_end=fuelhh_end,
            windfor_pub_start=windfor_pub_start,
            windfor_pub_end=windfor_pub_end,
            target_start=target_start,
            target_end=target_end,
            chunk_days=args.chunk_days,
        )
    )

    print("\n" + "=" * 70)
    print("INGESTION SUMMARY REPORT")
    print(f"Status: {report['status']}")
    print(f"Database File: {report['database_path']} ({report['database_file_size_mb']} MB)")
    print(f"FUELHH Actuals Stored: {report['final_database_stats']['actuals']['total_rows']}")
    print(
        f"  - Start Time Range: {report['final_database_stats']['actuals']['min_start_time']} -> {report['final_database_stats']['actuals']['max_start_time']}"
    )
    print(
        f"  - Null Generation Count: {report['final_database_stats']['actuals']['null_generation_count']}"
    )
    print(f"WINDFOR Forecasts Stored: {report['final_database_stats']['forecasts']['total_rows']}")
    print(
        f"  - Target Start Time Range: {report['final_database_stats']['forecasts']['min_start_time']} -> {report['final_database_stats']['forecasts']['max_start_time']}"
    )
    print(
        f"  - Publication Time Range: {report['final_database_stats']['forecasts']['min_publish_time']} -> {report['final_database_stats']['forecasts']['max_publish_time']}"
    )
    print(
        f"  - Null Generation Count: {report['final_database_stats']['forecasts']['null_generation_count']}"
    )
    print("=" * 70)

    if report["status"] != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
