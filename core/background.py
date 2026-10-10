"""
Smokeprint Regional Background Estimation and Event Classifier
Module: core/background.py

Implements:
  1. Regional background = median of other reliable stations (excluding target station
     and any station with is_suspect hours in the window).
  2. Reports n (contributing stations count) and spread (IQR = Q75 - Q25).
  3. Local excess = max(0, target_station_pm25 - background_median).
  4. Explicit event classification:
       - 'regional': widespread airshed-wide elevation (excess near zero, background high)
       - 'possible_fault': target station has active physical/telemetry fault flagged
       - 'local': target station stands out significantly with local excess
       - 'insufficient_evidence': borderline excess, quiet conditions, or weak signal
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

MIN_RELIABLE_SCORE = 0.60
REGIONAL_ELEVATION_THRESHOLD = 150.0  # ug/m3
REGIONAL_NETWORK_FRACTION = 0.70      # >= 70% stations elevated implies regional smog
MIN_LOCAL_EXCESS = 25.0               # ug/m3 for local classification

def compute_regional_background(
    target_station_id: Optional[int],
    timestamp_utc: str,
    all_stations_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes regional background median and IQR across reliable network stations.
    
    Args:
      target_station_id: ID of the station experiencing the spike (excluded from background)
      timestamp_utc: ISO timestamp string (e.g., '2026-04-05T22:00:00Z')
      all_stations_data: list of station dicts (from stations_qc or memory)
      
    Returns:
      dict with:
        'n_contributing': int
        'regional_median': float
        'regional_iqr': float
        'q25': float
        'q75': float
        'contributing_stations': list[dict]
        'network_elevation_pct': float
    """
    contributing_vals = []
    contributing_meta = []
    total_reporting = 0
    elevated_count = 0
    
    # Standardize target timestamp search
    target_prefix = timestamp_utc[:13] # match YYYY-MM-DDTHH
    
    for st in all_stations_data:
        sid = st.get("station_id")
        reliability = st.get("reliability_score", 1.0)
        
        # Search record for this timestamp
        records = st.get("records", [])
        matched_rec = None
        for r in records:
            r_ts = r.get("timestamp_utc", "")
            if r_ts == timestamp_utc or (r_ts.startswith(target_prefix) and r_ts.endswith("Z")):
                matched_rec = r
                break
                
        if not matched_rec:
            continue
            
        p25 = matched_rec.get("pm25")
        if p25 is None or np.isnan(p25):
            continue
            
        total_reporting += 1
        if p25 >= REGIONAL_ELEVATION_THRESHOLD:
            elevated_count += 1
            
        # Exclude target station
        if sid is not None and target_station_id is not None and sid == target_station_id:
            continue
            
        # Exclude suspect stations or low reliability stations
        if matched_rec.get("is_suspect", False):
            continue
        if reliability < MIN_RELIABLE_SCORE:
            continue
            
        contributing_vals.append(float(p25))
        contributing_meta.append({
            "station_id": sid,
            "name": st.get("name"),
            "pm25": float(p25)
        })
        
    n = len(contributing_vals)
    elevation_pct = round(100.0 * elevated_count / max(1, total_reporting), 1)
    
    if n == 0:
        return {
            "n_contributing": 0,
            "regional_median": 0.0,
            "regional_iqr": 0.0,
            "q25": 0.0,
            "q75": 0.0,
            "contributing_stations": [],
            "network_elevation_pct": elevation_pct,
            "total_reporting": total_reporting
        }
        
    arr = np.array(contributing_vals)
    med = float(np.median(arr))
    q25 = float(np.percentile(arr, 25))
    q75 = float(np.percentile(arr, 75))
    iqr = round(q75 - q25, 2)
    
    return {
        "n_contributing": n,
        "regional_median": round(med, 2),
        "regional_iqr": iqr,
        "q25": round(q25, 2),
        "q75": round(q75, 2),
        "contributing_stations": contributing_meta,
        "network_elevation_pct": elevation_pct,
        "total_reporting": total_reporting
    }

