import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

# Sensor 12234787 (R K Puram PM2.5)
params = {
    "datetime_from": "2026-04-01T00:00:00Z",
    "datetime_to": "2026-10-01T00:00:00Z",
    "limit": 1000,
    "page": 1
}

resp1 = requests.get("https://api.openaq.org/v3/sensors/12234787/hours", headers=headers, params=params).json()
print("Page 1 results count:", len(resp1.get("results", [])))
if resp1.get("results"):
    print("Page 1 start:", resp1["results"][0]["period"]["datetimeFrom"]["utc"])
    print("Page 1 end  :", resp1["results"][-1]["period"]["datetimeFrom"]["utc"])

params["page"] = 2
resp2 = requests.get("https://api.openaq.org/v3/sensors/12234787/hours", headers=headers, params=params).json()
print("Page 2 results count:", len(resp2.get("results", [])))
if resp2.get("results"):
    print("Page 2 start:", resp2["results"][0]["period"]["datetimeFrom"]["utc"])
    print("Page 2 end  :", resp2["results"][-1]["period"]["datetimeFrom"]["utc"])
