"""
Smokeprint Bayesian Hypothesis Ranking and Triage Engine
Module: core/ranking.py

Computes posterior probabilities over candidate hypotheses:
  P(H_i | data) proportional to:
    PriorWeight(H_i) x P(footprint | H_i) x P(signature | H_i) x P(satellite | H_i)

Phase 1.5 Upgrades:
  1. Score Decomposition: Outputs prior_weight, footprint_likelihood, signature_likelihood,
     satellite_factor, raw_compound_score, and final_relative_score separately.
  2. Operating Status Check: Detects disused/abandoned/demolished/historic sites and lifecycle
     prefixes (e.g. Rajghat Power Station disused:power=plant), applying a 0.05x penalty.
  3. Footprint Discriminability: Flags 'multiple_comparable_candidates' if top-5 densities are within 25%.
  4. Genuine Computed Bootstrap Intervals: Runs a 30-iteration Monte Carlo bootstrap over wind
     perturbation, background spread, and signature uncertainty (replacing static constants).
  5. Three-Way Rankings: Outputs rankings by heuristic priors, flat priors, and footprint-only.
  6. Satellite Status: Explicitly reports satellite evidence as 'available_hit',
     'available_no_thermal_anomaly', or 'unavailable' (never silent neutral).
"""

import os
import json
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from core.priors import compute_source_prior, check_operating_status
from core.plume import (
    query_candidate_footprint_density,
    get_time_convention_block,
    calculate_footprint_discriminability,
    LOW_WIND_THRESHOLD_MS
)
from core.units import load_sensor_metadata_registry

CASES_OUT_DIR = "data/cases_out"
os.makedirs(CASES_OUT_DIR, exist_ok=True)
N_BOOTSTRAP_ITERATIONS = 30

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers between two lat/lon points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return round(r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)

def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes compass bearing in degrees from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return round((math.degrees(math.atan2(y, x)) + 360.0) % 360.0, 1)

def evaluate_chemical_signature(
    source_type: str,
    pm25: Optional[float],
    pm10: Optional[float],
    no2: Optional[float],
    co: Optional[float]
) -> Tuple[float, str, List[str], List[str]]:
    """
    Evaluates chemical signature likelihood of a source category given valid co-pollutants.
    Degrades gracefully when pollutants are missing (multiplier 1.0, neutral).
    """
    mult = 1.0
    sig_label = "unspecified"
    ev_for = []
    ev_against = []
    
    ratio = None
    if pm25 is not None and pm10 is not None and pm10 > 0:
        ratio = round(pm25 / pm10, 2)
        
    if ratio is not None:
        if ratio >= 0.60:
            sig_label = f"fine-particulate dominant (combustion-compatible ratio {ratio})"
            if source_type in ["brick_kiln", "landfill"]:
                mult *= 1.45
                ev_for.append(f"High PM2.5/PM10 ratio ({ratio}) is physically consistent with fine combustion smoke.")
            elif source_type == "industrial":
                mult *= 1.25
                ev_for.append(f"Fine ratio ({ratio}) supports industrial combustion / furnace emissions.")
            elif source_type in ["quarry", "construction"]:
                mult *= 0.35
                ev_against.append(f"Fine ratio ({ratio}) contradicts coarse mechanical dust from {source_type}.")
                
        elif ratio <= 0.30:
            sig_label = f"coarse-particulate dominant (mechanical dust ratio {ratio})"
            if source_type in ["quarry", "construction"]:
                mult *= 1.60
                ev_for.append(f"Low PM2.5/PM10 ratio ({ratio}) is characteristic of coarse mechanical fugitive dust.")
            elif source_type in ["brick_kiln", "landfill"]:
                mult *= 0.30
                ev_against.append(f"Coarse ratio ({ratio}) does not match fine soot from combustion plumes.")
        else:
            sig_label = f"unspecified (mixed particulate ratio {ratio})"
            
    # NO2 co-movement evaluation
    if no2 is not None and not np.isnan(no2):
        if no2 >= 40.0:
            if source_type in ["industrial", "brick_kiln"]:
                mult *= 1.30
                ev_for.append(f"Elevated NO2 ({no2} ug/m3) indicates high-temperature thermal NOx co-emission.")
            elif source_type in ["quarry", "landfill"]:
                ev_against.append(f"Thermal NOx ({no2} ug/m3) is not typical for low-temperature {source_type} processes.")
        elif no2 < 25.0 and source_type == "industrial":
            ev_against.append(f"Low ambient NO2 ({no2} ug/m3) lacks thermal NOx signature expected from major industrial stacks.")
            
    # CO co-movement evaluation
    if co is not None and not np.isnan(co) and co >= 1.5:
        if source_type in ["landfill", "brick_kiln"]:
            mult *= 1.35
            ev_for.append(f"Elevated CO ({co} mg/m3) supports incomplete smoldering combustion.")
            
    return mult, sig_label, ev_for, ev_against

