import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAQ_API_KEY")

headers = {
    "X-API-Key": api_key,
    "Accept": "application/json"
}

# Test query for locations in Delhi-NCR bbox: min_lon, min_lat, max_lon, max_lat
url = "https://api.openaq.org/v3/locations"
params = {
    "bbox": "76.70,28.20,77.60,28.95",
    "limit": 100
}

try:
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    print("OpenAQ Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        results = data.get("results", [])
        print(f"Found {len(results)} locations in Delhi-NCR")
        if results:
            print("Sample location:", results[0].get("id"), results[0].get("name"))
            print("Sensors/parameters:", [s.get("parameter", {}).get("name") for s in results[0].get("sensors", [])])
    else:
        print("Response text:", resp.text[:500])
except Exception as e:
    print("Error:", e)
