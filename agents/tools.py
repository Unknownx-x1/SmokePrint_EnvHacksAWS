"""
Smokeprint Agent Tool Registry
Module: agents/tools.py

Exposes deterministic core physics and telemetry capabilities to the
Investigator and Critic agents via the Strands Agents SDK.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strands import tool

from core.ranking import (
    haversine_km,
    calculate_bearing_deg,
    rank_case_hypotheses,
    evaluate_chemical_signature
)
from core.priors import compute_source_prior, check_operating_status
from core.plume import (
    run_backward_plume_ensemble,
    query_candidate_footprint_density,
    calculate_footprint_discriminability
)
from core.background import compute_regional_background, classify_event

_VETTED_CASES = None
_OSM_CANDIDATES = None
_WIND_RECORDS = None
_ACTIVE_STATIONS = None

def _load_data():
    global _VETTED_CASES, _OSM_CANDIDATES, _WIND_RECORDS, _ACTIVE_STATIONS
    if _VETTED_CASES is None:
        with open("data/demo_cases_vetted.json", "r", encoding="utf-8") as f:
            _VETTED_CASES = json.load(f)
    if _OSM_CANDIDATES is None:
        with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
            _OSM_CANDIDATES = json.load(f)
    if _WIND_RECORDS is None:
        with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
            recs = json.load(f).get("records", [])
            _WIND_RECORDS = {r["time"]: r for r in recs}
    if _ACTIVE_STATIONS is None:
        with open("data/active_stations.json", "r", encoding="utf-8") as f:
            _ACTIVE_STATIONS = json.load(f)

@tool
def get_case_telemetry(case_id: str) -> Dict[str, Any]:
    """
    Retrieves vetted station telemetry, coordinates, pollutant concentrations,
    and QA/QC flags for an air-quality spike episode.
    """
    _load_data()
    case_meta = None
    for k, v in _VETTED_CASES.items():
        if v.get("case_id") == case_id or k == case_id:
            case_meta = v
            break

    if not case_meta:
        return {"error": f"Case ID '{case_id}' not found in vetted records."}

    return {
        "case_id": case_meta["case_id"],
        "station_id": case_meta.get("station_id"),
        "station_name": case_meta.get("station_name"),
        "timestamp_utc": case_meta["timestamp_utc"],
        "coordinates": case_meta.get("coordinates", {"latitude": 28.647, "longitude": 77.316}),
        "station_pm25": case_meta.get("station_pm25"),
        "station_pm10": case_meta.get("station_pm10"),
        "no2_ugm3": case_meta.get("no2_ugm3"),
        "co_mgm3": case_meta.get("co_mgm3"),
        "corroboration": case_meta.get("corroboration", {})
    }

@tool
def run_plume_trajectory(station_lat: float, station_lon: float, timestamp_utc: str) -> Dict[str, Any]:
    """
    Simulates a Monte Carlo backward Lagrangian atmospheric dispersion ensemble
    from the target station using ERA5 hourly winds, returning transport bearing,
    wind speed, and footprint discriminability.
    """
    _load_data()
    plume = run_backward_plume_ensemble(station_lat, station_lon, timestamp_utc, _WIND_RECORDS, n_particles=500)
    wind_cond = plume.get("wind_conditions", {})
    return {
        "wind_speed_ms": wind_cond.get("wind_speed_ms"),
        "wind_direction_deg": wind_cond.get("wind_direction_deg"),
        "boundary_layer_height_m": wind_cond.get("boundary_layer_height_m"),
        "is_low_wind": wind_cond.get("wind_speed_ms", 1.5) < 1.5,
        "upwind_transport_bearing_deg": plume.get("mean_transport_bearing_deg", wind_cond.get("wind_direction_deg"))
    }

@tool
def check_site_operating_history(candidate_id: str) -> Dict[str, Any]:
    """
    Inspects OpenStreetMap lifecycle tags (disused, abandoned, demolished, historic)
    and verifies whether a candidate site is actively operating or decommissioned.
    """
    _load_data()
    match = None
    for c in _OSM_CANDIDATES:
        if c.get("id") == candidate_id:
            match = c
            break

    if not match:
        return {"candidate_id": candidate_id, "found": False, "operating_status": "unknown"}

    status, penalty, reasons = check_operating_status(match)
    return {
        "candidate_id": candidate_id,
        "name": match.get("name"),
        "type": match.get("type"),
        "lat": match.get("lat"),
        "lon": match.get("lon"),
        "operating_status": status,
        "operating_reasons": reasons,
        "penalty_multiplier": penalty,
        "is_penalized": penalty < 1.0,
        "osm_tags": match.get("tags", {})
    }

@tool
def check_chemical_plume_coherence(
    pm25: Optional[float],
    pm10: Optional[float],
    no2: Optional[float],
    candidate_type: str
) -> Dict[str, Any]:
    """
    Validates physical coherence between observed co-pollutant concentrations
    and candidate emitter category (combustion smoke vs coarse mechanical dust).
    """
    mult, label, ev_for, ev_against = evaluate_chemical_signature(candidate_type, pm25, pm10, no2, None)
    ratio = round(pm25 / pm10, 2) if pm25 and pm10 and pm10 > 0 else None
    return {
        "candidate_type": candidate_type,
        "pm25_pm10_ratio": ratio,
        "signature_multiplier": mult,
        "signature_label": label,
        "evidence_for": ev_for,
        "evidence_against": ev_against,
        "is_consistent": mult >= 1.0
    }

@tool
def compute_initial_rankings(case_id: str) -> Dict[str, Any]:
    """
    Executes Smokeprint's full deterministic Bayesian ranking for the given case,
    returning ranked hypotheses, bootstrap confidence intervals, and discriminability.
    """
    case_file = os.path.join("data/cases_out", f"{case_id}.json")
    if os.path.exists(case_file):
        with open(case_file, "r", encoding="utf-8") as fp:
            return json.load(fp)

    _load_data()
    telemetry = get_case_telemetry(case_id)
    if "error" in telemetry:
        return telemetry

    c_lat = telemetry["coordinates"]["latitude"]
    c_lon = telemetry["coordinates"]["longitude"]
    ts = telemetry["timestamp_utc"]

    plume = run_backward_plume_ensemble(c_lat, c_lon, ts, _WIND_RECORDS, n_particles=500)
    bg_info = compute_regional_background(telemetry["station_id"], ts, _ACTIVE_STATIONS)
    event_class = classify_event(telemetry, ts, bg_info)

    out = rank_case_hypotheses(
        telemetry, bg_info, event_class, plume, _OSM_CANDIDATES, [], _ACTIVE_STATIONS
    )
    return out
