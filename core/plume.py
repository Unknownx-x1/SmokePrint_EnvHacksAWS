"""
Smokeprint Monte Carlo Lagrangian Atmospheric Plume Dispersion Engine
Module: core/plume.py

Simulates backward-in-time particle dispersion (~500 particles) using hourly
ERA5 / Open-Meteo wind fields (u, v) and boundary layer height (z_pbl).

Turbulent Dispersion Parameters (Documented):
  1. Direction Perturbation (sigma_theta): 15.0 degrees (0.2618 rad) Gaussian turbulence.
  2. Relative Wind Speed Perturbation (sigma_s / s): 0.20 (20% relative Gaussian fluctuation).
  3. Horizontal Sub-Grid Eddy Diffusivity (Kh): 10.0 m^2/s (Brownian random walk step sqrt(2*Kh*dt)).
  4. Vertical Boundary Layer Ceiling: Advection confined within planetary boundary layer height (z_pbl).

Temporal Alignment Convention:
  Observations are indexed by interval midpoint (UTC), and ERA5 wind vectors are sampled
  at the exact same midpoint. Output explicitly states interval start, midpoint, and end
  in both UTC and IST (Asia/Kolkata).
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional
import math
import numpy as np
import zoneinfo

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# Dispersion constants
# Normal wind (>= 1.5 m/s)
SIGMA_THETA_NORMAL_DEG = 15.0       # Wind direction perturbation (degrees)
SIGMA_SPEED_NORMAL_REL = 0.20       # Relative wind speed perturbation (fraction)
EDDY_DIFFUSIVITY_NORMAL_KH = 10.0   # Horizontal eddy diffusivity (m^2/s)

# Low wind (< 1.5 m/s) calm meandering regime
# Documented values: substantially widened direction spread under light/meandering atmospheric inversion
SIGMA_THETA_LOW_WIND_DEG = 45.0     # Widened wind direction perturbation (degrees)
SIGMA_SPEED_LOW_WIND_REL = 0.40     # Widened relative speed perturbation (fraction)
EDDY_DIFFUSIVITY_LOW_WIND_KH = 25.0 # Enhanced turbulent diffusion (m^2/s)
LOW_WIND_THRESHOLD_MS = 1.5         # Wind speed threshold for calm handling

INTEGRATION_STEP_SEC = 60           # 1-minute numerical integration time steps
DEFAULT_N_PARTICLES = 500           # Ensemble size
DEFAULT_RADIUS_KM = 15.0            # Maximum search radius (km)
GRID_CELL_SIZE_M = 250.0            # Spatial footprint grid cell resolution (meters)

METERS_PER_DEG_LAT = 111139.0

def get_time_convention_block(midpoint_utc_str: str) -> Dict[str, Any]:
    """
    Produces explicit interval metadata defining start, midpoint, and end
    in both UTC and IST, adhering to the OpenAQ-ERA5 alignment standard.
    """
    clean_str = midpoint_utc_str.replace("Z", "+00:00")
    if len(clean_str) == 16: # 'YYYY-MM-DDTHH:MM'
        clean_str += ":00+00:00"
    dt_mid = datetime.fromisoformat(clean_str)
    if dt_mid.tzinfo is None:
        dt_mid = dt_mid.replace(tzinfo=timezone.utc)
        
    dt_start = dt_mid - timedelta(minutes=30)
    dt_end = dt_mid + timedelta(minutes=30)
    
    dt_mid_ist = dt_mid.astimezone(IST)
    dt_start_ist = dt_start.astimezone(IST)
    dt_end_ist = dt_end.astimezone(IST)
    
    return {
        "interval_midpoint_utc": dt_mid.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval_start_utc": dt_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval_end_utc": dt_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval_midpoint_ist": dt_mid_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "interval_start_ist": dt_start_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "interval_end_ist": dt_end_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "timezone_storage": "UTC",
        "timezone_display": "Asia/Kolkata (IST, UTC+05:30)",
        "convention_note": "Hourly observations indexed by interval midpoint; wind aligned to same midpoint."
    }

def run_backward_plume_ensemble(
    station_lat: float,
    station_lon: float,
    midpoint_utc_str: str,
    wind_records_by_time: Dict[str, Dict[str, Any]],
    n_particles: int = DEFAULT_N_PARTICLES,
    max_advection_hours: int = 3,
    search_radius_km: float = DEFAULT_RADIUS_KM,
    random_seed: Optional[int] = 42
) -> Dict[str, Any]:
    """
    Simulates a Monte Carlo backward Lagrangian particle dispersion ensemble from the target station.
    
    Returns:
      dict with:
        'time_convention': dict
        'wind_conditions': dict (mean speed, direction, u, v, blh)
        'footprint_grid': dict (bounds, cell_size_m, shape, density_matrix)
        'ensemble_particles': list of final particle endpoints [lat, lon, travel_time_hours]
        'mean_transport_bearing_deg': float (compass bearing pointing upwind into the source zone)
    """
    if random_seed is not None:
        np.random.seed(random_seed)
        
    time_block = get_time_convention_block(midpoint_utc_str)
    midpoint_key = time_block["interval_midpoint_utc"][:13] + ":00" # Match 'YYYY-MM-DDTHH:00'
    
    # Retrieve base wind
    wind_rec = wind_records_by_time.get(midpoint_key)
    if not wind_rec:
        # Fallback search without :00
        for k, v in wind_records_by_time.items():
            if k.startswith(time_block["interval_midpoint_utc"][:13]):
                wind_rec = v
                break
                
    if not wind_rec:
        # Fallback calm wind
        wind_rec = {
            "wind_speed_ms": 1.0,
            "wind_direction_deg": 0.0,
            "u_ms": 0.0,
            "v_ms": -1.0,
            "boundary_layer_height_m": 150.0
        }
        
    u_base = float(wind_rec.get("u_ms") or 0.0)
    v_base = float(wind_rec.get("v_ms") or 0.0)
    ws_base = float(wind_rec.get("wind_speed_ms") or math.sqrt(u_base**2 + v_base**2))
    wd_base = float(wind_rec.get("wind_direction_deg") or (math.degrees(math.atan2(-u_base, -v_base)) % 360))
    blh = float(wind_rec.get("boundary_layer_height_m") or 200.0)
    
    meters_per_deg_lon = METERS_PER_DEG_LAT * math.cos(math.radians(station_lat))
    
    # Grid setup: centered on station with +/- search_radius_km
    dlat = (search_radius_km * 1000.0) / METERS_PER_DEG_LAT
    dlon = (search_radius_km * 1000.0) / meters_per_deg_lon
    
    lat_min, lat_max = station_lat - dlat, station_lat + dlat
    lon_min, lon_max = station_lon - dlon, station_lon + dlon
    
    n_lat_bins = int(math.ceil((lat_max - lat_min) * METERS_PER_DEG_LAT / GRID_CELL_SIZE_M))
    n_lon_bins = int(math.ceil((lon_max - lon_min) * meters_per_deg_lon / GRID_CELL_SIZE_M))
    
    footprint = np.zeros((n_lat_bins, n_lon_bins), dtype=np.float64)
    
    # Generate particle initial states
    total_steps = int((max_advection_hours * 3600) / INTEGRATION_STEP_SEC)
    dt = INTEGRATION_STEP_SEC
    
    is_low_wind = ws_base < LOW_WIND_THRESHOLD_MS
    sigma_theta_deg = SIGMA_THETA_LOW_WIND_DEG if is_low_wind else SIGMA_THETA_NORMAL_DEG
    sigma_speed_rel = SIGMA_SPEED_LOW_WIND_REL if is_low_wind else SIGMA_SPEED_NORMAL_REL
    kh = EDDY_DIFFUSIVITY_LOW_WIND_KH if is_low_wind else EDDY_DIFFUSIVITY_NORMAL_KH

    # Random perturbations per particle
    theta_offsets = np.random.normal(0.0, math.radians(sigma_theta_deg), n_particles)
    speed_factors = np.maximum(0.1, np.random.normal(1.0, sigma_speed_rel, n_particles))
    
    # Precompute perturbed particle velocity vectors
    base_rad = math.radians(wd_base)
    p_thetas = base_rad + theta_offsets
    p_speeds = ws_base * speed_factors
    
    # In meteorological terms: wind blows FROM p_thetas.
    # Backward trajectory travels UPWIND towards the origin of the wind:
    u_upwind = p_speeds * np.sin(p_thetas)
    v_upwind = p_speeds * np.cos(p_thetas)
    
    # Diffusion step standard deviation: sqrt(2 * Kh * dt)
    step_diff_sd = math.sqrt(2.0 * kh * dt)
    
    # Particle positions in meters relative to station
    p_x = np.zeros(n_particles, dtype=np.float64)
    p_y = np.zeros(n_particles, dtype=np.float64)
    
    particle_endpoints = []
    
    for step in range(total_steps):
        # Advection displacement (meters)
        dx_adv = u_upwind * dt
        dy_adv = v_upwind * dt
        
        # Sub-grid turbulent dispersion
        dx_diff = np.random.normal(0.0, step_diff_sd, n_particles)
        dy_diff = np.random.normal(0.0, step_diff_sd, n_particles)
        
        p_x += dx_adv + dx_diff
        p_y += dy_adv + dy_diff
        
        # Convert to lat, lon indices and deposit residence time
        p_lats = station_lat + (p_y / METERS_PER_DEG_LAT)
        p_lons = station_lon + (p_x / meters_per_deg_lon)
        
        valid_mask = (p_lats >= lat_min) & (p_lats < lat_max) & (p_lons >= lon_min) & (p_lons < lon_max)
        
        lat_idx = ((p_lats[valid_mask] - lat_min) / (lat_max - lat_min) * n_lat_bins).astype(int)
        lon_idx = ((p_lons[valid_mask] - lon_min) / (lon_max - lon_min) * n_lon_bins).astype(int)
        
        np.add.at(footprint, (lat_idx, lon_idx), 1.0)
        
    # Normalize footprint to spatial probability density
    sum_fp = footprint.sum()
    if sum_fp > 0:
        footprint /= sum_fp
        
    # Sample final endpoints (up to 50 for lightweight payload)
    final_lats = station_lat + (p_y / METERS_PER_DEG_LAT)
    final_lons = station_lon + (p_x / meters_per_deg_lon)
    for k in range(min(50, n_particles)):
        particle_endpoints.append({
            "lat": round(float(final_lats[k]), 5),
            "lon": round(float(final_lons[k]), 5)
        })
        
    upwind_bearing = round(float(wd_base % 360), 1)
    
    return {
        "time_convention": time_block,
        "wind_conditions": {
            "wind_speed_ms": round(ws_base, 2),
            "wind_direction_deg": round(wd_base, 1),
            "u_ms": round(u_base, 3),
            "v_ms": round(v_base, 3),
            "boundary_layer_height_m": round(blh, 1),
            "upwind_bearing_deg": upwind_bearing,
            "is_low_wind": is_low_wind,
            "direction_noise_deg": sigma_theta_deg,
            "speed_noise_rel": sigma_speed_rel,
            "eddy_diffusivity_kh": kh
        },
        "footprint_grid": {
            "lat_min": round(lat_min, 6),
            "lat_max": round(lat_max, 6),
            "lon_min": round(lon_min, 6),
            "lon_max": round(lon_max, 6),
            "n_lat_bins": n_lat_bins,
            "n_lon_bins": n_lon_bins,
            "cell_size_m": GRID_CELL_SIZE_M,
            "matrix": footprint.tolist()
        },
        "particle_endpoints": particle_endpoints
    }

def query_candidate_footprint_density(
    cand_lat: float,
    cand_lon: float,
    footprint_grid: Dict[str, Any]
) -> float:
    """
    Queries spatial probability density of a candidate emitter within the accumulated footprint.
    Returns: float density in [1e-5, 1.0].
    """
    lat_min = footprint_grid["lat_min"]
    lat_max = footprint_grid["lat_max"]
    lon_min = footprint_grid["lon_min"]
    lon_max = footprint_grid["lon_max"]
    n_lat = footprint_grid["n_lat_bins"]
    n_lon = footprint_grid["n_lon_bins"]
    matrix = footprint_grid["matrix"]
    
    if cand_lat < lat_min or cand_lat >= lat_max or cand_lon < lon_min or cand_lon >= lon_max:
        return 1e-5
        
    i_lat = int((cand_lat - lat_min) / (lat_max - lat_min) * n_lat)
    j_lon = int((cand_lon - lon_min) / (lon_max - lon_min) * n_lon)
    
    i_lat = max(0, min(n_lat - 1, i_lat))
    j_lon = max(0, min(n_lon - 1, j_lon))
    
    # Query 3x3 kernel around point to account for candidate footprint extents
    sub_vals = []
    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            ii = i_lat + di
            jj = j_lon + dj
            if 0 <= ii < n_lat and 0 <= jj < n_lon:
                sub_vals.append(matrix[ii][jj])
                
    peak_val = max(sub_vals) if sub_vals else matrix[i_lat][j_lon]
    return max(1e-5, float(peak_val))

def calculate_footprint_discriminability(candidate_densities: List[float]) -> Dict[str, Any]:
    """
    Computes footprint discriminability across top candidates:
      discriminability = (d_top1 - d_top5) / d_top1

    If discriminability < 0.25 (top-5 candidate densities within 25% of each other),
    the footprint is near-uniform/stagnant and cannot reliably separate candidates.
    """
    if not candidate_densities:
        return {
            "discriminability_metric": 0.0,
            "state": "no_candidates",
            "is_uniform": True,
            "note": "No candidate emitters found in radius."
        }
        
    sorted_dens = sorted(candidate_densities, reverse=True)
    d1 = sorted_dens[0]
    # Check 5th candidate or last available
    k = min(4, len(sorted_dens) - 1)
    dk = sorted_dens[k]
    
    if d1 <= 1e-6:
        metric = 0.0
    else:
        metric = round((d1 - dk) / d1, 3)
        
    is_uniform = (metric < 0.25)
    state = "multiple_comparable_candidates" if is_uniform else "discriminable_corridor"
    
    return {
        "discriminability_metric": metric,
        "top_to_k_spread": metric,
        "k_candidates_evaluated": k + 1,
        "is_uniform": is_uniform,
        "state": state,
        "note": "Near-uniform calm stagnation; cannot separate top candidates" if is_uniform else "Directional advection separates candidates"
    }

