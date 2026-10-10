import os
import sys
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAQ_API_KEY")
if not api_key:
    raise ValueError("OPENAQ_API_KEY not found")

headers = {"X-API-Key": api_key, "Accept": "application/json"}

WINTER_START = "2025-10-01T00:00:00Z"
WINTER_END   = "2026-04-01T00:00:00Z"

OUT_DIR = "data/stations_12m"
os.makedirs(OUT_DIR, exist_ok=True)

def fetch_sensor_hours_range(sensor_id, dt_from, dt_to, max_retries=3):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours"
    records = []
    page = 1
    while page <= 6:
        params = {
            "datetime_from": dt_from,
            "datetime_to": dt_to,
            "limit": 1000,
            "page": page
        }
        success = False
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=12)
                if resp.status_code == 200:
                    data = resp.json().get("results", [])
                    records.extend(data)
                    success = True
                    if len(data) < 1000:
                        return records
                    break
                elif resp.status_code == 429:
                    time.sleep(1.2 * (2 ** attempt))
                else:
                    time.sleep(0.5)
            except Exception:
                time.sleep(0.5)
        if not success:
            break
        page += 1
    return records

def process_station_12m(station_id):
    # Check if existing 6m data exists
    p6m = f"data/stations_hourly/station_{station_id}.json"
    p12m = os.path.join(OUT_DIR, f"station_{station_id}_12m.json")
    
    if os.path.exists(p12m):
        with open(p12m) as fp:
            return json.load(fp)
            
    if not os.path.exists(p6m):
        return None
        
    with open(p6m) as fp:
        st_data = json.load(fp)
        
    sensors = st_data.get("sensors", {})
    full_data = {}
    
    # Existing data is 2026-04-01 to 2026-10-01
    existing_data = st_data.get("data", {})
    
    for param, sid in sensors.items():
        winter_records = fetch_sensor_hours_range(sid, WINTER_START, WINTER_END)
        # Parse winter records
        combined_ts = {}
        for r in winter_records:
            period = r.get("period", {})
            dt = period.get("datetimeFrom", {}).get("utc")
            val = r.get("value")
            if dt and val is not None:
                combined_ts[dt] = val
                
        # Merge with existing 6m data
        ex_ts = existing_data.get(param, {})
        combined_ts.update(ex_ts)
        full_data[param] = combined_ts
        
    res = {
        "station_id": station_id,
        "name": st_data.get("name"),
        "coordinates": st_data.get("coordinates"),
        "sensors": sensors,
        "data": full_data
    }
    
    with open(p12m, "w") as fp:
        json.dump(res, fp)
        
    return res

def main():
    import glob
    files = glob.glob("data/stations_hourly/station_*.json")
    station_ids = [int(os.path.basename(f).replace("station_", "").replace(".json", "")) for f in files]
    print(f"Expanding {len(station_ids)} stations to full 12 months (Oct 2025 - Sep 2026)...", flush=True)
    
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futs = {executor.submit(process_station_12m, sid): sid for sid in station_ids}
        for fut in as_completed(futs):
            sid = futs[fut]
            try:
                r = fut.result()
                if r:
                    results.append(r)
                    p25_count = len(r.get("data", {}).get("pm25", {}))
                    print(f"[{len(results)}/{len(station_ids)}] Station {sid} ({r['name'][:25]}): {p25_count} PM2.5 hourly records across 12m", flush=True)
            except Exception as e:
                print(f"Failed station {sid}: {e}", flush=True)
                
    print(f"Successfully compiled 12-month records for {len(results)} stations.", flush=True)

if __name__ == "__main__":
    main()
