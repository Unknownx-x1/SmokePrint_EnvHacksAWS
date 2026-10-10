"""
Smokeprint Source Prior Formulation (Heuristic, Uncalibrated)
Provides relative prior weights W(source) for candidate emitters based on
source category, discrete geometry vs diffuse zone, naming status, and assumed seasonal activity.
Treated strictly as relative weights, normalized in the posterior, never displayed as probabilities.
"""

from datetime import datetime
from typing import Tuple, List
import math

# HEURISTIC, UNCALIBRATED RELATIVE BASE WEIGHTS
# These represent baseline relative weights before footprint and chemical likelihoods are applied.
# They are not probabilities and are labeled "heuristic, uncalibrated".
BASE_PRIOR_WEIGHTS = {
    "landfill_named_major": 0.85,    # Known chronic methane/waste burning (Ghazipur, Bhalswa, Okhla)
    "landfill_discrete_point": 0.60, # Small waste transfer station / local dump node
    "landfill_polygon": 0.50,        # Landfill area polygon
    
    "brick_kiln_base": 0.75,         # Kiln base weight (modified by assumed season)
    
    "industrial_discrete_point": 0.60, # Point factory / chimney
    "industrial_named_facility": 0.50, # Named industrial plot / works
    "industrial_diffuse_zone": 0.20,   # Broad landuse=industrial polygon / estate
    
    "construction_named": 0.45,      # Major named infrastructure / transport project
    "construction_unnamed": 0.35,    # General construction parcel
    
    "quarry_polygon": 0.30           # Mechanical aggregate / stone quarry
}

def get_kiln_month_multiplier(month: int) -> float:
    """
    Assumed seasonal brick kiln activity multiplier in Delhi-NCR:
      - Feb to Jun: Peak firing season (continuous kiln operations) -> 1.00
      - Jul to Oct: Monsoon shutdown (rain impedes unbaked brick drying) -> 0.05
      - Nov to Jan: Assumed winter curtailment period -> 0.20
    """
    if 2 <= month <= 6:
        return 1.00
    elif 7 <= month <= 10:
        return 0.05
    else: # 11, 12, 1
        return 0.20

def get_diurnal_multiplier(source_type: str, hour_ist: int) -> float:
    """
    Diurnal activity modifier based on Indian Standard Time hour (0-23):
      - Construction and Quarries are predominantly daytime mechanical activities (07:00 to 19:00 IST).
      - Landfills smolder continuously with nighttime inversion peaks.
      - Brick kilns operate continuous draft fires day and night when active.
    """
    is_daytime = 7 <= hour_ist <= 19
    if source_type in ["construction", "quarry"]:
        return 1.00 if is_daytime else 0.25
    return 1.00

def check_operating_status(source: dict) -> Tuple[str, float, List[str]]:
    """
    Checks OSM candidate tags for lifecycle prefixes and decommissioned/disused status:
      - disused:*, abandoned:*, demolished:*, historic:*, was:*
      - values: 'disused', 'abandoned', 'demolished', 'closed'
    Returns:
      (status_label, penalty_multiplier, reasons_list)
    """
    tags = source.get("tags", {})
    name = source.get("name", "").strip().lower()
    reasons = []
    
    for k, v in tags.items():
        k_str = str(k).lower()
        v_str = str(v).lower()
        if k_str.startswith(("disused", "abandoned", "demolished", "historic", "was:")):
            reasons.append(f"{k}={v}")
        elif v_str in ["disused", "abandoned", "demolished", "closed", "decommissioned"]:
            reasons.append(f"{k}={v}")
            
    # Explicit check for known historical shutdowns (e.g. Rajghat, Badarpur coal plants shut in 2015/2018)
    if "rajghat thermal power station" in name and not reasons:
        reasons.append("known_decommissioned_site=rajghat_coal_shutdown_2015")
    if "badarpur thermal power station" in name and not reasons:
        reasons.append("known_decommissioned_site=badarpur_coal_shutdown_2018")
        
    if reasons:
        return "unverified_operating_status (decommissioned/disused)", 0.05, reasons
    return "active_presumed", 1.0, []

def compute_source_prior(source: dict, event_dt: datetime) -> dict:
    """
    Computes heuristic, uncalibrated relative prior weight W(source) for a candidate emitter.
    
    Args:
      source: dict with keys 'type', 'id', 'name', 'tags', optional 'area_km2'
      event_dt: datetime of the spike event (UTC or IST)
      
    Returns:
      dict with 'prior_weight': float, 'label': 'heuristic, uncalibrated', 'factors': dict, 'operating_status': str
    """
    stype = source.get("type", "other")
    geom = source.get("id", "").split("_")[1] if "_" in source.get("id", "") else "way"
    name = source.get("name", "").strip()
    is_named = bool(name and name != "Unnamed Site")
    
    month = event_dt.month
    # Localize to IST for diurnal multiplier
    hour_ist = (event_dt.hour + 5 + (1 if event_dt.minute >= 30 else 0)) % 24
    
    op_status, status_penalty, op_reasons = check_operating_status(source)
    
    factors = {
        "base": 0.30,
        "seasonal": 1.00,
        "diurnal": 1.00,
        "geometry_penalty": 1.00,
        "operating_status_penalty": status_penalty
    }
    
    if stype == "brick_kiln":
        factors["base"] = BASE_PRIOR_WEIGHTS["brick_kiln_base"]
        factors["seasonal"] = get_kiln_month_multiplier(month)
        factors["diurnal"] = 1.00
        
    elif stype == "landfill":
        lower_name = name.lower()
        if any(major in lower_name for major in ["ghazipur", "bhalswa", "okhla"]):
            factors["base"] = BASE_PRIOR_WEIGHTS["landfill_named_major"]
        elif geom == "node":
            factors["base"] = BASE_PRIOR_WEIGHTS["landfill_discrete_point"]
        else:
            factors["base"] = BASE_PRIOR_WEIGHTS["landfill_polygon"]
            
    elif stype == "industrial":
        if geom == "node":
            factors["base"] = BASE_PRIOR_WEIGHTS["industrial_discrete_point"]
        elif is_named:
            factors["base"] = BASE_PRIOR_WEIGHTS["industrial_named_facility"]
        else:
            factors["base"] = BASE_PRIOR_WEIGHTS["industrial_diffuse_zone"]
            
        area_km2 = source.get("area_km2", 1.0)
        factors["geometry_penalty"] = round(1.0 / (1.0 + math.log(1.0 + max(0.1, area_km2))), 3)
        
    elif stype == "construction":
        factors["base"] = BASE_PRIOR_WEIGHTS["construction_named"] if is_named else BASE_PRIOR_WEIGHTS["construction_unnamed"]
        factors["diurnal"] = get_diurnal_multiplier("construction", hour_ist)
        
    elif stype == "quarry":
        factors["base"] = BASE_PRIOR_WEIGHTS["quarry_polygon"]
        factors["diurnal"] = get_diurnal_multiplier("quarry", hour_ist)
        
    raw_weight = factors["base"] * factors["seasonal"] * factors["diurnal"] * factors["geometry_penalty"] * factors["operating_status_penalty"]
    bounded_weight = max(0.005, min(1.0, round(raw_weight, 4)))
    
    return {
        "prior_weight": bounded_weight,
        "is_calibrated": False,
        "label": "heuristic, uncalibrated",
        "operating_status": op_status,
        "operating_reasons": op_reasons,
        "factors": factors
    }

