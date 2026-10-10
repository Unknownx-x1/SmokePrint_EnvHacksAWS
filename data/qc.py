"""
Smokeprint Quality Control (QC) Pipeline (Upgraded v1.0 / Phase 1)
Applies rigorous physical, telemetry, resolution-aware, and fault-detection checks
before spike detection and source attribution.
Integrated with core.qc_faults and core.units.
"""

import os
import sys
import json
import glob
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import zoneinfo

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.qc_faults import detect_all_faults
from core.units import load_sensor_metadata_registry, verify_and_convert_reading

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# Physical Bounds
PM25_MIN, PM25_MAX = 0.0, 1500.0  # ug/m3
PM10_MIN, PM10_MAX = 0.0, 2000.0  # ug/m3
NO2_MIN, NO2_MAX = 0.0, 1000.0    # ug/m3
CO_MIN, CO_MAX = 0.0, 50.0        # mg/m3

# Flatline thresholds
FINE_FLATLINE_HOURS = 6     # For fine-resolution floats (PM, NO2)
COARSE_FLATLINE_HOURS = 24  # For quantized / coarse telemetry

def detect_flatlines_resolution_aware(series: pd.Series) -> pd.Series:
    """
    Resolution-aware flatline detector:
      - Determines if data is coarse/quantized (step size >= 0.01) or continuous float.
      - For coarse resolution, requires >= 24 consecutive hours to flag as stuck telemetry.
      - For fine resolution, flags >= 6 consecutive hours.
      - Preserves legitimate atmospheric stability without false-flagging.
    """
    is_flat = pd.Series(False, index=series.index)
    clean_s = series.dropna()
    if len(clean_s) < 6:
        return is_flat
        
    diffs = clean_s.diff().abs()
    diffs = diffs[diffs > 1e-5]
    min_step = diffs.quantile(0.05) if not diffs.empty else 0.1
    
    threshold = COARSE_FLATLINE_HOURS if min_step >= 0.01 else FINE_FLATLINE_HOURS
    
    values = series.values
    n = len(values)
    i = 0
    while i < n:
        if np.isnan(values[i]):
            i += 1
            continue
        j = i
        while j < n and not np.isnan(values[j]) and abs(values[j] - values[i]) < 1e-6:
            j += 1
        run_len = j - i
        if run_len >= threshold:
            is_flat.iloc[i:j] = True
        i = j
    return is_flat

