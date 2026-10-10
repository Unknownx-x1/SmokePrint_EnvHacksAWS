"""
Smokeprint Phase 2.7: Mismatch Test & Physics-Perturbation Benchmark
Script: scripts/run_mismatch_test.py

Evaluates ranking robustness under model/physics mismatch:
  1. Injections generated with a DIFFERENT dispersion setup:
     - Briggs Urban sigma_y / sigma_z parameterisation (different lateral/vertical spread)
     - Nocturnal stable (Class E/F) vs convective (Class B/C) stability dynamics
     - Plume-rise term: effective emission release height Heff = Hs + Delta H (elevated stack emission with ground touchdown)
     - Wind perturbation: direction bias drawn from Uniform(-20 deg, +20 deg), speed perturbation drawn from Uniform(-30%, +30%)
  2. Scoring performed strictly with the CURRENT forward-plume kernel (unperturbed ERA5 wind, zero plume-rise assumption).
  3. Ranking formulation: forward_plume_likelihood * signature_gating * status_filter (category priors removed from score; tiebreaker only).
  4. 500 trials evaluated: P@1, P@3, Cluster P@3 with 95% bootstrap CIs against nearest-upwind.
  5. Full-catalog variant evaluated on all 1,212 candidates.
"""

import os
import sys
import json
import math
import random
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ranking import haversine_km, calculate_bearing_deg, evaluate_chemical_signature
from core.priors import compute_source_prior, check_operating_status
from core.plume import LOW_WIND_THRESHOLD_MS
from core.backtest import (
    build_spatial_emitter_clusters,
    find_candidate_matches_for_station,
    compute_metric_ci
)

