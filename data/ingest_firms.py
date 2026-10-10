import os
import io
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
map_key = os.getenv("FIRMS_MAP_KEY")
if not map_key:
    raise ValueError("FIRMS_MAP_KEY not found in .env")

# Delhi NCR bbox: min_lon, min_lat, max_lon, max_lat
BBOX_STR = "76.7,28.2,77.6,28.95"
OUTPUT_PATH = "data/firms_fires_6m.json"

def fetch_firms_window(date_str=None, day_range=5, source="VIIRS_SNPP_NRT"):
    """
    Fetch FIRMS fires for a given date and day_range in Delhi-NCR bbox.
    """
    if date_str:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{BBOX_STR}/{day_range}/{date_str}"
    else:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{BBOX_STR}/{day_range}"
        
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200 and "latitude" in resp.text:
            df = pd.read_csv(io.StringIO(resp.text))
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching FIRMS for {date_str}: {e}")
        return pd.DataFrame()

def ingest_firms_ncr():
    print(f"Ingesting NASA FIRMS fires for Delhi-NCR bbox ({BBOX_STR})...")
    # Sample key dates across the 6-month period (e.g. every 10 days) + recent 5 days
    sample_dates = [
        "2026-04-15", "2026-05-01", "2026-05-15", "2026-06-01",
        "2026-06-15", "2026-07-01", "2026-07-15", "2026-08-01",
        "2026-08-15", "2026-09-01", "2026-09-15", "2026-09-30"
    ]
    
    all_dfs = []
    # 1. Fetch current 5 days
    df_recent = fetch_firms_window(day_range=5)
    if not df_recent.empty:
        all_dfs.append(df_recent)
        print(f"Fetched {len(df_recent)} fire detections from recent 5-day window.")
        
    # 2. Fetch sampled historical windows
    for dt in sample_dates:
        df_hist = fetch_firms_window(date_str=dt, day_range=5)
        if not df_hist.empty:
            all_dfs.append(df_hist)
            print(f"Fetched {len(df_hist)} detections for 5-day window around {dt}.")
            
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        # Drop duplicates by coordinates and acquisition timestamp
        combined = combined.drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time"])
        print(f"\nTotal unique FIRMS thermal detections in NCR: {len(combined)}")
        
        # Save to JSON
        records = combined.to_dict(orient="records")
        with open(OUTPUT_PATH, "w") as f:
            json.dump({
                "source": "NASA FIRMS (VIIRS_SNPP_NRT)",
                "bbox": BBOX_STR,
                "total_fire_detections": len(records),
                "detections": records
            }, f, indent=2)
            
        print(f"Saved to {OUTPUT_PATH}")
        return records
    else:
        print("No FIRMS detections found.")
        return []

if __name__ == "__main__":
    ingest_firms_ncr()
