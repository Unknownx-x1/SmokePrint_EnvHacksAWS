import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Inspect DTU location (id: 13)
resp = requests.get("https://api.openaq.org/v3/locations/13", headers=headers)
loc = resp.json().get("results", [{}])[0]
print("Location 13 sensors:")
for s in loc.get("sensors", []):
    print(" ", s.get("id"), s.get("name"), s.get("parameter", {}).get("name"))

# Check hours endpoint for first sensor
sensor_id = loc.get("sensors", [])[0].get("id")
print(f"\nTesting sensor {sensor_id} hours:")
h_resp = requests.get(f"https://api.openaq.org/v3/sensors/{sensor_id}/hours", headers=headers, params={"limit": 5})
print("Hours status:", h_resp.status_code)
if h_resp.status_code == 200:
    h_data = h_resp.json()
    print("Found items:", len(h_data.get("results", [])))
    if h_data.get("results"):
        print("Sample hour:", h_data.get("results")[0])
else:
    print(h_resp.text[:300])
