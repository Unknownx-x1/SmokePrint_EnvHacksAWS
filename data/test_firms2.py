import os
import requests
from dotenv import load_dotenv

load_dotenv()
map_key = os.getenv("FIRMS_MAP_KEY")
bbox_str = "76.7,28.2,77.6,28.95"

# Test 1: Day range 5 (most recent 5 days)
url1 = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{bbox_str}/5"
resp1 = requests.get(url1, timeout=15)
print("FIRMS 5-day NRT status:", resp1.status_code)
lines1 = resp1.text.strip().split("\n")
print(f"Lines returned: {len(lines1)}")
if len(lines1) > 1:
    print("Header:", lines1[0])
    print("Sample:", lines1[1])

# Test 2: Specific historical date (e.g. 2026-05-15 or 2026-09-15)
url2 = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{bbox_str}/5/2026-09-15"
resp2 = requests.get(url2, timeout=15)
print("\nFIRMS specific date status:", resp2.status_code)
lines2 = resp2.text.strip().split("\n")
print(f"Lines returned: {len(lines2)}")
if len(lines2) > 1:
    print("Header:", lines2[0])
    for l in lines2[1:4]:
        print("Sample:", l)
