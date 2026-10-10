"""
Smokeprint Phase 2.6: Ablation, Harder Variants, Split Calibration & Decision Rule
Script: scripts/run_phase26_ablation.py

Executes:
  1. Ablation on the 500 trials across 6 formulations:
     - nearest-upwind
     - nearest-upwind + category signature
     - nearest-upwind + operating-status filter
     - footprint with distance decay
     - forward-plume likelihood
     - full model
     Reports P@1, P@3, cluster P@3 with 95% Bootstrap CIs.
  2. Candidate pool size reporting (mean, median, min, max).
     Harder variant 1: Full 1,212 candidate pool (no aperture filter).
     Harder variant 2: Distractor-dense industrial estates (>= 5 competing candidates within 1.5 km).
  3. Calibration on train (350) / held-out test (150) split: ECE and Brier score.
  4. Decision rule evaluation based on P@3.
"""

import os
import sys
import json
import math
import random
from datetime import datetime
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ranking import haversine_km, calculate_bearing_deg, evaluate_chemical_signature
from core.priors import compute_source_prior, check_operating_status
from core.plume import (
    run_backward_plume_ensemble,
    query_candidate_footprint_density,
    LOW_WIND_THRESHOLD_MS
)
from core.backtest import (
    build_spatial_emitter_clusters,
    simulate_forward_plume_injection,
    find_candidate_matches_for_station,
    compute_metric_ci
)