def simulate_mismatched_forward_injection(
    station_meta: Dict[str, Any],
    candidate_meta: Dict[str, Any],
    timestamp_utc: str,
    wind_record: Dict[str, Any],
    random_seed: int
) -> Dict[str, Any]:
    """
    Generates synthetic plume injection with MISMATCHED dispersion physics:
      - Perturbed wind: direction +/-20 deg, speed +/-30%
      - Briggs Urban dispersion sigma_y, sigma_z
      - Effective release height / plume rise Heff (30 - 75 m)
      - Stability class (Class E / F nocturnal stable)
    """
    rng = np.random.RandomState(random_seed)
    
    st_lat = station_meta["coordinates"]["latitude"]
    st_lon = station_meta["coordinates"]["longitude"]
    c_lat = candidate_meta["lat"]
    c_lon = candidate_meta["lon"]
    source_type = candidate_meta["type"]

    dist_km = haversine_km(c_lat, c_lon, st_lat, st_lon)
    dist_m = max(dist_km * 1000.0, 50.0)

    bearing_cand_to_st = calculate_bearing_deg(c_lat, c_lon, st_lat, st_lon)

    # Base wind from ERA5
    base_wind_from = float(wind_record.get("wind_direction_deg") or 0.0)
    base_wind_speed = max(float(wind_record.get("wind_speed_ms") or 1.5), 0.3)

    # 1. Wind Perturbations: +/-20 deg direction, +/-30% speed
    wind_dir_bias = rng.uniform(-20.0, 20.0)
    wind_speed_scale = rng.uniform(0.70, 1.30)

    true_wind_from = (base_wind_from + wind_dir_bias) % 360.0
    true_wind_towards = (true_wind_from + 180.0) % 360.0
    true_wind_speed = max(base_wind_speed * wind_speed_scale, 0.4)

    # 2. Angular offset under true perturbed wind
    ang_diff = abs(bearing_cand_to_st - true_wind_towards)
    if ang_diff > 180.0:
        ang_diff = 360.0 - ang_diff

    crosswind_y = dist_m * math.sin(math.radians(ang_diff))
    downwind_x = max(dist_m * math.cos(math.radians(ang_diff)), 20.0)

    # 3. Briggs Urban dispersion parameterisation (mismatched from standard rural power-law)
    # Urban nocturnal/moderately stable:
    sigma_y_briggs = 0.32 * downwind_x * (1.0 + 0.0004 * downwind_x) ** (-0.5)
    sigma_z_briggs = 0.24 * downwind_x * (1.0 + 0.001 * downwind_x) ** (0.5)
    sigma_y_briggs = max(sigma_y_briggs, 30.0)
    sigma_z_briggs = max(sigma_z_briggs, 15.0)

    # 4. Plume Rise Term (effective release height Heff)
    if source_type in ["industrial", "brick_kiln"]:
        # Elevated thermal buoyant stack
        stack_h = 35.0
        buoyancy_flux = 15.0  # m4/s3
        plume_rise_dh = min(50.0, (1.6 * (buoyancy_flux ** (1/3)) * (downwind_x ** (2/3))) / max(true_wind_speed, 1.0))
        h_eff = stack_h + plume_rise_dh
    else:
        # Ground-level / diffuse fugitive source
        h_eff = 5.0

    # Ground-level Gaussian concentration with elevated source touchdown:
    # C(x, y, 0) = Q / (2 pi u sigma_y sigma_z) * exp(-0.5*(y/sigma_y)^2) * exp(-0.5*(h_eff/sigma_z)^2)
    lat_gauss = math.exp(-0.5 * (crosswind_y / sigma_y_briggs) ** 2)
    vert_gauss = math.exp(-0.5 * (h_eff / sigma_z_briggs) ** 2)
    
    dilution = 1.0 / (2.0 * math.pi * true_wind_speed * sigma_y_briggs * sigma_z_briggs)
    # Scale injection increment
    base_increment = 2.5e6 * dilution * lat_gauss * vert_gauss
    pm25_increment = max(30.0, min(320.0, round(base_increment + rng.normal(0, 8.0), 1)))

    # Signature increments
    if source_type == "brick_kiln":
        ratio_target = float(rng.normal(0.72, 0.03))
        no2_inc = float(rng.normal(14.0, 3.0))
    elif source_type == "landfill":
        ratio_target = float(rng.normal(0.66, 0.03))
        no2_inc = float(rng.normal(8.0, 2.0))
    elif source_type == "industrial":
        ratio_target = float(rng.normal(0.62, 0.03))
        no2_inc = float(rng.normal(48.0, 8.0))
    elif source_type == "construction":
        ratio_target = float(rng.normal(0.24, 0.02))
        no2_inc = float(rng.normal(4.0, 1.5))
    else:  # quarry
        ratio_target = float(rng.normal(0.19, 0.02))
        no2_inc = float(rng.normal(2.5, 1.0))

    ratio_target = max(0.12, min(0.92, ratio_target))
    pm10_increment = round(pm25_increment / ratio_target, 1)

    return {
        "pm25_increment": pm25_increment,
        "pm10_increment": pm10_increment,
        "no2_increment": round(max(0.0, no2_inc), 1),
        "true_wind_from": true_wind_from,
        "true_wind_speed": true_wind_speed,
        "wind_dir_bias": wind_dir_bias,
        "wind_speed_scale": wind_speed_scale,
        "h_eff": round(h_eff, 1)
    }

