import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# 1. Fetch location 50 metadata and all sensors
loc_resp = requests.get("https://api.openaq.org/v3/locations/50", headers=headers).json()
sensors = loc_resp["results"][0]["sensors"]
print("Station 50 Sensors:")
for s in sensors:
    print(f"  Sensor ID: {s['id']:<10} Parameter: {s.get('parameter', {}).get('name'):<10} Units: {s.get('parameter', {}).get('units'):<10} Display: {s.get('parameter', {}).get('displayName')}")

# Window: 2026-04-27 23:00:00Z to 2026-04-28 12:00:00Z
dt_from = "2026-04-27T22:00:00Z"
dt_to = "2026-04-28T12:00:00Z"

# Find PM2.5 and PM10 sensors
pm_sensors = [s for s in sensors if s.get("parameter", {}).get("name") in ["pm25", "pm10"]]

print("\n" + "="*80)
print(f"RAW HOURLY RECORDS FOR STATION 50 ({dt_from} to {dt_to})")
print("="*80)

raw_records = {}
for s in pm_sensors:
    sid = s["id"]
    pname = s.get("parameter", {}).get("name")
    punits = s.get("parameter", {}).get("units")
    url = f"https://api.openaq.org/v3/sensors/{sid}/hours"
    r = requests.get(url, headers=headers, params={"datetime_from": dt_from, "datetime_to": dt_to, "limit": 100}).json()
    items = r.get("results", [])
    raw_records[sid] = {
        "param": pname,
        "units": punits,
        "items": items
    }
    print(f"\n--- SENSOR {sid} ({pname}, {punits}) --- Total records: {len(items)}")
    for item in items:
        dt_utc = item.get("period", {}).get("datetimeFrom", {}).get("utc")
        dt_loc = item.get("period", {}).get("datetimeFrom", {}).get("local")
        val = item.get("value")
        flag = item.get("flagInfo")
        cov = item.get("coverage", {}).get("percentCoverage")
        print(f"UTC: {dt_utc} | Local (IST): {dt_loc} | Val: {val} {punits} | Flag: {flag} | Cov: {cov}%")

with open("data/station50_investigation.json", "w") as f:
    json.dump(raw_records, f, indent=2)