def run_qc_on_station(station_dict: dict, registry: dict = None):
    """
    Applies complete QC pipeline:
      1. Unit verification strictly from OpenAQ sensor metadata (core.units)
      2. Negative & physical range bounds
      3. Resolution-aware flatline detection
      4. Automatic fault detectors from core.qc_faults:
         - PM2.5 > PM10 violations (+/- 3h suspect window)
         - Constant PM2.5/PM10 ratio lock (>= 3h)
         - Abrupt collapse to 0/NaN after extreme peak
         - Repeated identical high concentrations
      5. Station reliability scoring encompassing all detectors
      6. IST & UTC timestamping
    """
    if registry is None:
        registry = load_sensor_metadata_registry()
        
    station_id = station_dict["station_id"]
    name = station_dict["name"]
    raw_data = station_dict.get("data", {})
    sensors = station_dict.get("sensors", {})
    
    dfs = {}
    unit_stats = {}
    excluded_sensors = []
    
    for param in ["pm25", "pm10", "no2", "co"]:
        p_data = raw_data.get(param, {})
        sensor_id = sensors.get(param)
        
        if p_data:
            s = pd.Series(p_data, name=param)
            s.index = pd.to_datetime(s.index, utc=True)
            s = s.sort_index()
            
            # Unit check & conversion
            conv_vals = []
            target_unit = "unknown"
            sensor_valid = True
            log_msg = None
            
            # Check unit using first non-null reading
            first_val = s.dropna().iloc[0] if not s.dropna().empty else None
            _, t_unit, is_val, msg = verify_and_convert_reading(first_val, param, sensor_id, registry)
            if not is_val:
                excluded_sensors.append({"param": param, "sensor_id": sensor_id, "reason": msg})
                continue
                
            target_unit = t_unit
            meta_unit = registry.get(sensor_id, {}).get("units", "unknown") if sensor_id else "unknown"
            
            for v in s.values:
                if pd.isna(v):
                    conv_vals.append(np.nan)
                else:
                    cv, _, _, _ = verify_and_convert_reading(v, param, sensor_id, registry)
                    conv_vals.append(cv)
                    
            dfs[param] = pd.Series(conv_vals, index=s.index, name=param)
            unit_stats[param] = {"original_meta_unit": meta_unit, "target_unit": target_unit, "sensor_id": sensor_id}
            
    if not dfs or "pm25" not in dfs:
        return None, {"error": "No valid PM2.5 data after unit verification", "excluded": excluded_sensors}
        
    df = pd.DataFrame(dfs).resample("1h").mean()
    total_raw_points = len(df)
    
    stats = {
        "station_id": station_id,
        "name": name,
        "total_hourly_slots": total_raw_points,
        "raw_counts": {p: int(df[p].dropna().count()) for p in df.columns},
        "flags": {
            "negative_or_oob": 0,
            "flatlines": 0,
            "pm_ratio_violation": 0,
            "constant_ratio_hours": 0,
            "collapse_after_peak_hours": 0,
            "repeated_high_hours": 0,
            "total_suspect_hours": 0
        },
        "clean_counts": {},
        "reliability_score": 1.0,
        "excluded_sensors": excluded_sensors
    }
    
    invalid_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
    
    # Negative & Out-of-bounds check
    bounds = {
        "pm25": (PM25_MIN, PM25_MAX),
        "pm10": (PM10_MIN, PM10_MAX),
        "no2": (NO2_MIN, NO2_MAX),
        "co": (CO_MIN, CO_MAX)
    }
    for p in df.columns:
        if p in bounds:
            low, high = bounds[p]
            oob = (df[p] < low) | (df[p] > high)
            stats["flags"]["negative_or_oob"] += int(oob.sum())
            invalid_mask[p] = invalid_mask[p] | oob
            
    # Resolution-aware Flatlines
    for p in df.columns:
        flat = detect_flatlines_resolution_aware(df[p].where(~invalid_mask[p]))
        stats["flags"]["flatlines"] += int(flat.sum())
        invalid_mask[p] = invalid_mask[p] | flat
        
    df_clean = df.copy()
    for p in df.columns:
        df_clean.loc[invalid_mask[p], p] = np.nan
        
    # Automatic Fault Detectors from core.qc_faults
    fault_res = detect_all_faults(df_clean)
    
    df_clean["is_suspect"] = fault_res["is_suspect"]
    stats["flags"]["pm_ratio_violation"] = fault_res["fault_counts"]["pm_ratio_violation"]
    stats["flags"]["constant_ratio_hours"] = fault_res["fault_counts"]["constant_ratio_hours"]
    stats["flags"]["collapse_after_peak_hours"] = fault_res["fault_counts"]["collapse_after_peak_hours"]
    stats["flags"]["repeated_high_hours"] = fault_res["fault_counts"]["repeated_high_hours"]
    stats["flags"]["total_suspect_hours"] = fault_res["fault_counts"]["total_suspect_hours"]
    stats["reliability_score"] = fault_res["reliability_score"]
    
    # Invalidate direct ratio violation readings
    if "pm25" in df_clean.columns and "pm10" in df_clean.columns:
        df_clean.loc[fault_res["viol_ratio"], "pm25"] = np.nan
        df_clean.loc[fault_res["viol_ratio"], "pm10"] = np.nan
        
    for p in df_clean.columns:
        if p != "is_suspect":
            stats["clean_counts"][p] = int(df_clean[p].dropna().count())
            
    df_clean["timestamp_utc"] = df_clean.index.strftime("%Y-%m-%dT%H:%M:%SZ")
    df_clean["timestamp_ist"] = df_clean.index.tz_convert(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    df_clean["hour_ist"] = df_clean.index.tz_convert(IST).hour
    
    clean_dict = {
        "station_id": station_id,
        "name": name,
        "coordinates": station_dict.get("coordinates"),
        "reliability_score": stats["reliability_score"],
        "unit_conversions": unit_stats,
        "records": df_clean.to_dict(orient="records"),
        "fault_reasons": fault_res["fault_reasons_by_time"]
    }
    
    return clean_dict, stats

def run_dataset_qc(input_dir="data/stations_hourly", output_dir="data/stations_qc"):
    os.makedirs(output_dir, exist_ok=True)
    registry = load_sensor_metadata_registry()
    files = glob.glob(os.path.join(input_dir, "station_*.json"))
    
    all_stats = []
    print(f"Applying integrated QC pipeline to {len(files)} stations in {input_dir}...")
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            st = json.load(fp)
        clean_st, stats = run_qc_on_station(st, registry=registry)
        if clean_st:
            out_file = os.path.join(output_dir, f"station_{st['station_id']}_qc.json")
            with open(out_file, "w", encoding="utf-8") as fp:
                json.dump(clean_st, fp)
            all_stats.append(stats)
            
    total_raw_p25 = sum(s["raw_counts"].get("pm25", 0) for s in all_stats)
    total_raw_p10 = sum(s["raw_counts"].get("pm10", 0) for s in all_stats)
    total_raw_no2 = sum(s["raw_counts"].get("no2", 0) for s in all_stats)
    total_raw_co  = sum(s["raw_counts"].get("co", 0) for s in all_stats)
    total_raw = total_raw_p25 + total_raw_p10 + total_raw_no2 + total_raw_co
    
    clean_p25 = sum(s["clean_counts"].get("pm25", 0) for s in all_stats)
    clean_p10 = sum(s["clean_counts"].get("pm10", 0) for s in all_stats)
    clean_no2 = sum(s["clean_counts"].get("no2", 0) for s in all_stats)
    clean_co  = sum(s["clean_counts"].get("co", 0) for s in all_stats)
    total_clean = clean_p25 + clean_p10 + clean_no2 + clean_co
    
    total_oob = sum(s["flags"]["negative_or_oob"] for s in all_stats)
    total_flat = sum(s["flags"]["flatlines"] for s in all_stats)
    total_viol = sum(s["flags"]["pm_ratio_violation"] for s in all_stats)
    total_const = sum(s["flags"]["constant_ratio_hours"] for s in all_stats)
    total_collapse = sum(s["flags"]["collapse_after_peak_hours"] for s in all_stats)
    total_rep_high = sum(s["flags"]["repeated_high_hours"] for s in all_stats)
    total_suspect = sum(s["flags"]["total_suspect_hours"] for s in all_stats)
    
    report = {
        "stations_processed": len(all_stats),
        "total_raw_readings": total_raw,
        "total_clean_readings": total_clean,
        "readings_removed_pct": round(100.0 * (1.0 - total_clean / total_raw), 2),
        "co_raw": total_raw_co,
        "co_clean": clean_co,
        "co_flagged_pct": round(100.0 * (1.0 - clean_co / total_raw_co), 2),
        "fault_summary": {
            "pm_ratio_violations": total_viol,
            "constant_ratio_hours": total_const,
            "collapse_after_peak_hours": total_collapse,
            "repeated_high_hours": total_rep_high,
            "total_suspect_hours": total_suspect
        },
        "average_station_reliability": round(sum(s["reliability_score"] for s in all_stats) / len(all_stats), 3),
        "details": all_stats
    }
    
    with open("data/qc_report_upgraded.json", "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2)
        
    print("\n" + "="*70)
    print("UPGRADED QUALITY CONTROL & FAULT DETECTION REPORT (v1.0)")
    print("="*70)
    print(f"Stations Processed            : {len(all_stats)}")
    print(f"Total Raw Readings            : {total_raw:,}")
    print(f"Total Clean Readings Passed   : {total_clean:,} ({100.0 - report['readings_removed_pct']}%)")
    print(f"Readings Removed / Invalidated: {total_raw - total_clean:,} ({report['readings_removed_pct']}%)")
    print(f"CO Retention Rate             : {clean_co:,} / {total_raw_co:,} passed ({100.0 - report['co_flagged_pct']}%)")
    print(f"PM2.5 > PM10 Direct Violations: {total_viol:,}")
    print(f"Constant Ratio Locked Hours   : {total_const:,}")
    print(f"Collapse After Peak Hours     : {total_collapse:,}")
    print(f"Repeated High Float Hours     : {total_rep_high:,}")
    print(f"Total Suspect Hours Flagged   : {total_suspect:,}")
    print(f"Average Station Reliability   : {report['average_station_reliability']:.3f} / 1.000")
    print("="*70)
    return report

if __name__ == "__main__":
    run_dataset_qc()
