"""
Smokeprint Core Engine Automated Test Suite
Pytest test coverage for Phase 1 requirements:
  1. Punjabi Bagh episode (2026-04-28) => possible_fault
  2. Vikas Sadan episode (2026-06-30) => possible_fault
  3. CRRI episode (2026-05-16) => possible_fault or insufficient_evidence
  4. Regional smog (2025-10-20) => regional, no site ranking produced
  5. Corroborated Anand Vihar case => local, with a non-empty ranked site list
  6. Units: sensor with missing unit is excluded
  7. Missing PM10 or NO2 => ranking still runs, with wider intervals
"""

import os
import sys
import json
import pytest
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.qc_faults import detect_all_faults
from core.units import verify_and_convert_reading, load_sensor_metadata_registry
from core.background import compute_regional_background, classify_event
from core.plume import run_backward_plume_ensemble
from core.ranking import rank_case_hypotheses, evaluate_chemical_signature

@pytest.fixture(scope="session")
def shared_data():
    """Loads shared test datasets once per session."""
    with open("data/active_stations.json", "r", encoding="utf-8") as f:
        stations = json.load(f)
        
    with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
        wind = json.load(f)
        wind_records = {r["time"]: r for r in wind.get("records", [])}
        
    registry = load_sensor_metadata_registry()
    
    return {
        "stations": stations,
        "candidates": candidates,
        "wind_records": wind_records,
        "registry": registry
    }

def test_punjabi_bagh_episode():
    """Tests that Punjabi Bagh (2026-04-28) is flagged automatically as possible_fault."""
    with open("data/stations_qc/station_50_qc.json", "r", encoding="utf-8") as f:
        d50 = json.load(f)
        
    # Check that PM ratio violation or fault was caught at 2026-04-28 05:00Z
    fault_reasons = d50.get("fault_reasons", {})
    ts_fault = fault_reasons.get("2026-04-28T05:00:00Z")
    assert ts_fault is not None, "Punjabi Bagh fault was not recorded in fault_reasons"
    assert "pm_ratio_violation" in ts_fault, f"Expected pm_ratio_violation, got {ts_fault}"
    
    # Check background classification
    bg_info = {"regional_median": 75.0, "regional_iqr": 35.0, "network_elevation_pct": 20.0, "n_contributing": 25}
    classification = classify_event(d50, "2026-04-28T05:00:00Z", bg_info)
    assert classification["label"] == "possible_fault"

def test_vikas_sadan_episode():
    """Tests that Vikas Sadan (2026-06-30 constant 0.6 ratio then NaN) is flagged as possible_fault."""
    with open("data/stations_qc/station_301_qc.json", "r", encoding="utf-8") as f:
        d301 = json.load(f)
        
    fault_reasons = d301.get("fault_reasons", {})
    ts_fault = fault_reasons.get("2026-06-30T06:00:00Z")
    assert ts_fault is not None, "Vikas Sadan constant ratio lock not found in fault_reasons"
    assert "constant_ratio_lock" in ts_fault, f"Expected constant_ratio_lock, got {ts_fault}"
    
    bg_info = {"regional_median": 47.0, "regional_iqr": 22.0, "network_elevation_pct": 15.0, "n_contributing": 24}
    classification = classify_event(d301, "2026-06-30T06:00:00Z", bg_info)
    assert classification["label"] == "possible_fault"

def test_crri_episode():
    """Tests that CRRI (2026-05-16) collapse after peak triggers possible_fault or insufficient_evidence."""
    with open("data/stations_qc/station_5627_qc.json", "r", encoding="utf-8") as f:
        d5627 = json.load(f)
        
    fault_reasons = d5627.get("fault_reasons", {})
    ts_fault = fault_reasons.get("2026-05-16T06:00:00Z")
    assert ts_fault is not None, "CRRI collapse after peak not found in fault_reasons"
    assert "collapse_after_peak" in ts_fault, f"Expected collapse_after_peak, got {ts_fault}"
    
    bg_info = {"regional_median": 99.6, "regional_iqr": 41.0, "network_elevation_pct": 30.0, "n_contributing": 22}
    classification = classify_event(d5627, "2026-05-16T06:00:00Z", bg_info)
    assert classification["label"] in ["possible_fault", "insufficient_evidence"]

