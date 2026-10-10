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
    raise ValueError("OPENAQ_API_KEY is not set in .env")

headers = {"X-API-Key": api_key, "Accept": "application/json"}

DATA_DIR = os.path.join(os.path.dirname(__file__), "stations_hourly")
os.makedirs(DATA_DIR, exist_ok=True)

START_UTC = "2026-04-01T00:00:00Z"
END_UTC = "2026-10-01T00:00:00Z"
# 183 days * 24 hours = 4392 hours
EXPECTED_HOURS = 4392
COVERAGE_THRESHOLD = 0.80 # 80%

def fetch_sensor_hours(sensor_id, max_retries=4):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours"
    records = []
    page = 1
    while page <= 6:
        params = {
            "datetime_from": START_UTC,
            "datetime_to": END_UTC,
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

def process_station(station_info):
    station_id = station_info["id"]
    station_name = station_info["name"]
    cache_path = os.path.join(DATA_DIR, f"station_{station_id}.json")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
                if cached.get("station_id") and "coverage_pct" in cached:
                    return cached
        except Exception:
            pass

    try:
        sensors = station_info.get("sensors", [])
        param_sensors = {}
        for s in sensors:
            pname = s.get("parameter", {}).get("name")
            sid = s.get("id")
            if pname in ["pm25", "pm10", "no2", "co"]:
                if pname not in param_sensors or sid > param_sensors[pname]:
                    param_sensors[pname] = sid
                    
        if not param_sensors or "pm25" not in param_sensors:
            return None
            
        station_result = {
            "station_id": station_id,
            "name": station_name,
            "coordinates": station_info.get("coordinates"),
            "sensors": param_sensors,
            "hourly_counts": {},
            "coverage_pct": {},
            "data": {}
        }
        
        for param, sid in param_sensors.items():
            records = fetch_sensor_hours(sid)
            ts_data = {}
            for r in records:
                period = r.get("period", {})
                dt = period.get("datetimeFrom", {}).get("utc")
                val = r.get("value")
                if dt and val is not None:
                    ts_data[dt] = val
                    
            station_result["hourly_counts"][param] = len(ts_data)
            coverage = len(ts_data) / EXPECTED_HOURS
            station_result["coverage_pct"][param] = round(coverage * 100, 2)
            station_result["data"][param] = ts_data
            
        with open(cache_path, "w") as f:
            json.dump(station_result, f)
            
        return station_result
    except Exception as e:
        print(f"Error processing station {station_id}: {e}", flush=True)
        return None

def main():
    with open("data/active_stations.json") as f:
        stations = json.load(f)
        
    candidates = [s for s in stations if "pm25" in s.get("parameters", [])]
    target_count = 35 # Sufficient to firmly verify the 25 station threshold
    selected_candidates = candidates[:target_count]
    
    print(f"Evaluating {len(selected_candidates)} Delhi-NCR stations for 6-month coverage ({START_UTC} to {END_UTC})...", flush=True)
    
    results = []
    # Check already cached
    for s in selected_candidates:
        cpath = os.path.join(DATA_DIR, f"station_{s['id']}.json")
        if os.path.exists(cpath):
            try:
                with open(cpath) as f:
                    cached = json.load(f)
                    results.append(cached)
                    print(f"[CACHED {len(results)}/{len(selected_candidates)}] Station {cached['station_id']} ({cached['name'][:25]}): PM2.5={cached['coverage_pct'].get('pm25')}%, PM10={cached['coverage_pct'].get('pm10')}%", flush=True)
            except Exception:
                pass
                
    remaining = [s for s in selected_candidates if not any(r["station_id"] == s["id"] for r in results)]
    print(f"{len(results)} stations loaded from cache; fetching remaining {len(remaining)} stations...", flush=True)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_station = {executor.submit(process_station, s): s for s in remaining}
        for future in as_completed(future_to_station):
            s = future_to_station[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
                    pm25_cov = res.get("coverage_pct", {}).get("pm25", 0)
                    pm10_cov = res.get("coverage_pct", {}).get("pm10", 0)
                    print(f"[{len(results)}/{len(selected_candidates)}] Station {res['station_id']} ({res['name'][:25]}): PM2.5={pm25_cov}%, PM10={pm10_cov}%", flush=True)
            except Exception as e:
                print(f"Station {s['id']} failed: {e}", flush=True)
                
    usable_pm25 = [r for r in results if r.get("coverage_pct", {}).get("pm25", 0) >= 80.0]
    usable_both_pm = [r for r in results if r.get("coverage_pct", {}).get("pm25", 0) >= 80.0 and r.get("coverage_pct", {}).get("pm10", 0) >= 80.0]
    usable_all_4 = [r for r in results if all(r.get("coverage_pct", {}).get(p, 0) >= 80.0 for p in ["pm25", "pm10", "no2", "co"])]
    
    summary = {
        "total_evaluated": len(results),
        "expected_hours_6m": EXPECTED_HOURS,
        "stations_pm25_ge_80": len(usable_pm25),
        "stations_pm25_and_pm10_ge_80": len(usable_both_pm),
        "stations_all_4_ge_80": len(usable_all_4),
        "gate_threshold": 25,
        "gate_passed": len(usable_pm25) >= 25,
        "station_details": [
            {
                "id": r["station_id"],
                "name": r["name"],
                "coordinates": r["coordinates"],
                "coverage_pct": r["coverage_pct"],
                "hourly_counts": r["hourly_counts"]
            }
            for r in results
        ]
    }
    
    with open("data/coverage_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    print("\n" + "="*50, flush=True)
    print("DATA FEASIBILITY SUMMARY (DELHI-NCR 6 MONTHS)", flush=True)
    print("="*50, flush=True)
    print(f"Total Stations Evaluated         : {len(results)}", flush=True)
    print(f"Stations with PM2.5 >= 80%       : {len(usable_pm25)}", flush=True)
    print(f"Stations with PM2.5 & PM10 >= 80%: {len(usable_both_pm)}", flush=True)
    print(f"Stations with all 4 >= 80%       : {len(usable_all_4)}", flush=True)
    print(f"GATE THRESHOLD                   : >= 25 stations", flush=True)
    print(f"GATE STATUS                      : {'PASSED' if summary['gate_passed'] else 'FAILED'}", flush=True)
    print("="*50, flush=True)

if __name__ == "__main__":
    main()
