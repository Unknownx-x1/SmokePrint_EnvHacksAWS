import requests
import json

# Test Open-Meteo for Delhi center (lat 28.61, lon 77.21)
# Wind speed, wind direction at 10m and 100m, boundary layer height
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": 28.6139,
    "longitude": 77.2090,
    "start_date": "2026-04-01",
    "end_date": "2026-09-30",
    "hourly": ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "surface_pressure", "boundary_layer_height"]
}

try:
    resp = requests.get(url, params=params, timeout=15)
    print("Archive API status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        hourly = data.get("hourly", {})
        print("Variables returned:", list(hourly.keys()))
        times = hourly.get("time", [])
        print(f"Total hourly points: {len(times)}")
        if times:
            print(f"Range: {times[0]} to {times[-1]}")
            print(f"Sample wind: speed={hourly['wind_speed_10m'][0]} km/h, dir={hourly['wind_direction_10m'][0]} deg")
    else:
        print("Archive error:", resp.text[:300])
        # Try standard API with past_days or forecast
        url2 = "https://api.open-meteo.com/v1/forecast"
        p2 = {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "past_days": 90,
            "forecast_days": 0,
            "hourly": ["wind_speed_10m", "wind_direction_10m"]
        }
        r2 = requests.get(url2, params=p2)
        print("Forecast API past_days status:", r2.status_code)
        if r2.status_code == 200:
            print("Forecast past points:", len(r2.json().get("hourly", {}).get("time", [])))
except Exception as e:
    print("Open-Meteo error:", e)
