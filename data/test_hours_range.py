import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Let's test R K Puram (id: 17) sensor for pm25
# Find pm25 sensor id
loc_resp = requests.get("https://api.openaq.org/v3/locations/17", headers=headers).json()
sensors = loc_resp["results"][0]["sensors"]
pm25_sensor = next(s["id"] for s in sensors if s.get("parameter", {}).get("name") == "pm25")
print(f"PM25 sensor ID for R K Puram: {pm25_sensor}")

# Check hours with datetime_from and datetime_to (last 6 months: 2026-04-01 to 2026-10-01)
# Note: let's test what query parameters /hours supports
params = {
    "datetime_from": "2026-04-01T00:00:00Z",
    "datetime_to": "2026-10-01T00:00:00Z",
    "limit": 1000
}
resp = requests.get(f"https://api.openaq.org/v3/sensors/{pm25_sensor}/hours", headers=headers, params=params)
print("Hours query status:", resp.status_code)
if resp.status_code == 200:
    res = resp.json()
    print("Found count:", len(res.get("results", [])))
    if res.get("results"):
        print("First record:", res.get("results")[0]["period"]["datetimeFrom"])
        print("Last record:", res.get("results")[-1]["period"]["datetimeFrom"])
else:
    print(resp.text[:500])
