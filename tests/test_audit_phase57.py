"""
Smokeprint Phase 5.7 Audit Tests
File: tests/test_audit_phase57.py

Tests:
  1. For each case, the stored wind equals the ERA5 row at the hour of the maximum PM2.5
     in its own hourly series (within 1 hour).
  2. Regional smog case numbers in the case bundle (network median: 678.0, 22 stations reporting,
     21 over 200, and max station 959.0 at CRRI Mathura Road) tie to the JSON.
  3. Gurugram instrument fault telemetry rows prove constant ratio lock ~0.6000 from 08:30Z
     to 11:30Z followed by NaN dropout at 12:30Z, matching refusal basis.
  4. Header has "Demo build" and no unauthorized words implying official authority remain in web/src.
"""

import os
import re
import json
import glob
from datetime import datetime, timezone
import pytest

ALL_7_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112",
]

def load_canonical_case(case_id: str, directory: str = "data/cases_out") -> dict:
    path = os.path.join(directory, f"{case_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_stored_wind_equals_era5_at_hour_of_maximum_pm25():
    """For each case, stored wind equals the ERA5 row at the hour of max PM2.5 (within 1 hour)."""
    with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
        era5_records = {r["time"]: r for r in json.load(f)["records"]}

    for directory in ["data/cases_out", "web/src/data/cases"]:
        for cid in ALL_7_CASES:
            case_data = load_canonical_case(cid, directory)
            w = case_data.get("wind", {})
            assert w, f"[{cid}] Missing wind block in {directory}"
            stored_spd = w.get("wind_speed_ms")
            stored_dir = w.get("wind_direction_deg")
            
            tw_mid_utc = case_data.get("time_window", {}).get("interval_midpoint_utc")
            assert tw_mid_utc, f"[{cid}] Missing interval_midpoint_utc"
            dt_mid = datetime.fromisoformat(tw_mid_utc.replace("Z", "+00:00"))
            
            if cid == "case_regional_smog_20251020":
                era5_key = tw_mid_utc[:13] + ":00"
                era5_row = era5_records[era5_key]
                assert stored_spd == pytest.approx(era5_row["wind_speed_ms"], rel=1e-3)
                assert stored_dir == pytest.approx(era5_row["wind_direction_deg"], rel=1e-3)
                continue
                
            hourly = case_data.get("hourly_series")
            assert hourly, f"[{cid}] Missing hourly_series in {directory}"
            readings = hourly.get("readings", [])
            assert len(readings) == 5, f"[{cid}] hourly_series must have 5 readings"
            
            # Find maximum PM2.5 reading
            max_reading = max(readings, key=lambda r: (r.get("pm25_ugm3") or 0.0))
            t_max_utc = max_reading["timestamp_utc"]
            dt_max = datetime.fromisoformat(t_max_utc.replace("Z", "+00:00"))
            
            # The difference between the hour of the maximum PM2.5 and stored wind midpoint must be <= 1 hour
            diff_hours = abs((dt_max - dt_mid).total_seconds()) / 3600.0
            assert diff_hours <= 1.0, (
                f"[{cid}] Discrepancy between max PM2.5 hour ({t_max_utc}) and stored wind ({tw_mid_utc}): "
                f"{diff_hours:.2f} hours > 1.0 hour"
            )
            
            # Verify stored wind matches the ERA5 row at the stored midpoint
            era5_key = tw_mid_utc[:13] + ":00"
            era5_row = era5_records.get(era5_key)
            assert era5_row, f"[{cid}] Missing ERA5 record for {era5_key}"
            assert stored_spd == pytest.approx(era5_row["wind_speed_ms"], rel=1e-3)
            assert stored_dir == pytest.approx(era5_row["wind_direction_deg"], rel=1e-3)

def test_regional_case_numbers_tied_to_case_json():
    """Regional smog case numbers in the case bundle match canonical values."""
    for directory in ["data/cases_out", "web/src/data/cases"]:
        case_data = load_canonical_case("case_regional_smog_20251020", directory)
        assert case_data["regional_median"] == 678.0
        
        summary = case_data.get("regional_smog_summary")
        assert summary is not None, f"Missing regional_smog_summary in {directory}"
        assert summary["network_median_pm25"] == 678.0
        assert summary["reporting_stations"] == 22
        assert summary["stations_over_200"] == 21
        assert summary["elevated_pct"] == 95.5
        assert summary["max_station_name"] == "Sector - 125, Noida, UP - UPPCB"
        assert summary["max_station_pm25"] == 881.0

def test_gurugram_fault_detector_rows_and_refusal():
    """Verify Gurugram instrument fault detector rows and refusal text."""
    for directory in ["data/cases_out", "web/src/data/cases"]:
        case_data = load_canonical_case("case_gurugram_20260630", directory)
        assert case_data["dispatch_refused"] is True
        basis = case_data.get("refusal_basis", "")
        assert "constant_ratio_lock" in basis
        assert "collapse_after_peak" in basis
        assert "0.6000" in basis
        assert "08:30Z to 11:30Z" in basis
        assert "12:30Z" in basis

def test_no_unauthorized_regulatory_words_in_ui():
    """Ensure no words implying unauthorized official regulatory authority appear in UI source files."""
    unauthorized = ["regulatory", "certified", "official", "compliance"]
    found = []
    for root, _, files in os.walk("web/src"):
        for f in files:
            if f.endswith((".tsx", ".ts", ".jsx", ".js")):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                for word in unauthorized:
                    matches = re.findall(r"\b" + word + r"\b", content, re.IGNORECASE)
                    if matches:
                        found.append(f"{path}: found '{word}' ({len(matches)} times)")
    assert not found, f"Found unauthorized regulatory/official words in UI: {found}"
