import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Let's inspect sensor 12234787 details
s_resp = requests.get("https://api.openaq.org/v3/sensors/12234787", headers=headers).json()
print("Sensor 12234787 info:", s_resp.get("results", [{}])[0].get("datetimeFirst"), s_resp.get("results", [{}])[0].get("datetimeLast"))

# Query recent hours
h_resp = requests.get("https://api.openaq.org/v3/sensors/12234787/hours?limit=5", headers=headers).json()
results = h_resp.get("results", [])
print(f"Hours count: {len(results)}")
for r in results:
    print("  ", r.get("period", {}).get("datetimeFrom"), "value:", r.get("value"))
