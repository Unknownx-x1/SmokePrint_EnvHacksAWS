"""
Smokeprint Strict Unit Normalization and Verification Engine
Enforces requirement 4:
- Reads units strictly from OpenAQ sensor metadata per sensor ID.
- Excludes sensors with missing or unexpected units, logging the event.
- NEVER infers units from numeric magnitude.
- Standardizes all concentrations to CPCB standard ambient units:
    PM2.5: ug/m3
    PM10:  ug/m3
    NO2:   ug/m3
    CO:    mg/m3
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("smokeprint.units")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Approved canonical unit definitions and their conversion multipliers to target ambient units
# NO2 -> target: ug/m3 (1 ppb = 1.88 ug/m3 at 25 deg C, 1013 hPa)
# CO  -> target: mg/m3 (1 ppb = 0.001145 mg/m3; 1 ppm = 1.145 mg/m3)
APPROVED_UNITS = {
    "pm25": {
        "ug/m3": (1.0, "ug/m3"),
        "µg/m³": (1.0, "ug/m3"),
        "ug/m^3": (1.0, "ug/m3")
    },
    "pm10": {
        "ug/m3": (1.0, "ug/m3"),
        "µg/m³": (1.0, "ug/m3"),
        "ug/m^3": (1.0, "ug/m3")
    },
    "no2": {
        "ppb": (1.88, "ug/m3"),
        "parts per billion": (1.88, "ug/m3"),
        "ppm": (1880.0, "ug/m3"),
        "ug/m3": (1.0, "ug/m3"),
        "µg/m³": (1.0, "ug/m3"),
        "ug/m^3": (1.0, "ug/m3")
    },
    "co": {
        "ppb": (0.001145, "mg/m3"),
        "parts per billion": (0.001145, "mg/m3"),
        "ppm": (1.145, "mg/m3"),
        "parts per million": (1.145, "mg/m3"),
        "mg/m3": (1.0, "mg/m3"),
        "mg/m³": (1.0, "mg/m3"),
        "mg/m^3": (1.0, "mg/m3")
    }
}

_GLOBAL_SENSOR_REGISTRY: Optional[Dict[int, Dict[str, Any]]] = None

def load_sensor_metadata_registry(stations_file: str = "data/active_stations.json") -> Dict[int, Dict[str, Any]]:
    """Loads OpenAQ sensor metadata registry mapping sensor_id to parameter info."""
    global _GLOBAL_SENSOR_REGISTRY
    if _GLOBAL_SENSOR_REGISTRY is not None:
        return _GLOBAL_SENSOR_REGISTRY
        
    registry = {}
    if os.path.exists(stations_file):
        try:
            with open(stations_file, "r", encoding="utf-8") as f:
                stations = json.load(f)
                for st in stations:
                    for s in st.get("sensors", []):
                        sid = s.get("id")
                        param_obj = s.get("parameter", {})
                        pname = param_obj.get("name", "").strip().lower()
                        units = param_obj.get("units")
                        if units is not None:
                            units = str(units).strip().lower()
                        registry[sid] = {
                            "sensor_id": sid,
                            "parameter": pname,
                            "units": units,
                            "station_id": st.get("id"),
                            "station_name": st.get("name"),
                            "display_name": param_obj.get("displayName")
                        }
        except Exception as e:
            logger.error(f"Failed to load sensor registry from {stations_file}: {e}")
            
    _GLOBAL_SENSOR_REGISTRY = registry
    return registry

def verify_and_convert_reading(
    val: Optional[float],
    param: str,
    sensor_id: Optional[int],
    registry: Optional[Dict[int, Dict[str, Any]]] = None
) -> Tuple[Optional[float], str, bool, Optional[str]]:
    """
    Validates a reading's unit from OpenAQ sensor metadata and converts to standard units.
    
    Returns:
      (converted_val, target_unit, is_valid, log_reason)
      If unit is missing or unexpected, returns (None, 'unknown', False, reason).
    """
    if val is None:
        return None, "none", True, None
        
    if registry is None:
        registry = load_sensor_metadata_registry()
        
    param_clean = param.strip().lower()
    if param_clean not in APPROVED_UNITS:
        return val, "raw", True, None
        
    if sensor_id is None:
        msg = f"EXCLUDED: Missing sensor_id for parameter '{param}' reading. Cannot verify units."
        logger.warning(msg)
        return None, "unknown", False, msg
        
    sensor_meta = registry.get(sensor_id)
    if not sensor_meta:
        msg = f"EXCLUDED: Sensor ID {sensor_id} ({param}) not found in OpenAQ metadata registry."
        logger.warning(msg)
        return None, "unknown", False, msg
        
    meta_unit = sensor_meta.get("units")
    if not meta_unit or meta_unit in ["none", "null", "unknown", ""]:
        msg = f"EXCLUDED: Sensor ID {sensor_id} ({param}) has missing unit in metadata."
        logger.warning(msg)
        return None, "unknown", False, msg
        
    approved_map = APPROVED_UNITS[param_clean]
    if meta_unit not in approved_map:
        msg = f"EXCLUDED: Sensor ID {sensor_id} ({param}) has unexpected unit '{meta_unit}' not in approved list {list(approved_map.keys())}."
        logger.warning(msg)
        return None, meta_unit, False, msg
        
    multiplier, target_unit = approved_map[meta_unit]
    converted_val = round(float(val) * multiplier, 4 if param_clean == "co" else 2)
    return converted_val, target_unit, True, None
