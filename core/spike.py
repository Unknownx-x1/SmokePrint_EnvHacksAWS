"""
Smokeprint Robust Spike Detection Engine
Module: core/spike.py

Implements:
  1. Seasonal-Trend decomposition using LOESS (STL, period=24h diurnal cycle).
  2. Robust z-score computation on residuals using Median Absolute Deviation (MAD):
       z = (r - median(r)) / (1.4826 * MAD(r))
  3. Persistence enforcement: spikes must persist >= 3 consecutive hours (or be corroborated by a neighbour).
  4. Excludes all QC-flagged suspect readings (is_suspect == True).
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

DEFAULT_PEAK_Z_THRESH = 2.5
DEFAULT_PERSIST_Z_THRESH = 1.8
MIN_PERSIST_HOURS = 3

def compute_stl_residuals(series: pd.Series, period: int = 24) -> Tuple_STL:
    """
    Fits robust STL decomposition to an hourly series.
    Missing values are linearly interpolated up to 6 hours then filled with median.
    """
    clean_series = series.copy()
    # Interpolate gaps for STL fitting
    filled = clean_series.interpolate(method="linear", limit=6).fillna(clean_series.median())
    if len(filled.dropna()) < period * 2:
        # Fallback to simple rolling median subtraction if series too short
        trend = filled.rolling(period, center=True, min_periods=1).median()
        resid = filled - trend
        return resid, filled
        
    stl = STL(filled, period=period, robust=True)
    res = stl.fit()
    return res.resid, filled

def compute_robust_zscore(residuals: pd.Series) -> pd.Series:
    """
    Computes robust z-score on residuals using Median Absolute Deviation (MAD):
      z = (r - median(r)) / (1.4826 * MAD(r))
    """
    valid = residuals.dropna()
    if len(valid) == 0:
        return pd.Series(0.0, index=residuals.index)
        
    med = float(np.median(valid))
    mad = float(np.median(np.abs(valid - med)))
    
    scale = 1.4826 * mad
    if scale < 1e-4:
        scale = float(valid.std()) if valid.std() > 1e-4 else 1.0
        
    z = (residuals - med) / scale
    return z

def detect_station_spikes(
    df: pd.DataFrame,
    peak_z_thresh: float = DEFAULT_PEAK_Z_THRESH,
    persist_z_thresh: float = DEFAULT_PERSIST_Z_THRESH,
    min_persist_hours: int = MIN_PERSIST_HOURS,
    neighbour_corroborator: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """
    Detects persistent spikes on a station's QC'd DataFrame.
    DataFrame must contain: 'timestamp_utc' or datetime index, 'pm25', and optional 'is_suspect'.
    """
    if "pm25" not in df.columns:
        return []
        
    work_df = df.copy()
    if not isinstance(work_df.index, pd.DatetimeIndex):
        if "timestamp_utc" in work_df.columns:
            work_df.index = pd.to_datetime(work_df["timestamp_utc"], utc=True)
        else:
            work_df.index = pd.date_range(start="2026-01-01", periods=len(work_df), freq="1h")
            
    work_df = work_df.sort_index()
    
    # Strictly mask out suspect readings
    s_pm25 = work_df["pm25"].copy()
    if "is_suspect" in work_df.columns:
        s_pm25[work_df["is_suspect"]] = np.nan
        
    if s_pm25.dropna().count() < 48:
        return []
        
    residuals, filled = compute_stl_residuals(s_pm25, period=24)
    z_scores = compute_robust_zscore(residuals)
    
    # Spikes above persist threshold
    is_elevated = (z_scores >= persist_z_thresh) & s_pm25.notna()
    
    spikes = []
    n = len(is_elevated)
    i = 0
    
    while i < n:
        if not is_elevated.iloc[i]:
            i += 1
            continue
            
        j = i
        while j < n and is_elevated.iloc[j]:
            j += 1
            
        duration = j - i
        sub_z = z_scores.iloc[i:j]
        peak_z = float(sub_z.max())
        peak_idx = sub_z.idxmax()
        
        # Check persistence criteria
        is_persistent = (duration >= min_persist_hours) and (peak_z >= peak_z_thresh)
        is_neighbour_corroborated = False
        
        if not is_persistent and peak_z >= peak_z_thresh and neighbour_corroborator:
            # Check if a neighbouring station corroborates
            is_neighbour_corroborated = neighbour_corroborator(peak_idx)
            
        if is_persistent or is_neighbour_corroborated:
            start_ts = work_df.index[i].strftime("%Y-%m-%dT%H:%M:%SZ")
            peak_ts = peak_idx.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_ts = work_df.index[j - 1].strftime("%Y-%m-%dT%H:%M:%SZ")
            
            spikes.append({
                "start_utc": start_ts,
                "peak_utc": peak_ts,
                "end_utc": end_ts,
                "duration_hours": duration,
                "peak_z": round(peak_z, 2),
                "peak_pm25": round(float(work_df.loc[peak_idx, "pm25"]), 1),
                "is_corroborated": is_neighbour_corroborated,
                "corroboration_type": "persistence" if is_persistent else "neighbour_response"
            })
            
        i = j
        
    return spikes
