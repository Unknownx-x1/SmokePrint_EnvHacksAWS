import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAQ_API_KEY")
headers = {"X-API-Key": api_key}

def fetch_sensor_hours(sensor_id, dt_from="2026-04-01T00:00:00Z", dt_to="2026-10-01T00:00:00Z"):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours"
    all_records = []
    page = 1
    while True:
        params = {
            "datetime_from": dt_from,
            "datetime_to": dt_to,
            "limit": 1000,
            "page": page
        }
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=12)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    all_records.extend(results)
                    if len(results) < 1000:
                        return all_records
                    break
                elif resp.status_code == 429:
                    time.sleep(1.0 * (attempt + 1))
                else:
                    return all_records
            except Exception:
                time.sleep(0.5)
        page += 1
        if page > 6:
            break
    return all_records

t0 = time.time()
rec = fetch_sensor_hours(12234787)
t1 = time.time()
print(f"Fetched {len(rec)} hours for sensor 12234787 in {t1 - t0:.2f} seconds")
