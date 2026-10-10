#!/usr/bin/env python3
"""
Smokeprint Raw OpenAQ Telemetry Checker (Phase 5.9)
Script: scripts/raw_check.py

Downloads raw OpenAQ daily gzip files from AWS Open Data public archive:
s3://openaq-data-archive/records/csv.gz/locationid=<id>/year=YYYY/month=MM/location-<id>-YYYYMMDD.csv.gz
via unsigned S3 client access.

Converts all timestamps between UTC and Asia/Kolkata (IST = UTC+05:30).
Pivots pm25, pm10, and no2 by hour with exact selection method:
- Nominal target for UTC hour H is interval midpoint H + 05:30 (i.e. HH:30 IST).
- Selects exact row matching H + 05:30 if present.
- If missing, selects nearest row in window [H - 30m, H + 30m].
- If no data within window, reports NaN.

Usage:
    python scripts/raw_check.py --station <id> --start <YYYY-MM-DDTHH:MM:SSZ> --end <YYYY-MM-DDTHH:MM:SSZ>
    python scripts/raw_check.py --case <case_id>
    python scripts/raw_check.py --all
"""

import os
import sys
import io
import csv
import gzip
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import boto3
from botocore import UNSIGNED
from botocore.config import Config

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

IST = timezone(timedelta(hours=5, minutes=30))
CACHE_DIR = "data/raw_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

S3_BUCKET = "openaq-data-archive"
s3_client = boto3.client("s3", config=Config(signature_version=UNSIGNED))

CASE_WINDOWS = {
    "case_anand_vihar_20251102": {
        "station_id": 235,
        "name": "Anand Vihar, New Delhi - DPCC",
        "spike_utc": "2025-11-02T22:00:00Z",  # True raw peak at 22:00Z (03:30 IST)
        "window_start": "2025-11-02T17:00:00Z",
        "window_end": "2025-11-03T03:00:00Z"
    },
    "case_anand_vihar_20260131": {
        "station_id": 235,
        "name": "Anand Vihar, New Delhi - DPCC",
        "spike_utc": "2026-01-31T06:00:00Z",  # True raw peak at 06:00Z (11:30 IST)
        "window_start": "2026-01-31T01:00:00Z",
        "window_end": "2026-01-31T11:00:00Z"
    },
    "case_rkpuram_20251112": {
        "station_id": 17,
        "name": "R K Puram, Delhi - DPCC",
        "spike_utc": "2025-11-12T16:00:00Z",  # True raw peak at 16:00Z (21:30 IST)
        "window_start": "2025-11-12T11:00:00Z",
        "window_end": "2025-11-12T21:00:00Z"
    },
    "case_crri_20260515": {
        "station_id": 5627,
        "name": "CRRI Mathura Road, New Delhi - IMD",
        "spike_utc": "2026-05-16T00:00:00Z",  # True raw peak at 00:00Z (05:30 IST May 16)
        "window_start": "2026-05-15T19:00:00Z",
        "window_end": "2026-05-16T05:00:00Z"
    },
    "case_gurugram_20260630": {
        "station_id": 301,
        "name": "Vikas Sadan, Gurugram - HSPCB",
        "spike_utc": "2026-06-30T07:00:00Z",  # Raw peak before lock at 07:00Z (12:30 IST)
        "window_start": "2026-06-30T02:00:00Z",
        "window_end": "2026-06-30T12:00:00Z"
    },
    "case_regional_smog_20251020": {
        "station_id": 5598,  # Highest clean regional station: Sector-125 Noida
        "name": "Sector - 125, Noida, UP - UPPCB (Clean Airshed Representative)",
        "spike_utc": "2025-10-20T17:00:00Z",
        "window_start": "2025-10-20T12:00:00Z",
        "window_end": "2025-10-20T22:00:00Z"
    }
}