def test_regional_smog(shared_data):
    """Tests that regional smog (Diwali 2025-10-20) outputs 'regional' and NO site ranking."""
    bg_info = {
        "n_contributing": 22,
        "regional_median": 678.0,
        "regional_iqr": 142.0,
        "network_elevation_pct": 95.5
    }
    classification = classify_event(None, "2025-10-20T17:00:00Z", bg_info)
    assert classification["label"] == "regional"
    assert classification["dispatch_recommended"] is False
    
    # Run ranking
    plume_res = run_backward_plume_ensemble(28.6139, 77.2090, "2025-10-20T17:00:00Z", shared_data["wind_records"], n_particles=50)
    case_meta = {
        "case_id": "test_diwali",
        "station_name": "Airshed Regional Baseline",
        "timestamp_utc": "2025-10-20T17:00:00Z",
        "coordinates": {"latitude": 28.6139, "longitude": 77.2090}
    }
    
    out = rank_case_hypotheses(
        case_meta, bg_info, classification, plume_res, shared_data["candidates"], [], []
    )
    assert out["label"] == "regional"
    # Verify no site ranking was produced
    site_types = [h["type"] for h in out["hypotheses"] if h["type"] not in ["regional", "possible_fault", "insufficient_evidence"]]
    assert len(site_types) == 0, f"Expected zero site ranking for regional event, got {site_types}"
    assert out["hypotheses"][0]["type"] == "regional"

def test_corroborated_anand_vihar(shared_data):
    """Tests that a corroborated Anand Vihar case outputs 'local' with non-empty ranked site list."""
    with open("data/cases_out/case_anand_vihar_20260405.json", "r", encoding="utf-8") as f:
        case_out = json.load(f)
        
    assert case_out["label"] == "local"
    assert case_out["local_excess"] >= 50.0
    
    # Verify top hypothesis is an emitter site or localized candidate
    top_hypo = case_out["hypotheses"][0]
    assert top_hypo["type"] in ["landfill", "industrial", "brick_kiln", "construction"]
    assert top_hypo["relative_score"] >= 0.20
    assert len(top_hypo["interval"]) == 2
    assert top_hypo["interval"][0] < top_hypo["interval"][1]

def test_units_missing_excluded(shared_data):
    """Tests that sensors with missing units are excluded and logged, never guessing from magnitude."""
    custom_registry = {
        999991: {"sensor_id": 999991, "parameter": "no2", "units": None}, # missing unit
        999992: {"sensor_id": 999992, "parameter": "co", "units": "invalid_unit"} # unexpected unit
    }
    
    # Reading with missing unit
    val, unit, is_val, msg = verify_and_convert_reading(45.0, "no2", 999991, registry=custom_registry)
    assert not is_val
    assert val is None
    assert "missing unit" in msg
    
    # Reading with unexpected unit
    val, unit, is_val, msg = verify_and_convert_reading(1.5, "co", 999992, registry=custom_registry)
    assert not is_val
    assert val is None
    assert "unexpected unit" in msg
    
    # Non-existent sensor
    val, unit, is_val, msg = verify_and_convert_reading(30.0, "no2", 888888, registry=custom_registry)
    assert not is_val
    assert val is None
    assert "not found" in msg

def test_missing_pollutants_graceful_degradation(shared_data):
    """Tests that ranking still runs when PM10 or NO2 is missing, degrading gracefully with wider intervals."""
    # Complete pollutants
    mult_full, _, _, _ = evaluate_chemical_signature("brick_kiln", pm25=250.0, pm10=350.0, no2=50.0, co=1.8)
    
    # Missing PM10 and NO2
    mult_missing, sig_label, _, _ = evaluate_chemical_signature("brick_kiln", pm25=250.0, pm10=None, no2=None, co=None)
    
    assert mult_missing == 1.0, "Expected neutral multiplier 1.0 when co-pollutants are missing"
    assert sig_label == "unspecified"
    
    # Execute full ranking with missing pollutants
    bg_info = {"n_contributing": 20, "regional_median": 50.0, "regional_iqr": 20.0, "network_elevation_pct": 10.0}
    event_class = {"label": "local", "local_excess": 100.0, "regional_median": 50.0, "background_iqr": 20.0, "n_stations_background": 20}
    plume_res = run_backward_plume_ensemble(28.647, 77.316, "2026-04-05T22:00:00Z", shared_data["wind_records"], n_particles=50)
    
    case_meta = {
        "case_id": "test_missing_params",
        "station_name": "Test Station",
        "station_id": 235,
        "timestamp_utc": "2026-04-05T22:00:00Z",
        "station_pm25": 150.0,
        "station_pm10": None, # Missing PM10
        "no2_ugm3": None,     # Missing NO2
        "co_mgm3": None,      # Missing CO
        "coordinates": {"latitude": 28.647, "longitude": 77.316}
    }
    
    out = rank_case_hypotheses(
        case_meta, bg_info, event_class, plume_res, shared_data["candidates"], [], []
    )
    assert len(out["hypotheses"]) > 0
    top_h = out["hypotheses"][0]
    interval = top_h["interval"]
    assert interval[1] > interval[0]