def run_mismatch_benchmark():
    print("=" * 95)
    print("PHASE 2.7: MISMATCH BENCHMARK (PHYSICS PERTURBATIONS & ROBUSTNESS AUDIT)")
    print("=" * 95)

    random.seed(142)
    np.random.seed(142)

    # Load canonical catalogs
    with open("data/active_stations.json", "r", encoding="utf-8") as f:
        stations = json.load(f)
    with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
        candidates = json.load(f)
    with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
        wind_records = json.load(f).get("records", [])
        wind_by_time = {r["time"]: r for r in wind_records}

    cand_to_cluster, clusters = build_spatial_emitter_clusters(candidates, cluster_dist_km=0.50)
    print(f"Loaded {len(candidates)} candidates, {len(clusters)} 500m clusters.")

    target_stations = [
        s for s in stations
        if s.get("coordinates") and s["coordinates"].get("latitude") and s["coordinates"].get("longitude")
    ][:30]

    step = max(1, len(wind_records) // 310)
    sampled_timestamps = [wind_records[idx]["time"] + ":00Z" for idx in range(0, len(wind_records), step)]

    source_type_quotas = {
        "industrial": 150,
        "brick_kiln": 120,
        "landfill": 90,
        "construction": 80,
        "quarry": 60
    }
    source_type_counts = {k: 0 for k in source_type_quotas}

    trials = []
    trial_idx = 0

    for ts in sampled_timestamps:
        w_rec = wind_by_time.get(ts[:16])
        if not w_rec:
            continue

        for st in target_stations:
            matches = find_candidate_matches_for_station(st, candidates, w_rec)
            if not matches:
                continue

            picked = None
            for cand, dist_km, ang_diff in matches:
                ctype = cand["type"]
                if source_type_counts[ctype] < source_type_quotas[ctype]:
                    picked = (cand, dist_km, ang_diff)
                    break

            if not picked:
                matches_sorted = sorted(matches, key=lambda m: source_type_counts.get(m[0]["type"], 999))
                picked = matches_sorted[0]

            cand, dist_km, ang_diff = picked
            ctype = cand["type"]
            source_type_counts[ctype] += 1
            trial_idx += 1

            mismatched_inj = simulate_mismatched_forward_injection(
                st, cand, ts, w_rec, random_seed=(142 + trial_idx)
            )

            trials.append({
                "trial_id": f"mismatch_trial_{trial_idx:03d}",
                "station": st,
                "candidate": cand,
                "timestamp_utc": ts,
                "wind_record": w_rec,
                "injection": mismatched_inj,
                "matches": matches
            })

            if len(trials) >= 500:
                break
        if len(trials) >= 500:
            break

    print(f"Generated {len(trials)} trials under MISMATCHED physics (wind perturbation +/-20 deg, speed +/-30%, Briggs urban, plume rise).")

    # Scorer setup: Scorer ONLY has the unperturbed ERA5 wind and standard forward kernel
    print("\nEvaluating scoring on mismatched trials...")
    
    # 1. Base Pool (aperture <= 12 km)
    # 2. Full Catalog Pool (N = 1,212)
    
    results = {
        "base_nearest_upwind": {"p1": [], "p3": [], "cl_p3": []},
        "base_shortlist_score": {"p1": [], "p3": [], "cl_p3": []},  # forward_plume * sig_gating * status_filter (priors tiebreaker only)
        "base_forward_plume_only": {"p1": [], "p3": [], "cl_p3": []},
        "full_nearest_upwind": {"p1": [], "p3": [], "cl_p3": []},
        "full_shortlist_score": {"p1": [], "p3": [], "cl_p3": []}
    }

    for i, t in enumerate(trials):
        st = t["station"]
        cand = t["candidate"]
        inj = t["injection"]
        w_rec = t["wind_record"]
        st_lat = st["coordinates"]["latitude"]
        st_lon = st["coordinates"]["longitude"]
        true_id = cand["id"]
        true_cluster_id = cand_to_cluster.get(true_id)

        obs_pm25 = 60.0 + inj["pm25_increment"]
        obs_pm10 = 120.0 + inj["pm10_increment"]
        obs_no2 = 30.0 + inj["no2_increment"]

        # Scorer wind (UNPERTURBED ERA5)
        wind_dir_from = float(w_rec.get("wind_direction_deg") or 0.0)
        wind_speed = max(float(w_rec.get("wind_speed_ms") or 1.5), 0.3)
        wind_dir_towards = (wind_dir_from + 180.0) % 360.0
        is_low_wind = wind_speed < LOW_WIND_THRESHOLD_MS
        sigma_theta_rad = math.radians(45.0 if is_low_wind else 15.0)

        # Base pool candidates
        cands_in_pool = [m[0] for m in t["matches"]]
        if not any(c["id"] == true_id for c in cands_in_pool):
            cands_in_pool.append(cand)

        def score_candidate(c: Dict[str, Any]) -> Dict[str, float]:
            d = haversine_km(st_lat, st_lon, c["lat"], c["lon"])
            d_m = max(d * 1000.0, 50.0)
            b_c_to_st = calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon)
            ang_diff = abs(b_c_to_st - wind_dir_towards)
            if ang_diff > 180.0:
                ang_diff = 360.0 - ang_diff
            
            cross_y = d_m * math.sin(math.radians(ang_diff))
            down_x = max(d_m * math.cos(math.radians(ang_diff)), 20.0)
            sigma_y = sigma_theta_rad * down_x + 50.0

            # Forward Gaussian advection kernel (scorer formulation)
            gauss_kernel = math.exp(-0.5 * (cross_y / max(sigma_y, 10.0)) ** 2) * (1.0 / math.sqrt(d_m))
            
            # Signature gating
            sig_mult, _, _, _ = evaluate_chemical_signature(c["type"], obs_pm25, obs_pm10, obs_no2, None)
            
            # Status filter
            _, op_mult, _ = check_operating_status(c)

            # Nearest score (upwind-weighted distance)
            nearest_score = 1.0 / max(d, 0.05)

            # Category prior (strictly tiebreaker)
            event_dt = pd.to_datetime(t["timestamp_utc"]).to_pydatetime()
            prior_res = compute_source_prior(c, event_dt)
            prior_tiebreaker = prior_res.get("prior_weight", 0.50)

            # Phase 2.7 Shortlist Score: forward_kernel * sig_mult * op_mult
            shortlist_score = gauss_kernel * sig_mult * op_mult

            return {
                "id": c["id"],
                "cluster_id": cand_to_cluster.get(c["id"]),
                "distance_km": d,
                "nearest_score": nearest_score,
                "gauss_kernel": gauss_kernel,
                "shortlist_score": shortlist_score,
                "prior_tiebreaker": prior_tiebreaker
            }

        # 1. Base Pool Scoring
        base_cand_scores = [score_candidate(c) for c in cands_in_pool]

        # Evaluate Nearest-Upwind
        ranked_nu = sorted(base_cand_scores, key=lambda x: (x["nearest_score"], x["prior_tiebreaker"]), reverse=True)
        nu_ids = [c["id"] for c in ranked_nu]
        results["base_nearest_upwind"]["p1"].append(1.0 if nu_ids[0] == true_id else 0.0)
        results["base_nearest_upwind"]["p3"].append(1.0 if true_id in nu_ids[:3] else 0.0)
        
        seen_cl = []
        for c in ranked_nu:
            cid = c["cluster_id"]
            if cid and cid not in seen_cl:
                seen_cl.append(cid)
            if len(seen_cl) == 3:
                break
        results["base_nearest_upwind"]["cl_p3"].append(1.0 if true_cluster_id in seen_cl else 0.0)

        # Evaluate Forward Plume Only
        ranked_fp = sorted(base_cand_scores, key=lambda x: (x["gauss_kernel"], x["prior_tiebreaker"]), reverse=True)
        fp_ids = [c["id"] for c in ranked_fp]
        results["base_forward_plume_only"]["p1"].append(1.0 if fp_ids[0] == true_id else 0.0)
        results["base_forward_plume_only"]["p3"].append(1.0 if true_id in fp_ids[:3] else 0.0)
        seen_cl_fp = []
        for c in ranked_fp:
            cid = c["cluster_id"]
            if cid and cid not in seen_cl_fp:
                seen_cl_fp.append(cid)
            if len(seen_cl_fp) == 3:
                break
        results["base_forward_plume_only"]["cl_p3"].append(1.0 if true_cluster_id in seen_cl_fp else 0.0)

        # Evaluate Shortlist Score (Forward-Plume * Sig * Status, with Prior tiebreaker)
        ranked_sl = sorted(base_cand_scores, key=lambda x: (x["shortlist_score"], x["prior_tiebreaker"]), reverse=True)
        sl_ids = [c["id"] for c in ranked_sl]
        results["base_shortlist_score"]["p1"].append(1.0 if sl_ids[0] == true_id else 0.0)
        results["base_shortlist_score"]["p3"].append(1.0 if true_id in sl_ids[:3] else 0.0)
        seen_cl_sl = []
        for c in ranked_sl:
            cid = c["cluster_id"]
            if cid and cid not in seen_cl_sl:
                seen_cl_sl.append(cid)
            if len(seen_cl_sl) == 3:
                break
        results["base_shortlist_score"]["cl_p3"].append(1.0 if true_cluster_id in seen_cl_sl else 0.0)

        # 2. Full 1,212 Catalog Scoring
        full_cand_scores = [score_candidate(c) for c in candidates]
        
        # Nearest-upwind on full catalog
        ranked_full_nu = sorted(full_cand_scores, key=lambda x: (x["nearest_score"], x["prior_tiebreaker"]), reverse=True)
        full_nu_ids = [c["id"] for c in ranked_full_nu]
        results["full_nearest_upwind"]["p1"].append(1.0 if full_nu_ids[0] == true_id else 0.0)
        results["full_nearest_upwind"]["p3"].append(1.0 if true_id in full_nu_ids[:3] else 0.0)
        seen_cl_fnu = []
        for c in ranked_full_nu:
            cid = c["cluster_id"]
            if cid and cid not in seen_cl_fnu:
                seen_cl_fnu.append(cid)
            if len(seen_cl_fnu) == 3:
                break
        results["full_nearest_upwind"]["cl_p3"].append(1.0 if true_cluster_id in seen_cl_fnu else 0.0)

        # Shortlist score on full catalog
        ranked_full_sl = sorted(full_cand_scores, key=lambda x: (x["shortlist_score"], x["prior_tiebreaker"]), reverse=True)
        full_sl_ids = [c["id"] for c in ranked_full_sl]
        results["full_shortlist_score"]["p1"].append(1.0 if full_sl_ids[0] == true_id else 0.0)
        results["full_shortlist_score"]["p3"].append(1.0 if true_id in full_sl_ids[:3] else 0.0)
        seen_cl_fsl = []
        for c in ranked_full_sl:
            cid = c["cluster_id"]
            if cid and cid not in seen_cl_fsl:
                seen_cl_fsl.append(cid)
            if len(seen_cl_fsl) == 3:
                break
        results["full_shortlist_score"]["cl_p3"].append(1.0 if true_cluster_id in seen_cl_fsl else 0.0)

        if (i + 1) % 100 == 0:
            print(f"  Processed [{i+1}/500] trials...")

    # Compute 95% Bootstrap CIs
    print("\n" + "=" * 95)
    print("MISMATCH BENCHMARK RESULTS (500 TRIALS UNDER PERTURBED DISPERSION)")
    print("=" * 95)
    print(f"{'Variant Formulation':<45} | {'P@1 (95% CI)':<22} | {'P@3 (95% CI)':<22} | {'Cluster P@3 (95% CI)'}")
    print("-" * 115)

    summary_table = {}
    for key, label in [
        ("base_nearest_upwind", "1. Nearest-Upwind (Base Pool)"),
        ("base_forward_plume_only", "2. Forward-Plume Likelihood Only"),
        ("base_shortlist_score", "3. Phase 2.7 Shortlist Score (Plume x Sig x Status)"),
        ("full_nearest_upwind", "4. Full 1,212 Catalog: Nearest-Upwind"),
        ("full_shortlist_score", "5. Full 1,212 Catalog: Phase 2.7 Shortlist Score")
    ]:
        p1_pt, p1_lo, p1_hi = compute_metric_ci(results[key]["p1"])
        p3_pt, p3_lo, p3_hi = compute_metric_ci(results[key]["p3"])
        cl_pt, cl_lo, cl_hi = compute_metric_ci(results[key]["cl_p3"])

        p1_str = f"{p1_pt*100:.1f}% [{p1_lo*100:.1f}%, {p1_hi*100:.1f}%]"
        p3_str = f"{p3_pt*100:.1f}% [{p3_lo*100:.1f}%, {p3_hi*100:.1f}%]"
        cl_str = f"{cl_pt*100:.1f}% [{cl_lo*100:.1f}%, {cl_hi*100:.1f}%]"
        print(f"{label:<45} | {p1_str:<22} | {p3_str:<22} | {cl_str}")

        summary_table[key] = {
            "label": label,
            "p1": [p1_pt, p1_lo, p1_hi],
            "p3": [p3_pt, p3_lo, p3_hi],
            "cluster_p3": [cl_pt, cl_lo, cl_hi]
        }

    # Save results
    out_path = "docs/mismatch_phase27_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary_table, f, indent=2)
    print(f"\nSaved benchmark results to {out_path}")

if __name__ == "__main__":
    run_mismatch_benchmark()