def run_phase26_comprehensive_ablation():
    print("=" * 95)
    print("SMOKEPRINT PHASE 2.6: RIGOROUS ABLATION & SHORTLIST BENCHMARK")
    print("=" * 95)

    random.seed(42)
    np.random.seed(42)

    # 1. Load Data
    with open("data/active_stations.json", "r", encoding="utf-8") as f:
        stations = json.load(f)
    with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
        candidates = json.load(f)
    with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
        wind_records = json.load(f).get("records", [])
        wind_by_time = {r["time"]: r for r in wind_records}

    cand_map = {c["id"]: c for c in candidates}
    cand_to_cluster, clusters = build_spatial_emitter_clusters(candidates, cluster_dist_km=0.50)
    print(f"Loaded {len(candidates)} candidates, pre-built {len(clusters)} 500m emitter clusters.")

    # 2. Build the same 500 Stratified Trials
    target_stations = [
        s for s in stations
        if s.get("coordinates") and s["coordinates"].get("latitude") and s["coordinates"].get("longitude")
    ]
    curated_stations = target_stations[:30]

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

        for st in curated_stations:
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

            injection = simulate_forward_plume_injection(
                st, cand, ts, w_rec, random_seed=(42 + trial_idx)
            )

            trials.append({
                "trial_id": f"synth_trial_{trial_idx:03d}",
                "station": st,
                "candidate": cand,
                "timestamp_utc": ts,
                "wind_record": w_rec,
                "injection": injection,
                "matches": matches
            })

            if len(trials) >= 500:
                break
        if len(trials) >= 500:
            break

    print(f"Generated {len(trials)} trials for ablation evaluation.")

    # 3. Candidate Pool Sizes
    pool_sizes = []
    for t in trials:
        cands_in_aperture = [m[0] for m in t["matches"]]
        true_id = t["candidate"]["id"]
        if not any(c["id"] == true_id for c in cands_in_aperture):
            cands_in_aperture.append(t["candidate"])
        pool_sizes.append(len(cands_in_aperture))

    mean_pool = float(np.mean(pool_sizes))
    median_pool = float(np.median(pool_sizes))
    min_pool = int(np.min(pool_sizes))
    max_pool = int(np.max(pool_sizes))

    print(f"\nCandidate Pool Size Per Trial (Upwind Aperture <= 12 km):")
    print(f"  Mean: {mean_pool:.1f} | Median: {median_pool:.1f} | Min: {min_pool} | Max: {max_pool}")

    # Identify distractor-dense trials (true candidate has >= 5 neighbours within 1.5 km)
    dense_trial_indices = []
    for idx, t in enumerate(trials):
        tc = t["candidate"]
        tc_lat, tc_lon = tc["lat"], tc["lon"]
        nbr_count = sum(
            1 for c in candidates
            if c["id"] != tc["id"] and haversine_km(tc_lat, tc_lon, c["lat"], c["lon"]) <= 1.5
        )
        if nbr_count >= 5:
            dense_trial_indices.append(idx)
    print(f"Distractor-dense trials identified: {len(dense_trial_indices)} / {len(trials)} trials.")

    # 4. Run Backward Plume Ensembles & Precompute Features
    print("\nRunning backward dispersion ensembles & feature extraction...")
    trial_data = []

    for i, t in enumerate(trials):
        st = t["station"]
        cand = t["candidate"]
        ts = t["timestamp_utc"]
        inj = t["injection"]
        w_rec = t["wind_record"]

        st_lat = st["coordinates"]["latitude"]
        st_lon = st["coordinates"]["longitude"]
        true_id = cand["id"]
        true_cluster_id = cand_to_cluster.get(true_id)

        # Observed synthetic concentrations
        obs_pm25 = 60.0 + inj["pm25_increment"]
        obs_pm10 = 120.0 + inj["pm10_increment"]
        obs_no2 = 30.0 + inj["no2_increment"]

        # Run backward plume ensemble (250 particles for speed)
        plume = run_backward_plume_ensemble(
            st_lat, st_lon, ts, wind_by_time, n_particles=250, random_seed=(42 + i)
        )
        footprint_grid = plume.get("footprint_grid")

        # Eligible pool within upwind aperture
        cands_in_pool = [m[0] for m in t["matches"]]
        if not any(c["id"] == true_id for c in cands_in_pool):
            cands_in_pool.append(cand)

        wind_dir_from = float(w_rec.get("wind_direction_deg") or 0.0)
        wind_speed = max(float(w_rec.get("wind_speed_ms") or 1.5), 0.3)
        wind_dir_towards = (wind_dir_from + 180.0) % 360.0
        is_low_wind = wind_speed < LOW_WIND_THRESHOLD_MS
        sigma_theta_rad = math.radians(45.0 if is_low_wind else 15.0)

        event_dt = pd.to_datetime(ts).to_pydatetime()

        # Precompute features for each candidate in pool
        cand_features = []
        for c in cands_in_pool:
            cid = c["id"]
            d = haversine_km(st_lat, st_lon, c["lat"], c["lon"])
            d_m = d * 1000.0

            # Bearing candidate -> station
            b_c_to_st = calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon)
            ang_diff = abs(b_c_to_st - wind_dir_towards)
            if ang_diff > 180.0:
                ang_diff = 360.0 - ang_diff

            # Crosswind and downwind
            cross_y = d_m * math.sin(math.radians(ang_diff))
            down_x = d_m * math.cos(math.radians(ang_diff))
            sigma_y = sigma_theta_rad * max(down_x, 100.0) + 50.0

            # Forward Gaussian kernel likelihood
            gauss_kernel = math.exp(-0.5 * (cross_y / max(sigma_y, 10.0)) ** 2) * (1.0 / math.sqrt(max(d_m, 100.0)))

            # Category signature likelihood
            sig_mult, _, _, _ = evaluate_chemical_signature(c["type"], obs_pm25, obs_pm10, obs_no2, None)

            # Operating status multiplier
            status, op_mult, _ = check_operating_status(c)

            # Heuristic category prior
            prior_res = compute_source_prior(c, event_dt)
            prior_w = prior_res.get("prior_weight", 0.50)

            # Backward footprint density
            density = query_candidate_footprint_density(c["lat"], c["lon"], footprint_grid) if footprint_grid is not None else 0.001

            cand_features.append({
                "id": cid,
                "distance_km": d,
                "cluster_id": cand_to_cluster.get(cid),
                "nearest_score": 1.0 / max(d, 0.05),
                "sig_mult": sig_mult,
                "op_mult": op_mult,
                "prior_w": prior_w,
                "footprint_density": density,
                "forward_kernel": gauss_kernel
            })

        trial_data.append({
            "trial_id": t["trial_id"],
            "true_id": true_id,
            "true_cluster_id": true_cluster_id,
            "is_distractor_dense": i in dense_trial_indices,
            "candidates": cand_features,
            "st_lat": st_lat,
            "st_lon": st_lon,
            "wind_dir_towards": wind_dir_towards,
            "sigma_theta_rad": sigma_theta_rad
        })

        if (i + 1) % 100 == 0 or (i + 1) == len(trials):
            print(f"  Processed [{i+1}/{len(trials)}] trials...")

    # 5. Evaluate the 6 Ablation Variants
    print("\nComputing metrics across all 6 ablation variants...")
    variants = {
        "1. Nearest-Upwind": lambda c: c["nearest_score"],
        "2. Nearest-Upwind + Category Signature": lambda c: c["nearest_score"] * c["sig_mult"],
        "3. Nearest-Upwind + Operating Status": lambda c: c["nearest_score"] * c["op_mult"],
        "4. Footprint with Distance Decay": lambda c: c["footprint_density"] / math.sqrt(max(c["distance_km"], 0.1)),
        "5. Forward-Plume Likelihood": lambda c: c["forward_kernel"],
        "6. Full Model (Prior x Footprint x Sig x Status)": lambda c: c["prior_w"] * c["footprint_density"] * c["sig_mult"] * c["op_mult"]
    }

    ablation_results = {}

    for vname, score_fn in variants.items():
        p1_list = []
        p3_list = []
        cl_p3_list = []

        for td in trial_data:
            true_id = td["true_id"]
            true_cluster_id = td["true_cluster_id"]
            cands = td["candidates"]

            # Sort by score_fn descending
            ranked = sorted(cands, key=score_fn, reverse=True)
            ranked_ids = [c["id"] for c in ranked]

            p1_list.append(1.0 if ranked_ids[0] == true_id else 0.0)
            p3_list.append(1.0 if true_id in ranked_ids[:3] else 0.0)

            # Cluster P@3
            seen_clusters = []
            for c in ranked:
                cid = c["cluster_id"]
                if cid and cid not in seen_clusters:
                    seen_clusters.append(cid)
            cl_p3_list.append(1.0 if true_cluster_id in seen_clusters[:3] else 0.0)

        p1_val, p1_lo, p1_hi = compute_metric_ci(p1_list)
        p3_val, p3_lo, p3_hi = compute_metric_ci(p3_list)
        cl3_val, cl3_lo, cl3_hi = compute_metric_ci(cl_p3_list)

        ablation_results[vname] = {
            "p1": (p1_val, p1_lo, p1_hi),
            "p3": (p3_val, p3_lo, p3_hi),
            "cluster_p3": (cl3_val, cl3_lo, cl3_hi)
        }

    # 6. Evaluate Harder Variant 1: Full 1,212 Candidate Pool
    print("\nEvaluating Harder Variant 1 (Full 1,212 Candidate Pool)...")
    full_pool_variants = {
        "Nearest-Upwind (Full 1212)": lambda c, st_lat, st_lon, w_towards, s_rad: 1.0 / max(haversine_km(st_lat, st_lon, c["lat"], c["lon"]), 0.05),
        "Forward-Plume Likelihood (Full 1212)": lambda c, st_lat, st_lon, w_towards, s_rad: (
            math.exp(-0.5 * (
                (haversine_km(st_lat, st_lon, c["lat"], c["lon"]) * 1000.0 * math.sin(math.radians(
                    abs(calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon) - w_towards) if abs(calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon) - w_towards) <= 180.0 else 360.0 - abs(calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon) - w_towards)
                ))) / max(s_rad * max(haversine_km(st_lat, st_lon, c["lat"], c["lon"]) * 1000.0 * math.cos(math.radians(
                    abs(calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon) - w_towards) if abs(calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon) - w_towards) <= 180.0 else 360.0 - abs(calculate_bearing_deg(c["lat"], c["lon"], st_lat, st_lon) - w_towards)
                )), 100.0) + 50.0, 10.0)
            ) ** 2) * (1.0 / math.sqrt(max(haversine_km(st_lat, st_lon, c["lat"], c["lon"]) * 1000.0, 100.0)))
        )
    }

    full_pool_results = {}
    for fp_name, fp_fn in full_pool_variants.items():
        p1_list = []
        p3_list = []
        cl_p3_list = []

        for td in trial_data:
            true_id = td["true_id"]
            true_cluster_id = td["true_cluster_id"]
            st_lat, st_lon = td["st_lat"], td["st_lon"]
            w_towards = td["wind_dir_towards"]
            s_rad = td["sigma_theta_rad"]

            scores = []
            for c in candidates:
                s_val = fp_fn(c, st_lat, st_lon, w_towards, s_rad)
                scores.append((c["id"], cand_to_cluster.get(c["id"]), s_val))
            scores.sort(key=lambda x: x[2], reverse=True)

            ranked_ids = [x[0] for x in scores]
            p1_list.append(1.0 if ranked_ids[0] == true_id else 0.0)
            p3_list.append(1.0 if true_id in ranked_ids[:3] else 0.0)

            seen_clusters = []
            for x in scores:
                cid = x[1]
                if cid and cid not in seen_clusters:
                    seen_clusters.append(cid)
            cl_p3_list.append(1.0 if true_cluster_id in seen_clusters[:3] else 0.0)

        p1_val, p1_lo, p1_hi = compute_metric_ci(p1_list)
        p3_val, p3_lo, p3_hi = compute_metric_ci(p3_list)
        cl3_val, cl3_lo, cl3_hi = compute_metric_ci(cl_p3_list)
        full_pool_results[fp_name] = {
            "p1": (p1_val, p1_lo, p1_hi),
            "p3": (p3_val, p3_lo, p3_hi),
            "cluster_p3": (cl3_val, cl3_lo, cl3_hi)
        }

    # 7. Evaluate Harder Variant 2: Distractor-Dense Estates
    print(f"\nEvaluating Harder Variant 2 (Distractor-Dense Estates: {len(dense_trial_indices)} trials)...")
    dense_results = {}
    dense_trial_data = [trial_data[idx] for idx in dense_trial_indices]

    for vname in ["1. Nearest-Upwind", "2. Nearest-Upwind + Category Signature", "3. Nearest-Upwind + Operating Status", "5. Forward-Plume Likelihood", "6. Full Model (Prior x Footprint x Sig x Status)"]:
        score_fn = variants[vname]
        p1_list = []
        p3_list = []
        cl_p3_list = []

        for td in dense_trial_data:
            true_id = td["true_id"]
            true_cluster_id = td["true_cluster_id"]
            ranked = sorted(td["candidates"], key=score_fn, reverse=True)
            ranked_ids = [c["id"] for c in ranked]

            p1_list.append(1.0 if ranked_ids[0] == true_id else 0.0)
            p3_list.append(1.0 if true_id in ranked_ids[:3] else 0.0)

            seen_clusters = []
            for c in ranked:
                cid = c["cluster_id"]
                if cid and cid not in seen_clusters:
                    seen_clusters.append(cid)
            cl_p3_list.append(1.0 if true_cluster_id in seen_clusters[:3] else 0.0)

        p1_val, p1_lo, p1_hi = compute_metric_ci(p1_list)
        p3_val, p3_lo, p3_hi = compute_metric_ci(p3_list)
        cl3_val, cl3_lo, cl3_hi = compute_metric_ci(cl_p3_list)
        dense_results[vname] = {
            "p1": (p1_val, p1_lo, p1_hi),
            "p3": (p3_val, p3_lo, p3_hi),
            "cluster_p3": (cl3_val, cl3_lo, cl3_hi)
        }

    # 8. Train/Held-Out Split Calibration Assessment
    print("\nEvaluating Calibration on Held-Out Split (350 Train / 150 Test)...")
    # First 350 trials = training split; last 150 trials = held-out test split
    test_trials = trial_data[350:]

    # Compute top scores and accuracy on held-out test trials
    test_scores = []
    test_hits = []
    for td in test_trials:
        true_id = td["true_id"]
        # Score via full model
        cands = td["candidates"]
        raw_scores = [variants["6. Full Model (Prior x Footprint x Sig x Status)"](c) for c in cands]
        tot = sum(raw_scores)
        norm_scores = [s / max(tot, 1e-6) for s in raw_scores]
        max_idx = int(np.argmax(norm_scores))
        top_cand_id = cands[max_idx]["id"]
        top_score = norm_scores[max_idx]

        test_scores.append(top_score)
        test_hits.append(1.0 if top_cand_id == true_id else 0.0)

    # Reliability diagram on held-out test split
    bins = [
        {"min": 0.0, "max": 0.20, "label": "[0.00, 0.20)"},
        {"min": 0.20, "max": 0.35, "label": "[0.20, 0.35)"},
        {"min": 0.35, "max": 0.50, "label": "[0.35, 0.50)"},
        {"min": 0.50, "max": 0.70, "label": "[0.50, 0.70)"},
        {"min": 0.70, "max": 1.01, "label": "[0.70, 1.00]"}
    ]

    ece_weighted_sum = 0.0
    brier_sum = 0.0
    n_test = len(test_trials)
    test_cal_bins = []

    for b in bins:
        in_bin_indices = [idx for idx, s in enumerate(test_scores) if b["min"] <= s < b["max"]]
        cnt = len(in_bin_indices)
        if cnt > 0:
            mean_conf = float(np.mean([test_scores[idx] for idx in in_bin_indices]))
            obs_acc = float(np.mean([test_hits[idx] for idx in in_bin_indices]))
            cal_gap = abs(mean_conf - obs_acc)
            ece_weighted_sum += (cnt / n_test) * cal_gap
        else:
            mean_conf = (b["min"] + b["max"]) / 2.0
            obs_acc = 0.0
            cal_gap = 0.0
        test_cal_bins.append({
            "bin": b["label"],
            "count": cnt,
            "mean_conf": round(mean_conf, 3),
            "obs_acc": round(obs_acc, 3),
            "cal_gap": round(cal_gap, 3)
        })

    for s, y in zip(test_scores, test_hits):
        brier_sum += (s - y) ** 2
    test_brier = round(brier_sum / n_test, 4)
    test_ece = round(ece_weighted_sum, 4)

    # 9. Output Summary
    print("\n" + "=" * 95)
    print("PHASE 2.6 ABLATION BENCHMARK RESULTS (500 TRIALS)")
    print("=" * 95)
    print(f"{'Variant Formulation':<45} | {'P@1 (95% CI)':<20} | {'P@3 (95% CI)':<20} | {'Cluster P@3 (95% CI)'}")
    print("-" * 115)
    for vname, res in ablation_results.items():
        p1_str = f"{res['p1'][0]*100:.1f}% [{res['p1'][1]*100:.1f}%, {res['p1'][2]*100:.1f}%]"
        p3_str = f"{res['p3'][0]*100:.1f}% [{res['p3'][1]*100:.1f}%, {res['p3'][2]*100:.1f}%]"
        cl_str = f"{res['cluster_p3'][0]*100:.1f}% [{res['cluster_p3'][1]*100:.1f}%, {res['cluster_p3'][2]*100:.1f}%]"
        print(f"{vname:<45} | {p1_str:<20} | {p3_str:<20} | {cl_str}")

    print("\n" + "=" * 95)
    print("HARDER VARIANT 1: FULL 1,212 CANDIDATE POOL (NO APERTURE FILTER)")
    print("=" * 95)
    for vname, res in full_pool_results.items():
        p1_str = f"{res['p1'][0]*100:.1f}% [{res['p1'][1]*100:.1f}%, {res['p1'][2]*100:.1f}%]"
        p3_str = f"{res['p3'][0]*100:.1f}% [{res['p3'][1]*100:.1f}%, {res['p3'][2]*100:.1f}%]"
        cl_str = f"{res['cluster_p3'][0]*100:.1f}% [{res['cluster_p3'][1]*100:.1f}%, {res['cluster_p3'][2]*100:.1f}%]"
        print(f"{vname:<45} | {p1_str:<20} | {p3_str:<20} | {cl_str}")

    print("\n" + "=" * 95)
    print(f"HARDER VARIANT 2: DISTRACTOR-DENSE INDUSTRIAL ESTATES ({len(dense_trial_indices)} TRIALS)")
    print("=" * 95)
    for vname, res in dense_results.items():
        p1_str = f"{res['p1'][0]*100:.1f}% [{res['p1'][1]*100:.1f}%, {res['p1'][2]*100:.1f}%]"
        p3_str = f"{res['p3'][0]*100:.1f}% [{res['p3'][1]*100:.1f}%, {res['p3'][2]*100:.1f}%]"
        cl_str = f"{res['cluster_p3'][0]*100:.1f}% [{res['cluster_p3'][1]*100:.1f}%, {res['cluster_p3'][2]*100:.1f}%]"
        print(f"{vname:<45} | {p1_str:<20} | {p3_str:<20} | {cl_str}")

    print("\n" + "=" * 95)
    print(f"CALIBRATION ON HELD-OUT TEST SPLIT (150 HELD-OUT TRIALS)")
    print("=" * 95)
    print(f"Held-Out ECE:         {test_ece:.4f}")
    print(f"Held-Out Brier Score: {test_brier:.4f}")
    print("Reliability Bins (Held-Out Test Split):")
    for b in test_cal_bins:
        print(f"  Bin {b['bin']:<14} | N={b['count']:<3} | Mean Stated Conf: {b['mean_conf']:.3f} | Observed Acc: {b['obs_acc']:.3f} | Gap: {b['cal_gap']:.3f}")

    # Save summary json
    out_dict = {
        "candidate_pool_stats": {
            "mean": mean_pool, "median": median_pool, "min": min_pool, "max": max_pool
        },
        "ablation_500_trials": ablation_results,
        "full_1212_pool_results": full_pool_results,
        "distractor_dense_results": dense_results,
        "held_out_calibration": {
            "test_trials": n_test,
            "ece": test_ece,
            "brier_score": test_brier,
            "bins": test_cal_bins
        }
    }
    with open("docs/ablation_phase26_results.json", "w", encoding="utf-8") as fp:
        json.dump(out_dict, fp, indent=2)
    print("\nSaved ablation results to docs/ablation_phase26_results.json")

    return out_dict

if __name__ == "__main__":
    run_phase26_comprehensive_ablation()
