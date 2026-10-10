import os
import requests
from dotenv import load_dotenv

load_dotenv()
map_key = os.getenv("FIRMS_MAP_KEY")

# Delhi NCR bbox: min_lon, min_lat, max_lon, max_lat = 76.70, 28.20, 77.60, 28.95
bbox_str = "76.7,28.2,77.6,28.95"

# Let's test FIRMS area endpoint for last 10 days
url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{bbox_str}/10"
print(f"Testing FIRMS URL: {url.replace(map_key, 'REDACTED')}")

resp = requests.get(url, timeout=20)
print("FIRMS Status:", resp.status_code)
lines = resp.text.strip().split("\n")
print(f"Returned {len(lines)} lines")
for line in lines[:5]:
    print("  ", line)