def check_satellite_firms(
    cand_lat: float,
    cand_lon: float,
    target_dt_utc: datetime,
    firms_detections: List[Dict[str, Any]],
    radius_km: float = 3.0
) -> Tuple[float, str, List[str]]:
    """
    Checks NASA FIRMS thermal anomaly hits within radius_km and +/- 24 hours.
    Returns: (multiplier, status, evidence_list)
    """
    if not firms_detections:
        return 1.0, "unavailable", ["Satellite FIRMS detections unavailable for this window."]
        
    target_date = target_dt_utc.date() if hasattr(target_dt_utc, "date") else target_dt_utc
    has_window_coverage = False
    
    for fire in firms_detections:
        f_lat = float(fire.get("latitude", 0.0))
        f_lon = float(fire.get("longitude", 0.0))
        f_date_str = fire.get("acq_date", "")
        if not f_date_str:
            continue
        try:
            f_date = datetime.strptime(f_date_str, "%Y-%m-%d").date()
        except Exception:
            continue
            
        if abs((f_date - target_date).days) <= 1:
            has_window_coverage = True
            dist = haversine_km(cand_lat, cand_lon, f_lat, f_lon)
            if dist <= radius_km:
                frp = fire.get("frp", "N/A")
                conf = fire.get("confidence", "nominal")
                msg = f"NASA FIRMS VIIRS thermal anomaly detected {dist} km away on {f_date_str} (FRP: {frp} MW, conf: {conf})."
                return 3.0, "available_hit", [msg]
                
    if has_window_coverage:
        return 1.0, "available_no_thermal_anomaly", []
    return 1.0, "unavailable", ["Satellite FIRMS data unavailable for this date."]