def download_raw_file(loc_id: int, day_str: str) -> Optional[str]:
    """Downloads raw OpenAQ daily csv.gz file if not already cached."""
    cache_path = os.path.join(CACHE_DIR, f"location-{loc_id}-{day_str}.csv.gz")
    if os.path.exists(cache_path):
        return cache_path

    year = day_str[:4]
    month = day_str[4:6]
    s3_key = f"records/csv.gz/locationid={loc_id}/year={year}/month={month}/location-{loc_id}-{day_str}.csv.gz"

    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        with open(cache_path, "wb") as f:
            f.write(obj["Body"].read())
        return cache_path
    except Exception as e:
        print(f"  [WARN] Failed to download {s3_key}: {e}", file=sys.stderr)
        return None

def fetch_raw_rows_for_window(loc_id: int, start_utc: datetime, end_utc: datetime) -> List[Dict[str, Any]]:
    """Loads all raw records for a station within a UTC time window."""
    # Compute calendar IST days needed
    cur = start_utc - timedelta(hours=6)
    days = set()
    while cur <= end_utc + timedelta(hours=6):
        ist_cur = cur.astimezone(IST)
        days.add(ist_cur.strftime("%Y%m%d"))
        cur += timedelta(hours=6)

    raw_rows = []
    for day_str in sorted(days):
        fpath = download_raw_file(loc_id, day_str)
        if not fpath:
            continue
        try:
            with gzip.open(fpath, "rt", encoding="utf-8") as gz:
                reader = csv.DictReader(gz)
                for r in reader:
                    # Datetime in raw file is IST (+05:30)
                    dt = datetime.fromisoformat(r["datetime"])
                    dt_utc = dt.astimezone(timezone.utc)
                    if start_utc - timedelta(minutes=45) <= dt_utc <= end_utc + timedelta(minutes=45):
                        raw_rows.append({
                            "utc_dt": dt_utc,
                            "ist_dt": dt.astimezone(IST),
                            "raw_datetime": r["datetime"],
                            "param": r["parameter"],
                            "val": float(r["value"]),
                            "units": r["units"],
                            "sensor_id": r["sensors_id"],
                            "location": r.get("location", "")
                        })
        except Exception as e:
            print(f"  [ERROR] Reading {fpath}: {e}", file=sys.stderr)

    return raw_rows

def pivot_hourly_telemetry(loc_id: int, start_utc: datetime, end_utc: datetime, name_hint: str = ""):
    """Computes hourly pivot with exact value selection method."""
    rows = fetch_raw_rows_for_window(loc_id, start_utc, end_utc)
    if not rows:
        print(f"No raw data found for Station {loc_id} between {start_utc.isoformat()} and {end_utc.isoformat()}")
        return

    location_name = rows[0]["location"] if rows else name_hint
    params = ["pm25", "pm10", "no2"]

    # Discover sensor IDs and units
    sensors = {}
    units = {}
    for p in params:
        p_rows = [r for r in rows if r["param"] == p]
        if p_rows:
            sensors[p] = p_rows[0]["sensor_id"]
            units[p] = p_rows[0]["units"]
        else:
            sensors[p] = "N/A"
            units[p] = "N/A"

    print("=" * 115)
    print(f"RAW OPENAQ HOURLY PIVOT: Station {loc_id} | {location_name}")
    print(f"UTC Window: {start_utc.strftime('%Y-%m-%d %H:%M:%SZ')} to {end_utc.strftime('%Y-%m-%d %H:%M:%SZ')}")
    print(f"Sensors: PM2.5={sensors['pm25']} ({units['pm25']}), PM10={sensors['pm10']} ({units['pm10']}), NO2={sensors['no2']} ({units['no2']})")
    print("Exact Method: For each UTC hour H (HH:00Z), interval midpoint is H + 05:30 (HH:30 IST).")
    print("              Selects exact row at HH:30 IST if present, else nearest reading in [H - 30m, H + 30m].")
    print("=" * 115)
    print(f"{'UTC (Midpoint)':<18} | {'IST (Midpoint)':<16} | {'PM2.5':<10} | {'PM10':<10} | {'Ratio':<8} | {'NO2':<10} | {'Method / Match Details'}")
    print("-" * 115)

    cur = start_utc
    while cur <= end_utc:
        ist_cur = cur.astimezone(IST)
        vals = {}
        match_details = []

        for p in params:
            p_rows = [r for r in rows if r["param"] == p and abs((r["utc_dt"] - cur).total_seconds()) <= 1800]
            if not p_rows:
                vals[p] = None
            else:
                # Find exact match at cur (:00Z / :30 IST)
                exact = [r for r in p_rows if r["utc_dt"] == cur]
                if exact:
                    vals[p] = exact[0]["val"]
                else:
                    # Pick closest reading
                    p_rows.sort(key=lambda x: abs((x["utc_dt"] - cur).total_seconds()))
                    vals[p] = p_rows[0]["val"]
                    offset_min = int((p_rows[0]["utc_dt"] - cur).total_seconds() / 60)
                    match_details.append(f"{p}:{offset_min:+d}m")

        pm25_v = vals.get("pm25")
        pm10_v = vals.get("pm10")
        no2_v = vals.get("no2")

        pm25_str = f"{pm25_v:7.1f} {units['pm25']}" if pm25_v is not None else "   NaN"
        pm10_str = f"{pm10_v:7.1f} {units['pm10']}" if pm10_v is not None else "   NaN"
        no2_str = f"{no2_v:7.1f} {units['no2']}" if no2_v is not None else "   NaN"

        ratio_str = f"{pm25_v / pm10_v:.3f}" if (pm25_v is not None and pm10_v is not None and pm10_v > 0) else "   —"

        detail_str = "exact :30 IST" if not match_details else f"nearest ({', '.join(match_details)})"
        if pm25_v is None and pm10_v is None:
            detail_str = "no telemetry / dropout"

        utc_str = cur.strftime("%Y-%m-%d %H:%M:%SZ")
        ist_str = ist_cur.strftime("%Y-%m-%d %H:%M IST")

        print(f"{utc_str:<18} | {ist_str:<16} | {pm25_str:<10} | {pm10_str:<10} | {ratio_str:<8} | {no2_str:<10} | {detail_str}")

        cur += timedelta(hours=1)
    print("=" * 115)
    print()

