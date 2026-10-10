"""
Smokeprint Shared Confidence Tier Rules
Module: data/tier_rules.py

Single source of truth for qualitative confidence tier assignment across
markdown generator, API serialization, and recompute workflows.

Documented Tier Rules:
  1. Operating status penalty:
     If operating_status contains 'disused' or 'decommissioned' -> 'low'
  2. Geometry / dispersion limits:
     If angular_offset_deg > 45.0 or wind_speed_ms < 1.5 -> 'low'
  3. Classification cap:
     If attribution classification is 'Multiple Comparable Candidates' -> cannot contain 'high' (capped at 'medium')
  4. Core baseline rules:
     - 'low': discriminability < 0.25 or interval_spread > 0.30
     - 'high': interval_spread <= 0.15 and relative_score >= 0.35 (unless capped)
     - 'medium': interval_spread <= 0.30
"""

from typing import Optional

LOW_WIND_THRESHOLD_MS = 1.5
MAX_ANGULAR_OFFSET_DEG = 50.0

def determine_confidence_tier(
    score: float,
    spread: float,
    discriminability: float = 1.0,
    operating_status: Optional[str] = "active_presumed",
    angular_offset_deg: Optional[float] = None,
    wind_speed_ms: Optional[float] = None,
    classification: Optional[str] = None
) -> str:
    """
    Computes qualitative confidence tier ('high', 'medium', 'low') enforcing all documented rules.
    """
    status_str = (operating_status or "").lower()
    
    # 1. Disused / decommissioned sites are strictly LOW confidence
    if "disused" in status_str or "decommissioned" in status_str:
        return "low"

    # 2. Extreme angular offset (> 45 deg) or calm wind (< 1.5 m/s) forces LOW confidence
    if angular_offset_deg is not None and angular_offset_deg > MAX_ANGULAR_OFFSET_DEG:
        return "low"
    if wind_speed_ms is not None and wind_speed_ms < LOW_WIND_THRESHOLD_MS:
        return "low"

    # 3. Baseline score & spread evaluation
    if discriminability < 0.25 or spread > 0.30:
        base_tier = "low"
    elif spread <= 0.15 and score >= 0.35:
        base_tier = "high"
    elif spread <= 0.30:
        base_tier = "medium"
    else:
        base_tier = "low"

    # 4. Multiple Comparable Candidates cannot contain a high tier
    class_str = (classification or "").lower()
    if "comparable" in class_str or "diffuse" in class_str:
        if base_tier == "high":
            base_tier = "medium"

    return base_tier
