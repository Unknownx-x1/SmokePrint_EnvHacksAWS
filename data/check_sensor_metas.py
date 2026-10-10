import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Let's inspect 5 active stations and their sensors
with open("data/active_stations.json") as f:
    stations = json.load(f)

for st in stations[:3]:
    loc_id = st["id"]
    r = requests.get(f"https://api.openaq.org/v3/locations/{loc_id}", headers=headers).json()
    res = r.get("results", [{}])[0]
    print(f"\nLocation {loc_id} ({res.get('name')}):")
    for s in res.get("sensors", []):
        param = s.get("parameter", {}).get("name")
        if param in ["pm25", "pm10", "no2", "co"]:
            sid = s["id"]
            # fetch sensor metadata
            s_meta = requests.get(f"https://api.openaq.org/v3/sensors/{sid}", headers=headers).json()
            s_info = s_meta.get("results", [{}])[0]
            cov = s_info.get("coverage", {})
            print(f"  Sensor {sid} ({param}): observedCount={cov.get('observedCount')}, from={cov.get('datetimeFrom', {}).get('utc')}, to={cov.get('datetimeTo', {}).get('utc')}")
