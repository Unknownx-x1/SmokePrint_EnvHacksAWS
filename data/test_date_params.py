import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Test different query parameter variations for date ranges on sensor 12234787
variants = [
    {"datetime_from": "2026-04-01T00:00:00Z", "datetime_to": "2026-04-02T00:00:00Z"},
    {"date_from": "2026-04-01T00:00:00Z", "date_to": "2026-04-02T00:00:00Z"},
    {"datetime_from": "2026-04-01", "datetime_to": "2026-04-02"},
]

for var in variants:
    resp = requests.get("https://api.openaq.org/v3/sensors/12234787/hours", headers=headers, params=var)
    data = resp.json()
    print(var, "Status:", resp.status_code, "Count:", len(data.get("results", [])))
    if data.get("results"):
        print("  Sample date:", data.get("results")[0]["period"]["datetimeFrom"])
