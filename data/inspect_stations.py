import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# OpenAQ bbox for Delhi-NCR: min_lon, min_lat, max_lon, max_lat
url = "https://api.openaq.org/v3/locations"
params = {
    "bbox": "76.70,28.20,77.60,28.95",
    "limit": 100
}

all_locations = []
page = 1
while True:
    params["page"] = page
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"Error page {page}: {resp.status_code}")
        break
    data = resp.json()
    results = data.get("results", [])
    if not results:
        break
    all_locations.extend(results)
    print(f"Page {page}: fetched {len(results)} locations (total {len(all_locations)})")
    if len(results) < params["limit"]:
        break
    page += 1

print(f"\nTotal locations returned: {len(all_locations)}")

# Filter for locations active in 2026 or with recent data
active_locations = []
for loc in all_locations:
    dt_last = loc.get("datetimeLast")
    if dt_last and isinstance(dt_last, dict):
        utc = dt_last.get("utc", "")
        # Check if last record is in 2026 or 2025
        if utc.startswith("2026") or utc.startswith("2025"):
            params_available = [s.get("parameter", {}).get("name") for s in loc.get("sensors", [])]
            active_locations.append({
                "id": loc.get("id"),
                "name": loc.get("name"),
                "coordinates": loc.get("coordinates"),
                "last_utc": utc,
                "first_utc": loc.get("datetimeFirst", {}).get("utc") if loc.get("datetimeFirst") else None,
                "sensors": loc.get("sensors", []),
                "parameters": params_available
            })

print(f"Active locations (2025-2026): {len(active_locations)}")
with open("data/active_stations.json", "w") as f:
    json.dump(active_locations, f, indent=2)

print("\nSample active stations:")
for a in active_locations[:10]:
    print(f"[{a['id']}] {a['name']} | Last: {a['last_utc']} | Params: {a['parameters']}")
