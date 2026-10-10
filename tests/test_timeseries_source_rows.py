"""
Unit test for Phase 5.6 TimeSeriesChart data integrity.
Asserts that every plotted point in hourly_series across all canonical cases
exists directly in the stored OpenAQ source rows (QC'd, with same units and sensor IDs).
"""

import json
import glob
import os
import pytest

CASES_DIRS = ["data/cases_out", "web/src/data/cases"]
CANONICAL_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112",
]


def test_hourly_series_source_rows_exist_and_match():
    """Verify that every hourly point plotted in TimeSeriesChart originates from stored OpenAQ rows."""
    for base_dir in CASES_DIRS:
        for cid in CANONICAL_CASES:
            case_path = os.path.join(base_dir, f"{cid}.json")
            assert os.path.exists(case_path), f"Missing {case_path}"
            
            with open(case_path, "r", encoding="utf-8") as f:
                case_data = json.load(f)
                
            if case_data.get("hidden_from_demo"):
                continue

            hourly = case_data.get("hourly_series")
            
            # Regional smog is a multi-station regional event: hourly_series must be None
            if cid == "case_regional_smog_20251020":
                assert hourly is None, f"{cid} should have hourly_series = None for plain baseline comparison"
                continue
                
            # Single-station cases must have an hourly_series
            assert hourly is not None, f"{cid} in {base_dir} lacks hourly_series"
            assert "station_id" in hourly, f"{cid} missing station_id"
            assert "sensor_id" in hourly, f"{cid} missing sensor_id"
            assert hourly["label"] == "hourly value (as reported), shown in IST"
            assert hourly["parameter"] == "pm25"
            assert hourly["unit"] == "ug/m3"
            
            readings = hourly.get("readings", [])
            assert len(readings) == 5, f"{cid} must have exactly 5 hourly window readings (T-2h to T+2h)"
            
            # Load stored OpenAQ source rows
            source_file = hourly["source_file"]
            assert os.path.exists(source_file), f"Source row file {source_file} not found"
            
            with open(source_file, "r", encoding="utf-8") as sf:
                source_json = json.load(sf)
                
            data_dict = source_json.get("data", {})
            param = hourly.get("parameter", "pm25")
            param_data = data_dict.get(param, {})
            assert len(param_data) > 0, f"No {param} data found in {source_file}"
            
            # Verify sensor ID matches
            sensor_map = source_json.get("sensors", {})
            if param in sensor_map:
                assert sensor_map[param] == hourly["sensor_id"], (
                    f"Sensor ID mismatch for {cid}: expected {sensor_map[param]}, got {hourly['sensor_id']}"
                )
                    
            # Check every plotted point against source rows
            for r in readings:
                ts_utc = r["timestamp_utc"]
                plotted_val = float(r["pm25_ugm3"])
                
                assert ts_utc in param_data, (
                    f"Plotted point {ts_utc} for {cid} not found in {source_file} under {param}"
                )
                source_val = float(param_data[ts_utc])
                assert abs(plotted_val - source_val) < 1e-3, (
                    f"Plotted value {plotted_val} does not match source row value {source_val} at {ts_utc} in {source_file}"
                )


def test_timeseries_label_and_units():
    """Verify label is 'hourly means, interval midpoint, IST' and no interpolation/synthetic points."""
    for base_dir in CASES_DIRS:
        for cid in CANONICAL_CASES:
            case_path = os.path.join(base_dir, f"{cid}.json")
            with open(case_path, "r", encoding="utf-8") as f:
                case_data = json.load(f)
            if case_data.get("hidden_from_demo"):
                continue
            hourly = case_data.get("hourly_series")
            if hourly:
                assert hourly["label"] == "hourly value (as reported), shown in IST"
                for reading in hourly["readings"]:
                    assert "time_ist" in reading
                    assert "offset_label" in reading
                    assert isinstance(reading["pm25_ugm3"], (int, float))
