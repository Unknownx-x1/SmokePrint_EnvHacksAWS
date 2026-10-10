"""
Smokeprint Automatic Quality Control & Instrument Fault Detectors
Module: core/qc_faults.py

Implements 4 automatic physical & telemetry fault detectors:
  1. PM2.5 > PM10 violation (with +/-3h suspect window)
  2. Constant PM2.5/PM10 ratio over >= 3 consecutive hours (logger synthesis/lock)
  3. Abrupt collapse to 0 / negative / NaN within 1-2 hours after an extreme peak
  4. Repeated identical float values at high concentration (stuck telemetry/inlet jam)

Feeds station reliability scores and directly supports the 'possible_fault' hypothesis.
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

# Tolerances & Thresholds
PM_RATIO_TOLERANCE_MULT = 1.05
PM_RATIO_TOLERANCE_ADD = 5.0
SUSPECT_WINDOW_HOURS = 3

CONSTANT_RATIO_MIN_HOURS = 3
CONSTANT_RATIO_TOLERANCE = 0.005
CONSTANT_RATIO_MIN_PM10 = 25.0
CONSTANT_RATIO_MIN_PM25 = 15.0

COLLAPSE_PEAK_PM10 = 200.0
COLLAPSE_PEAK_PM25 = 120.0
COLLAPSE_FLOOR = 5.0

REPEATED_HIGH_MIN_HOURS = 3
REPEATED_HIGH_THRESHOLDS = {
    "pm25": 80.0,
    "pm10": 120.0,
    "no2": 40.0,
    "co": 3.0
}

def detect_pm_ratio_violations(
    df: pd.DataFrame,
    mult: float = PM_RATIO_TOLERANCE_MULT,
    add: float = PM_RATIO_TOLERANCE_ADD,
    window: int = SUSPECT_WINDOW_HOURS
) -> Tuple[pd.Series, pd.Series]:
    """
    Detects unphysical PM2.5 > PM10 instances and generates a +/- window suspect mask.
    Returns: (violation_mask, suspect_mask)
    """
    n = len(df)
    viol = pd.Series(False, index=df.index)
    suspect = pd.Series(False, index=df.index)
    
    if "pm25" not in df.columns or "pm10" not in df.columns:
        return viol, suspect
        
    pm25 = pd.to_numeric(df["pm25"], errors="coerce")
    pm10 = pd.to_numeric(df["pm10"], errors="coerce")
    both_valid = pm25.notna() & pm10.notna() & (pm25 > 0) & (pm10 > 0)
    viol = both_valid & (pm25 > (pm10 * mult + add))
    
    suspect = viol.copy()
    for shift in range(-window, window + 1):
        suspect = suspect | viol.shift(shift, fill_value=False)
        
    return viol, suspect

def detect_constant_ratio(
    df: pd.DataFrame,
    min_hours: int = CONSTANT_RATIO_MIN_HOURS,
    tol: float = CONSTANT_RATIO_TOLERANCE,
    min_pm10: float = CONSTANT_RATIO_MIN_PM10,
    min_pm25: float = CONSTANT_RATIO_MIN_PM25
) -> pd.Series:
    """
    Detects periods where PM2.5/PM10 ratio is artificially locked/constant over >= min_hours.
    """
    flag = pd.Series(False, index=df.index)
    if "pm25" not in df.columns or "pm10" not in df.columns:
        return flag
        
    pm25 = pd.to_numeric(df["pm25"], errors="coerce")
    pm10 = pd.to_numeric(df["pm10"], errors="coerce")
    valid = (pm25 >= min_pm25) & (pm10 >= min_pm10)
    ratio = (pm25 / pm10).where(valid)
    
    # Rolling max - min
    rolling_spread = ratio.rolling(min_hours, min_periods=min_hours).apply(
        lambda x: x.max() - x.min(), raw=True
    )
    is_locked_end = (rolling_spread <= tol) & valid
    
    # Expand across the run
    for i in range(len(is_locked_end)):
        if is_locked_end.iloc[i]:
            start_idx = max(0, i - min_hours + 1)
            flag.iloc[start_idx : i + 1] = True
            
    return flag

def detect_nan_dropout_after_peak(
    df: pd.DataFrame,
    peak_pm10: float = COLLAPSE_PEAK_PM10,
    peak_pm25: float = COLLAPSE_PEAK_PM25
) -> pd.Series:
    """
    Detects prolonged NaN telemetry dropouts (>= 2 consecutive NaNs)
    occurring within 1-2 hours after an extreme peak.
    """
    flag = pd.Series(False, index=df.index)
    n = len(df)
    if n < 4:
        return flag

    for p, thresh in [("pm10", peak_pm10), ("pm25", peak_pm25)]:
        if p not in df.columns:
            continue
        s = pd.to_numeric(df[p], errors="coerce")
        is_peak = s >= thresh
        next1 = s.shift(-1)
        next2 = s.shift(-2)
        crashed_nan = is_peak & next1.isna() & next2.isna()
        for i in range(len(crashed_nan) - 2):
            if crashed_nan.iloc[i]:
                flag.iloc[max(0, i - 1) : min(len(flag), i + 3)] = True
    return flag

def detect_crash_to_zero(
    df: pd.DataFrame,
    peak_pm10: float = COLLAPSE_PEAK_PM10,
    peak_pm25: float = COLLAPSE_PEAK_PM25,
    floor_val: float = COLLAPSE_FLOOR
) -> pd.Series:
    """
    Detects abrupt crashes to near zero (<= floor_val) or negative readings
    occurring within 1-2 hours after an extreme peak.
    """
    flag = pd.Series(False, index=df.index)
    n = len(df)
    if n < 4:
        return flag

    for p, thresh in [("pm10", peak_pm10), ("pm25", peak_pm25)]:
        if p not in df.columns:
            continue
        s = pd.to_numeric(df[p], errors="coerce")
        is_peak = s >= thresh
        next1 = s.shift(-1)
        crashed_zero = is_peak & next1.notna() & (next1 <= floor_val)
        for i in range(len(crashed_zero) - 2):
            if crashed_zero.iloc[i]:
                flag.iloc[max(0, i - 1) : min(len(flag), i + 3)] = True
    return flag

def detect_collapse_after_peak(
    df: pd.DataFrame,
    peak_pm10: float = COLLAPSE_PEAK_PM10,
    peak_pm25: float = COLLAPSE_PEAK_PM25,
    floor_val: float = COLLAPSE_FLOOR
) -> pd.Series:
    """
    Combined alias for backward compatibility: union of nan_dropout_after_peak and crash_to_zero.
    """
    nan_drop = detect_nan_dropout_after_peak(df, peak_pm10, peak_pm25)
    crash_zero = detect_crash_to_zero(df, peak_pm10, peak_pm25, floor_val)
    return nan_drop | crash_zero

def detect_repeated_high_concentration(
    df: pd.DataFrame,
    min_hours: int = REPEATED_HIGH_MIN_HOURS,
    thresholds: Dict[str, float] = REPEATED_HIGH_THRESHOLDS
) -> pd.Series:
    """
    Detects repeated identical values (flatlines) at high concentrations (sensor/logger stall).
    """
    flag = pd.Series(False, index=df.index)
    for p, thresh in thresholds.items():
        if p not in df.columns:
            continue
        s = pd.to_numeric(df[p], errors="coerce")
        vals = s.values
        n = len(vals)
        i = 0
        while i < n:
            val_i = vals[i]
            if pd.isna(val_i) or val_i < thresh:
                i += 1
                continue
            j = i
            while j < n and not pd.isna(vals[j]) and abs(vals[j] - val_i) < 1e-5:
                j += 1
            if (j - i) >= min_hours:
                flag.iloc[i:j] = True
            i = j
    return flag

def detect_all_faults(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Executes the full suite of automatic fault detectors on a station's time series.
    Returns:
      dict with:
        'is_suspect': pd.Series[bool]
        'viol_ratio': pd.Series[bool]
        'constant_ratio': pd.Series[bool]
        'nan_dropout_after_peak': pd.Series[bool]
        'crash_to_zero': pd.Series[bool]
        'collapse_after_peak': pd.Series[bool]
        'repeated_high': pd.Series[bool]
        'fault_counts': dict
        'total_suspect_hours': int
        'reliability_score': float
        'fault_reasons_by_time': dict[str, list[str]]
    """
    viol_ratio, suspect_ratio = detect_pm_ratio_violations(df)
    const_ratio = detect_constant_ratio(df)
    nan_drop = detect_nan_dropout_after_peak(df)
    crash_zero = detect_crash_to_zero(df)
    collapse = nan_drop | crash_zero
    rep_high = detect_repeated_high_concentration(df)
    
    combined_suspect = suspect_ratio | const_ratio | collapse | rep_high
    
    fault_counts = {
        "pm_ratio_violation": int(viol_ratio.sum()),
        "ratio_suspect_expanded": int(suspect_ratio.sum()),
        "constant_ratio_hours": int(const_ratio.sum()),
        "nan_dropout_after_peak_hours": int(nan_drop.sum()),
        "crash_to_zero_hours": int(crash_zero.sum()),
        "collapse_after_peak_hours": int(collapse.sum()),
        "repeated_high_hours": int(rep_high.sum()),
        "total_suspect_hours": int(combined_suspect.sum())
    }
    
    valid_hours = len(df)
    if "pm25" in df.columns:
        valid_hours = max(1, int(df["pm25"].notna().sum()))
        
    suspect_hours = int(combined_suspect.sum())
    reliability = max(0.0, round(1.0 - (suspect_hours / valid_hours), 3))
    
    fault_reasons = {}
    for idx in df.index[combined_suspect]:
        ts_str = idx.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(idx, "strftime") else str(idx)
        reasons = []
        if viol_ratio.loc[idx]:
            reasons.append("pm_ratio_violation")
        elif suspect_ratio.loc[idx]:
            reasons.append("within_ratio_violation_window")
        if const_ratio.loc[idx]:
            reasons.append("constant_ratio_lock")
        if nan_drop.loc[idx]:
            reasons.append("data dropout after peak")
        if crash_zero.loc[idx]:
            reasons.append("crash_to_zero")
        if rep_high.loc[idx]:
            reasons.append("repeated_high_concentration")
        fault_reasons[ts_str] = reasons
        
    return {
        "is_suspect": combined_suspect,
        "viol_ratio": viol_ratio,
        "constant_ratio": const_ratio,
        "nan_dropout_after_peak": nan_drop,
        "crash_to_zero": crash_zero,
        "collapse_after_peak": collapse,
        "repeated_high": rep_high,
        "fault_counts": fault_counts,
        "total_suspect_hours": suspect_hours,
        "reliability_score": reliability,
        "fault_reasons_by_time": fault_reasons
    }
