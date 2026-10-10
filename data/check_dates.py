import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

resp = requests.get("https://api.openaq.org/v3/locations", headers=headers, params={
    "bbox": "76.70,28.20,77.60,28.95",
    "limit": 10
})
results = resp.json().get("results", [])
for r in results:
    print(r.get("id"), r.get("name"))
    print("  first:", r.get("datetimeFirst"))
    print("  last :", r.get("datetimeLast"))