def main():
    parser = argparse.ArgumentParser(description="Raw OpenAQ Telemetry Pivot Checker")
    parser.add_argument("--station", type=int, help="Station ID")
    parser.add_argument("--start", type=str, help="Start UTC timestamp (ISO)")
    parser.add_argument("--end", type=str, help="End UTC timestamp (ISO)")
    parser.add_argument("--case", type=str, help="Specific Case ID")
    parser.add_argument("--all", action="store_true", help="Run for all 6 visible cases")

    args = parser.parse_args()

    if args.all:
        for cid, cinfo in CASE_WINDOWS.items():
            s_utc = datetime.fromisoformat(cinfo["window_start"].replace("Z", "+00:00"))
            e_utc = datetime.fromisoformat(cinfo["window_end"].replace("Z", "+00:00"))
            print(f"\n>>> CASE: {cid} (Spike at {cinfo['spike_utc']} UTC, Window: -5h to +5h)")
            pivot_hourly_telemetry(cinfo["station_id"], s_utc, e_utc, cinfo["name"])
        return

    if args.case:
        if args.case not in CASE_WINDOWS:
            print(f"Unknown case: {args.case}. Available: {list(CASE_WINDOWS.keys())}")
            sys.exit(1)
        cinfo = CASE_WINDOWS[args.case]
        s_utc = datetime.fromisoformat(cinfo["window_start"].replace("Z", "+00:00"))
        e_utc = datetime.fromisoformat(cinfo["window_end"].replace("Z", "+00:00"))
        pivot_hourly_telemetry(cinfo["station_id"], s_utc, e_utc, cinfo["name"])
        return

    if args.station and args.start and args.end:
        s_utc = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
        e_utc = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
        pivot_hourly_telemetry(args.station, s_utc, e_utc)
        return

    # Default to running all
    for cid, cinfo in CASE_WINDOWS.items():
        s_utc = datetime.fromisoformat(cinfo["window_start"].replace("Z", "+00:00"))
        e_utc = datetime.fromisoformat(cinfo["window_end"].replace("Z", "+00:00"))
        print(f"\n>>> CASE: {cid} (Spike at {cinfo['spike_utc']} UTC, Window: -5h to +5h)")
        pivot_hourly_telemetry(cinfo["station_id"], s_utc, e_utc, cinfo["name"])

if __name__ == "__main__":
    main()
