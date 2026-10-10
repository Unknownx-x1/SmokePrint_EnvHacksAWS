import os
import math
import json
import requests

def fetch_meteo_wind(
    lat=28.6139,
    lon=77.2090,
    start_date="2026-04-01",
    end_date="2026-09-30",
    output_path="data/wind_hourly_6m.json"
):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "surface_pressure",
            "boundary_layer_height"
        ]
    }
    
    print(f"Fetching Open-Meteo ERA5 wind data for ({lat}, {lon}) from {start_date} to {end_date}...")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    speeds = hourly.get("wind_speed_10m", [])
    dirs = hourly.get("wind_direction_10m", [])
    blhs = hourly.get("boundary_layer_height", [])
    pressures = hourly.get("surface_pressure", [])
    
    records = []
    for i in range(len(times)):
        t = times[i]
        ws = speeds[i] # km/h
        wd = dirs[i]   # degrees (direction wind is coming from)
        blh = blhs[i] if i < len(blhs) else None
        p = pressures[i] if i < len(pressures) else None
        
        # Convert wind speed to m/s
        ws_ms = (ws * 1000.0 / 3600.0) if ws is not None else None
        
        # Meteorological convention: direction wind is COMING from
        # u = -ws * sin(theta), v = -ws * cos(theta) (pointing in the direction wind blows TO)
        u_ms = None
        v_ms = None
        if ws_ms is not None and wd is not None:
            rad = math.radians(wd)
            u_ms = -ws_ms * math.sin(rad)
            v_ms = -ws_ms * math.cos(rad)
            
        records.append({
            "time": t,
            "wind_speed_kmh": ws,
            "wind_speed_ms": round(ws_ms, 2) if ws_ms is not None else None,
            "wind_direction_deg": wd,
            "u_ms": round(u_ms, 3) if u_ms is not None else None,
            "v_ms": round(v_ms, 3) if v_ms is not None else None,
            "boundary_layer_height_m": blh,
            "surface_pressure_hpa": p
        })
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "source": "Open-Meteo ERA5 reanalysis",
            "coordinates": {"latitude": lat, "longitude": lon},
            "total_hours": len(records),
            "start_time": times[0] if times else None,
            "end_time": times[-1] if times else None,
            "records": records
        }, f, indent=2)
        
    print(f"Successfully saved {len(records)} hourly wind records to {output_path}")
    return records

if __name__ == "__main__":
    fetch_meteo_wind()