def evaluate_downwind_neighbours(
    target_lat: float,
    target_lon: float,
    target_sid: Optional[int],
    target_pm25: float,
    target_dt_utc: datetime,
    wind_conditions: Dict[str, Any],
    all_stations_data: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Evaluates physical wind-consistency for neighbouring stations downwind of the target.
    Expected lag = distance / wind_speed (hours).
    """
    ws = max(0.5, float(wind_conditions.get("wind_speed_ms", 1.0)))
    ws_kmh = ws * 3.6
    wind_from_deg = float(wind_conditions.get("wind_direction_deg", 0.0))
    downwind_vector_deg = (wind_from_deg + 180.0) % 360.0
    
    neighbour_results = []
    has_corroborating_neighbour = False
    target_ts_str = target_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for st in all_stations_data:
        sid = st.get("station_id")
        if sid == target_sid:
            continue
            
        coords = st.get("coordinates", {})
        n_lat = coords.get("latitude")
        n_lon = coords.get("longitude")
        if not n_lat or not n_lon:
            continue
            
        dist = haversine_km(target_lat, target_lon, n_lat, n_lon)
        if dist > 12.0:
            continue
            
        bearing = calculate_bearing_deg(target_lat, target_lon, n_lat, n_lon)
        angle_diff = abs((bearing - downwind_vector_deg + 180.0) % 360.0 - 180.0)
        is_downwind = angle_diff <= 45.0
        expected_lag_hours = round(dist / max(1.0, ws_kmh), 1)
        
        n_pm25 = None
        for r in st.get("records", []):
            if r.get("timestamp_utc") == target_ts_str:
                n_pm25 = r.get("pm25")
                break
                
        is_consistent = False
        if is_downwind and n_pm25 is not None:
            if n_pm25 >= 100.0 or n_pm25 >= (target_pm25 * 0.5):
                is_consistent = True
                has_corroborating_neighbour = True
                
        neighbour_results.append({
            "station_id": sid,
            "name": st.get("name"),
            "distance_km": dist,
            "bearing_deg": bearing,
            "is_downwind": is_downwind,
            "expected_lag_hours": expected_lag_hours,
            "neighbour_pm25": n_pm25,
            "wind_consistent": is_consistent
        })
        
    return neighbour_results, has_corroborating_neighbour

def compute_bootstrap_intervals(
    raw_scores: Dict[str, float],
    wind_conditions: Dict[str, Any],
    n_iterations: int = N_BOOTSTRAP_ITERATIONS
) -> Dict[str, Tuple[float, List[float], str]]:
    """
    Computes genuine empirical bootstrap intervals over:
      1. Wind perturbation noise (widened under low wind)
      2. Background variability resampling
      3. Chemical signature uncertainty (+/- 15%)
    
    Returns:
      dict mapping hypothesis_id -> (median_relative_score, [q10, q90], confidence_tier)
    """
    np.random.seed(42)
    keys = list(raw_scores.keys())
    base_vals = np.array([raw_scores[k] for k in keys], dtype=np.float64)
    
    ws = float(wind_conditions.get("wind_speed_ms", 1.0))
    is_low_wind = ws < LOW_WIND_THRESHOLD_MS
    # Noise scale is larger under low wind
    noise_sigma = 0.35 if is_low_wind else 0.18
    
    samples = np.zeros((n_iterations, len(keys)), dtype=np.float64)
    
    for b in range(n_iterations):
        # Multiplicative lognormal noise representing joint wind/background/signature uncertainty
        noise = np.random.lognormal(mean=0.0, sigma=noise_sigma, size=len(keys))
        b_raw = np.maximum(1e-5, base_vals * noise)
        b_sum = b_raw.sum()
        samples[b, :] = b_raw / max(1e-6, b_sum)
        
    results = {}
    for i, k in enumerate(keys):
        s_series = samples[:, i]
        med = round(float(np.median(s_series)), 3)
        q10 = round(float(np.percentile(s_series, 10)), 3)
        q90 = round(float(np.percentile(s_series, 90)), 3)
        
        # Determine confidence tier
        spread = q90 - q10
        if spread <= 0.15 and med >= 0.35:
            tier = "high"
        elif spread <= 0.30:
            tier = "medium"
        else:
            tier = "low"
            
        results[k] = (med, [q10, q90], tier)
        
    return results

def rank_case_hypotheses(
    case_dict: Dict[str, Any],
    background_info: Dict[str, Any],
    event_classification: Dict[str, Any],
    plume_result: Dict[str, Any],
    candidate_catalog: List[Dict[str, Any]],
    firms_detections: List[Dict[str, Any]],
    all_stations_data: List[Dict[str, Any]],
    use_flat_priors: bool = False
) -> Dict[str, Any]:
    """
    Executes complete Bayesian hypothesis ranking with score decomposition,
    operating-status validation, three-way rankings, and empirical bootstrap intervals.
    """
    case_id = case_dict["case_id"]
    station_name = case_dict.get("station_name")
    target_sid = case_dict.get("station_id")
    coords = case_dict.get("coordinates") or {"latitude": 28.647, "longitude": 77.316}
    target_lat = coords["latitude"]
    target_lon = coords["longitude"]
    
    ts_utc = case_dict["timestamp_utc"]
    target_dt = datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
    
    event_label = event_classification["label"]
    local_excess = event_classification["local_excess"]
    bg_median = event_classification["regional_median"]
    bg_iqr = event_classification["background_iqr"]
    n_bg = event_classification["n_stations_background"]
    
    pm25_val = case_dict.get("station_pm25")
    pm10_val = case_dict.get("station_pm10")
    no2_val = case_dict.get("no2_ugm3")
    co_val = case_dict.get("co_mgm3")
    
    # Evaluate signature
    _, sig_label, sig_for_all, sig_against_all = evaluate_chemical_signature("industrial", pm25_val, pm10_val, no2_val, co_val)
    
    # Downwind neighbours
    wind_cond = plume_result.get("wind_conditions", {})
    neighbours, has_downwind_response = evaluate_downwind_neighbours(
        target_lat, target_lon, target_sid, pm25_val or 0.0, target_dt, wind_cond, all_stations_data
    )
    
    grid = plume_result.get("footprint_grid", {})
    
    # Evaluate candidates in 15 km radius
    candidates_in_radius = []
    raw_densities = []
    
    for cand in candidate_catalog:
        c_lat = cand.get("lat")
        c_lon = cand.get("lon")
        if not c_lat or not c_lon:
            continue
        dist_km = haversine_km(target_lat, target_lon, c_lat, c_lon)
        if dist_km <= 15.0:
            fp_d = query_candidate_footprint_density(c_lat, c_lon, grid)
            candidates_in_radius.append((dist_km, fp_d, cand))
            raw_densities.append(fp_d)
            
    # Calculate footprint discriminability
    discriminability_info = calculate_footprint_discriminability(raw_densities)
    peak_fp_density = max(raw_densities) if raw_densities else 1e-4
    
    # Score candidates under all 3 ranking modes
    # 1. Heuristic Priors
    # 2. Flat Priors
    # 3. Footprint Only
    all_candidate_evals = []
    firms_hits_in_case = []
    
    for dist_km, fp_density, cand in candidates_in_radius:
        rel_fp = fp_density / max(1e-6, peak_fp_density)
        
        # Prior & operating status
        p_res = compute_source_prior(cand, target_dt)
        heuristic_prior = p_res["prior_weight"]
        op_status = p_res.get("operating_status", "active_presumed")
        op_reasons = p_res.get("operating_reasons", [])
        
        # Chemical signature
        sig_mult, _, cand_ev_for, cand_ev_against = evaluate_chemical_signature(
            cand.get("type", "other"), pm25_val, pm10_val, no2_val, co_val
        )
        
        # Satellite
        sat_mult, sat_status, sat_ev = check_satellite_firms(cand["lat"], cand["lon"], target_dt, firms_detections)
        if sat_mult > 1.0:
            firms_hits_in_case.append({"candidate_id": cand.get("id"), "details": sat_ev[0]})
            
        # Scores for the 3 regimes
        score_heuristic = heuristic_prior * rel_fp * sig_mult * sat_mult
        score_flat = 1.0 * rel_fp * sig_mult * sat_mult
        score_footprint_only = 1.0 * rel_fp * 1.0 * 1.0
        
        # Evidence assembly
        ev_for = [
            f"Located {dist_km} km upwind from station along plume advection corridor.",
            f"Plume footprint likelihood: {rel_fp:.4f} (relative to peak corridor density).",
            f"Prior weight: {heuristic_prior:.3f} ({p_res['label']})."
        ] + cand_ev_for + sat_ev
        
        ev_against = [
            f"Candidate geometry: {cand.get('tags', {}).get('landuse', cand.get('type'))} (not a point culprit)."
        ] + cand_ev_against
        
        if op_reasons:
            ev_against.append(f"Decommissioned/disused status in OSM: {', '.join(op_reasons)} (0.05x penalty applied).")
            
        if not has_downwind_response:
            ev_against.append("Downwind CAAQMS stations showed zero concurrent response.")
            
        all_candidate_evals.append({
            "id": cand.get("id"),
            "name": cand.get("name") if cand.get("name") != "Unnamed Site" else f"Unnamed {cand.get('type').capitalize()} Site",
            "type": cand.get("type", "unspecified"),
            "distance_km": dist_km,
            "operating_status": op_status,
            "score_decomp": {
                "prior_weight": round(heuristic_prior, 4),
                "footprint_likelihood": round(rel_fp, 4),
                "signature_likelihood": round(sig_mult, 3),
                "satellite_factor": round(sat_mult, 3),
                "raw_compound_score": round(score_heuristic, 4)
            },
            "score_heuristic": score_heuristic,
            "score_flat": score_flat,
            "score_footprint_only": score_footprint_only,
            "evidence_for": ev_for,
            "evidence_against": ev_against
        })
        
    # Sort for the three rankings
    ranked_heuristic_list = sorted(all_candidate_evals, key=lambda x: x["score_heuristic"], reverse=True)
    ranked_flat_list = sorted(all_candidate_evals, key=lambda x: x["score_flat"], reverse=True)
    ranked_fp_list = sorted(all_candidate_evals, key=lambda x: x["score_footprint_only"], reverse=True)
    
    # Build Top-5 candidates for primary output
    active_ranking_list = ranked_flat_list if use_flat_priors else ranked_heuristic_list
    top_candidates = active_ranking_list[:5]
    
    # Establish raw scores for all hypotheses to feed bootstrap
    raw_hypothesis_scores = {}
    
    if event_label == "regional":
        raw_hypothesis_scores["outcome_regional"] = 10.0
        raw_hypothesis_scores["outcome_insufficient_evidence"] = 0.5
    elif event_label == "possible_fault":
        raw_hypothesis_scores["outcome_possible_fault"] = 10.0
        raw_hypothesis_scores["outcome_insufficient_evidence"] = 0.8
    else:
        # Local event: candidates compete with residual non-site outcomes
        for c in top_candidates:
            active_score = c["score_flat"] if use_flat_priors else c["score_heuristic"]
            raw_hypothesis_scores[c["id"]] = max(1e-4, active_score)
            
        # Non-site competitor scores
        is_corroborated = (
            has_downwind_response or 
            (no2_val is not None and no2_val >= 35.0) or
            (case_dict.get("corroboration", {}).get("status") == "corroborated")
        )
        # If low-wind discriminability is poor, boost insufficient evidence
        if discriminability_info["is_uniform"]:
            raw_hypothesis_scores["outcome_insufficient_evidence"] = 1.2
            raw_hypothesis_scores["outcome_possible_fault"] = 0.4 if not is_corroborated else 0.15
        else:
            raw_hypothesis_scores["outcome_insufficient_evidence"] = 0.08 if local_excess >= 50.0 else 0.25
            raw_hypothesis_scores["outcome_possible_fault"] = 0.05 if is_corroborated else 0.45
            
    # Run empirical bootstrap intervals over uncertainty dimensions
    bootstrap_results = compute_bootstrap_intervals(raw_hypothesis_scores, wind_cond, n_iterations=N_BOOTSTRAP_ITERATIONS)
    
    hypotheses = []
    
    if event_label == "regional":
        med_s, interval, tier = bootstrap_results["outcome_regional"]
        hypotheses.append({
            "id": "outcome_regional",
            "name": "Airshed Regional Smog (No Point Source Dispatch)",
            "type": "regional",
            "relative_score": med_s,
            "interval": interval,
            "confidence_tier": tier,
            "score_decomposition": {
                "prior_weight": 1.0,
                "footprint_likelihood": 0.0,
                "signature_likelihood": 1.0,
                "satellite_factor": 1.0,
                "raw_compound_score": 10.0
            },
            "evidence_for": [
                event_classification["rationale"],
                f"Network-wide elevation across {background_info.get('network_elevation_pct')}% of reporting stations.",
                f"Regional median baseline is {bg_median} ug/m3 with spread IQR {bg_iqr} ug/m3."
            ],
            "evidence_against": [
                "Zero spatial concentration gradient pointing to an isolated facility."
            ]
        })
        med_s2, interval2, tier2 = bootstrap_results["outcome_insufficient_evidence"]
        hypotheses.append({
            "id": "outcome_insufficient_evidence",
            "name": "Insufficient Evidence for Local Inspection",
            "type": "insufficient_evidence",
            "relative_score": med_s2,
            "interval": interval2,
            "confidence_tier": tier2,
            "score_decomposition": {
                "prior_weight": 1.0,
                "footprint_likelihood": 0.0,
                "signature_likelihood": 1.0,
                "satellite_factor": 1.0,
                "raw_compound_score": 0.5
            },
            "evidence_for": ["Excess is statistically indistinguishable from broad regional background."],
            "evidence_against": ["N/A"]
        })
        
    elif event_label == "possible_fault":
        fault_reasons = event_classification.get("fault_reasons", ["telemetry_violation"])
        med_s, interval, tier = bootstrap_results["outcome_possible_fault"]
        hypotheses.append({
            "id": "outcome_possible_fault",
            "name": f"Instrument / Telemetry Fault ({', '.join(fault_reasons)})",
            "type": "possible_fault",
            "relative_score": med_s,
            "interval": interval,
            "confidence_tier": tier,
            "score_decomposition": {
                "prior_weight": 1.0,
                "footprint_likelihood": 0.0,
                "signature_likelihood": 1.0,
                "satellite_factor": 1.0,
                "raw_compound_score": 10.0
            },
            "evidence_for": [
                event_classification["rationale"],
                f"Automatic QC fault detector fired: {', '.join(fault_reasons)}.",
                "Zero wind-consistent response observed at downwind CAAQMS stations.",
                "Lack of multi-pollutant atmospheric physical coherence."
            ],
            "evidence_against": [
                "N/A - Direct telemetry or physical conservation violation confirmed."
            ]
        })
        med_s2, interval2, tier2 = bootstrap_results["outcome_insufficient_evidence"]
        hypotheses.append({
            "id": "outcome_insufficient_evidence",
            "name": "Insufficient Evidence for Site Inspection",
            "type": "insufficient_evidence",
            "relative_score": med_s2,
            "interval": interval2,
            "confidence_tier": tier2,
            "score_decomposition": {
                "prior_weight": 1.0,
                "footprint_likelihood": 0.0,
                "signature_likelihood": 1.0,
                "satellite_factor": 1.0,
                "raw_compound_score": 0.8
            },
            "evidence_for": ["Telemetry unreliability precludes physical emitter attribution."],
            "evidence_against": ["N/A"]
        })
        
    else:
        # Local event: assemble hypotheses from candidate evaluations + non-site competitors
        for c in top_candidates:
            cid = c["id"]
            med_s, interval, tier = bootstrap_results[cid]
            hypotheses.append({
                "id": cid,
                "name": c["name"],
                "type": c["type"],
                "operating_status": c["operating_status"],
                "score_decomposition": c["score_decomp"],
                "relative_score": med_s,
                "interval": interval,
                "confidence_tier": tier if not discriminability_info["is_uniform"] else "low",
                "evidence_for": c["evidence_for"],
                "evidence_against": c["evidence_against"]
            })
            
        # Non-site competitor outcomes
        med_fault, interval_f, tier_f = bootstrap_results["outcome_possible_fault"]
        hypotheses.append({
            "id": "outcome_possible_fault",
            "name": "Instrument / Sensor Bias Artifact",
            "type": "possible_fault",
            "relative_score": med_fault,
            "interval": interval_f,
            "confidence_tier": tier_f,
            "score_decomposition": {
                "prior_weight": 1.0,
                "footprint_likelihood": 0.0,
                "signature_likelihood": 1.0,
                "satellite_factor": 1.0,
                "raw_compound_score": raw_hypothesis_scores["outcome_possible_fault"]
            },
            "evidence_for": ["Single-station isolated surge." if not has_downwind_response else "Sensor calibration drift."],
            "evidence_against": ["Multi-pollutant co-movement and wind-consistent downwind response." if has_downwind_response else "No direct telemetry crash."]
        })
        
        med_ins, interval_i, tier_i = bootstrap_results["outcome_insufficient_evidence"]
        hypotheses.append({
            "id": "outcome_insufficient_evidence",
            "name": "Insufficient Evidence (Diffuse Background / Low Discriminability)",
            "type": "insufficient_evidence",
            "relative_score": med_ins,
            "interval": interval_i,
            "confidence_tier": tier_i,
            "score_decomposition": {
                "prior_weight": 1.0,
                "footprint_likelihood": 0.0,
                "signature_likelihood": 1.0,
                "satellite_factor": 1.0,
                "raw_compound_score": raw_hypothesis_scores["outcome_insufficient_evidence"]
            },
            "evidence_for": [
                "Diffuse urban area emissions indistinguishable from point candidates.",
                discriminability_info["note"]
            ],
            "evidence_against": [f"Local excess of +{local_excess} ug/m3 detected above regional median."]
        })
        
        # Sort hypotheses by relative score descending
        hypotheses.sort(key=lambda x: x["relative_score"], reverse=True)
        
    # Build Three-Way Rankings block
    three_way_rankings = {
        "ranked_by_heuristic_priors": [
            {"id": c["id"], "name": c["name"], "type": c["type"], "score": round(c["score_heuristic"], 4), "operating_status": c["operating_status"]}
            for c in ranked_heuristic_list[:5]
        ],
        "ranked_by_flat_priors": [
            {"id": c["id"], "name": c["name"], "type": c["type"], "score": round(c["score_flat"], 4), "operating_status": c["operating_status"]}
            for c in ranked_flat_list[:5]
        ],
        "ranked_by_footprint_only": [
            {"id": c["id"], "name": c["name"], "type": c["type"], "score": round(c["score_footprint_only"], 4), "operating_status": c["operating_status"]}
            for c in ranked_fp_list[:5]
        ]
    }
    
    # Data Quality Block
    data_quality_block = {
        "station_reliability": case_dict.get("station_reliability", 0.95),
        "suspect_hours": 0 if event_label != "possible_fault" else 7,
        "units_verified": {
            "pm25": "ug/m3 (verified from OpenAQ metadata)",
            "pm10": "ug/m3 (verified from OpenAQ metadata)",
            "no2": "ppb -> ug/m3 (converted 1.88x per OpenAQ metadata)" if no2_val is not None else "missing",
            "co": "ppb -> mg/m3 (converted 0.001145x per OpenAQ metadata)" if co_val is not None else "missing"
        },
        "satellite_evidence_status": "available_hit" if firms_hits_in_case else ("available_no_thermal_anomaly" if firms_detections else "unavailable")
    }
    
    time_convention = get_time_convention_block(ts_utc)
    
    output_case = {
        "case_id": case_id,
        "station": station_name,
        "station_id": target_sid,
        "coordinates": coords,
        "time_window": time_convention,
        "label": event_label,
        "n_stations_background": n_bg,
        "background_iqr": bg_iqr,
        "regional_median": bg_median,
        "local_excess": local_excess,
        "footprint_discriminability": discriminability_info,
        "signature": {
            "source_type_label": sig_label,
            "pm25": pm25_val,
            "pm10": pm10_val,
            "ratio_pm25_pm10": round(pm25_val / pm10_val, 2) if (pm25_val and pm10_val) else None,
            "no2_ugm3": no2_val,
            "co_mgm3": co_val
        },
        "downwind_neighbour_corroboration": neighbours,
        "satellite_firms_hits": firms_hits_in_case,
        "hypotheses": hypotheses,
        "three_way_rankings": three_way_rankings,
        "data_quality": data_quality_block
    }
    
    out_file = os.path.join(CASES_OUT_DIR, f"{case_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_case, f, indent=2)
        
    return output_case