def classify_event(
    target_station_data: Optional[Dict[str, Any]],
    timestamp_utc: str,
    background_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Classifies the spike event into one of:
      - 'possible_fault'
      - 'regional'
      - 'local'
      - 'insufficient_evidence'
      
    Returns complete diagnostics including local excess and reason.
    """
    bg_med = background_info.get("regional_median", 0.0)
    bg_iqr = background_info.get("regional_iqr", 0.0)
    elev_pct = background_info.get("network_elevation_pct", 0.0)
    n_bg = background_info.get("n_contributing", 0)
    
    # Check if target station has record
    target_rec = None
    target_sid = None
    fault_reasons = []
    
    if target_station_data:
        target_sid = target_station_data.get("station_id")
        target_prefix = timestamp_utc[:13]
        for r in target_station_data.get("records", []):
            r_ts = r.get("timestamp_utc", "")
            if r_ts == timestamp_utc or (r_ts.startswith(target_prefix) and r_ts.endswith("Z")):
                target_rec = r
                break
                
        # Look up fault reasons
        all_faults = target_station_data.get("fault_reasons", {})
        for f_ts, reasons in all_faults.items():
            if f_ts.startswith(target_prefix):
                fault_reasons.extend(reasons)
                
    st_p25 = float(target_rec.get("pm25")) if (target_rec and target_rec.get("pm25") is not None and not np.isnan(target_rec.get("pm25"))) else None
    
    # 1. Regional Airshed Check (before station-level checks)
    is_regional_pct = elev_pct >= (REGIONAL_NETWORK_FRACTION * 100.0)
    if is_regional_pct and (bg_med > 350.0 or st_p25 is None or (st_p25 - bg_med) / max(1.0, bg_med) < 0.40):
        excess = max(0.0, round((st_p25 - bg_med) if st_p25 is not None else 0.0, 2))
        return {
            "label": "regional",
            "station_pm25": st_p25,
            "regional_median": bg_med,
            "background_iqr": bg_iqr,
            "local_excess": excess,
            "n_stations_background": n_bg,
            "dispatch_recommended": False,
            "rationale": f"Widespread regional event: {elev_pct}% of stations elevated above {REGIONAL_ELEVATION_THRESHOLD} ug/m3. Airshed median is {bg_med} ug/m3. Regional smog event, no localized dispatch."
        }
        
    # 2. Fault Check
    if fault_reasons or (target_rec and target_rec.get("is_suspect")):
        excess = max(0.0, round((st_p25 or 0.0) - bg_med, 2))
        return {
            "label": "possible_fault",
            "station_pm25": st_p25,
            "regional_median": bg_med,
            "background_iqr": bg_iqr,
            "local_excess": excess,
            "n_stations_background": n_bg,
            "fault_detected": True,
            "fault_reasons": list(set(fault_reasons)) or ["marked_suspect"],
            "dispatch_recommended": False,
            "rationale": f"Instrument fault detected on target station telemetry: {', '.join(set(fault_reasons)) or 'suspect flags'}."
        }
        
    if st_p25 is None:
        return {
            "label": "possible_fault" if not target_station_data else "insufficient_evidence",
            "station_pm25": None,
            "regional_median": bg_med,
            "background_iqr": bg_iqr,
            "local_excess": 0.0,
            "n_stations_background": n_bg,
            "dispatch_recommended": False,
            "rationale": "Target station PM2.5 missing, collapsed, or invalidated by QC."
        }
        
    local_excess = max(0.0, round(st_p25 - bg_med, 2))
    relative_excess = local_excess / max(1.0, bg_med)
        
    # 3. Local Check
    if local_excess >= MIN_LOCAL_EXCESS and relative_excess >= 0.25:
        return {
            "label": "local",
            "station_pm25": st_p25,
            "regional_median": bg_med,
            "background_iqr": bg_iqr,
            "local_excess": local_excess,
            "n_stations_background": n_bg,
            "dispatch_recommended": True,
            "rationale": f"Localized emission excess of +{local_excess} ug/m3 stands out above regional background median ({bg_med} ug/m3, IQR {bg_iqr})."
        }
        
    # 4. Insufficient Evidence Fallback
    return {
        "label": "insufficient_evidence",
        "station_pm25": st_p25,
        "regional_median": bg_med,
        "background_iqr": bg_iqr,
        "local_excess": local_excess,
        "n_stations_background": n_bg,
        "dispatch_recommended": False,
        "rationale": f"Excess (+{local_excess} ug/m3) is too weak relative to background variability (IQR {bg_iqr} ug/m3). Monitor only."
    }
