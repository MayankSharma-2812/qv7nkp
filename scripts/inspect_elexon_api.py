#!/usr/bin/env python3
"""
scripts/inspect_elexon_api.py

Inspection utility to validate live Elexon BMRS API endpoints:
- datasets/FUELHH/stream
- datasets/WINDFOR/stream
"""

import json
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Gridbricks-Verification-Script/1.0",
            "Accept": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            raw_body = response.read()
            parsed = json.loads(raw_body)
            return {
                "status": status,
                "content_type": content_type,
                "data": parsed,
                "error": None
            }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "content_type": e.headers.get("Content-Type", ""),
            "data": None,
            "error": f"HTTPError {e.code}: {e.read().decode('utf-8', errors='replace')}"
        }
    except Exception as e:
        return {
            "status": None,
            "content_type": None,
            "data": None,
            "error": str(e)
        }

def inspect_fuelhh():
    print("=" * 60)
    print("1. Inspecting FUELHH/stream for settlementDate 2026-01-10 (fuelType=WIND)")
    print("=" * 60)
    url = f"{BASE_URL}/datasets/FUELHH/stream?settlementDateFrom=2026-01-10&settlementDateTo=2026-01-10&fuelType=WIND"
    print(f"Request URL: {url}")
    res = fetch_json(url)
    
    print(f"HTTP Status: {res['status']}")
    print(f"Content-Type: {res['content_type']}")
    
    if res['error']:
        print(f"Error encountered: {res['error']}")
        return None
        
    data = res['data']
    print(f"Response Shape: list of {type(data[0]).__name__ if data else 'empty list'}")
    print(f"Returned Records Count: {len(data)}")
    
    if not data:
        print("No records returned.")
        return None

    sample = data[0]
    print(f"Field Names: {list(sample.keys())}")
    print(f"Sample Record:\n{json.dumps(sample, indent=2)}")
    
    # Validation checks
    null_gen = [d for d in data if d.get("generation") is None]
    missing_start = [d for d in data if not d.get("startTime")]
    missing_pub = [d for d in data if not d.get("publishTime")]
    non_wind = [d for d in data if d.get("fuelType") != "WIND"]
    
    periods = [d.get("settlementPeriod") for d in data]
    unique_periods = sorted(list(set(periods)))
    
    print("\nQuality Checks:")
    print(f" - Records with null generation: {len(null_gen)}")
    print(f" - Records with missing startTime: {len(missing_start)}")
    print(f" - Records with missing publishTime: {len(missing_pub)}")
    print(f" - Records with fuelType != 'WIND': {len(non_wind)}")
    print(f" - Settlement periods present: {len(unique_periods)} (min: {min(unique_periods)}, max: {max(unique_periods)})")
    
    # Check duplicates by startTime
    starts = [d.get("startTime") for d in data]
    print(f" - Unique start times: {len(set(starts))} / {len(starts)} total records")
    
    # Save small representative fixture (first 2 and last 1)
    fixtures_dir = Path("scripts/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture_sample = data[:2] + data[-1:]
    with open(fixtures_dir / "fuelhh_sample.json", "w") as f:
        json.dump(fixture_sample, f, indent=2)
    print(f"Saved {len(fixture_sample)} representative sample records to scripts/fixtures/fuelhh_sample.json")
    
    return data

def inspect_windfor():
    print("\n" + "=" * 60)
    print("2. Inspecting WINDFOR/stream for publishTime around 2026-01-09")
    print("=" * 60)
    url = f"{BASE_URL}/datasets/WINDFOR/stream?publishDateTimeFrom=2026-01-09T00:00:00Z&publishDateTimeTo=2026-01-09T23:59:59Z"
    print(f"Request URL: {url}")
    res = fetch_json(url)
    
    print(f"HTTP Status: {res['status']}")
    print(f"Content-Type: {res['content_type']}")
    
    if res['error']:
        print(f"Error encountered: {res['error']}")
        return None
        
    data = res['data']
    print(f"Response Shape: list of {type(data[0]).__name__ if data else 'empty list'}")
    print(f"Returned Records Count: {len(data)}")
    
    if not data:
        print("No records returned.")
        return None

    sample = data[0]
    print(f"Field Names: {list(sample.keys())}")
    print(f"Sample Record:\n{json.dumps(sample, indent=2)}")
    
    # Validation checks
    null_gen = [d for d in data if d.get("generation") is None]
    missing_start = [d for d in data if not d.get("startTime")]
    missing_pub = [d for d in data if not d.get("publishTime")]
    
    pub_times = sorted(list(set(d.get("publishTime") for d in data)))
    start_times = sorted(list(set(d.get("startTime") for d in data)))
    
    print("\nQuality Checks:")
    print(f" - Records with null generation: {len(null_gen)}")
    print(f" - Records with missing startTime: {len(missing_start)}")
    print(f" - Records with missing publishTime: {len(missing_pub)}")
    print(f" - Distinct publication times count: {len(pub_times)}")
    print(f" - Distinct publication times: {pub_times}")
    print(f" - Target start times range: {start_times[0]} to {start_times[-1]}")
    
    # Check whether multiple forecast publications exist for the same startTime
    by_start = defaultdict(list)
    for d in data:
        by_start[d.get("startTime")].append(d)
        
    multi_pubs = {st: pubs for st, pubs in by_start.items() if len(pubs) > 1}
    print(f"\nRelationship between publishTime and startTime:")
    print(f" - Total unique target start times in this publication batch: {len(by_start)}")
    print(f" - Target start times with multiple forecast publications: {len(multi_pubs)}")
    
    if multi_pubs:
        # Pick one example startTime to inspect revisions
        example_st = list(multi_pubs.keys())[len(multi_pubs)//2]
        print(f"\nExample Target StartTime: {example_st}")
        print("Forecast revisions published across 2026-01-09:")
        for rec in multi_pubs[example_st]:
            print(f"   Published at: {rec.get('publishTime')} -> Forecast Generation: {rec.get('generation')} MW")
            
    # Check exact duplicates: (publishTime, startTime)
    keys = [(d.get("publishTime"), d.get("startTime")) for d in data]
    print(f"\nDuplicate Check: {len(keys)} total records, {len(set(keys))} unique (publishTime, startTime) pairs")
    
    # Save small representative fixture (first 2 and last 1)
    fixtures_dir = Path("scripts/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture_sample = data[:2] + data[-1:]
    with open(fixtures_dir / "windfor_sample.json", "w") as f:
        json.dump(fixture_sample, f, indent=2)
    print(f"Saved {len(fixture_sample)} representative sample records to scripts/fixtures/windfor_sample.json")
    
    return data

if __name__ == "__main__":
    inspect_fuelhh()
    inspect_windfor()
