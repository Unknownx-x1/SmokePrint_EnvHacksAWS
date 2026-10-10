import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Sensor 35 metadata
s_resp = requests.get("https://api.openaq.org/v3/sensors/35", headers=headers).json()
print("Sensor 35 info:", s_resp.get("results", [{}])[0].get("datetimeFirst"), s_resp.get("results", [{}])[0].get("datetimeLast"))

# Query without datetime filter with limit 10
r_resp = requests.get("https://api.openaq.org/v3/sensors/35/hours?limit=10", headers=headers).json()
results = r_resp.get("results", [])
print(f"Results without filter ({len(results)}):")
for r in results[:3]:
    print(r.get("period"))
