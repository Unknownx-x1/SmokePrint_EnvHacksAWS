import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {"X-API-Key": os.getenv("OPENAQ_API_KEY")}

loc_resp = requests.get("https://api.openaq.org/v3/locations/17", headers=headers).json()
for s in loc_resp["results"][0]["sensors"]:
    print(f"ID: {s['id']:<8} Parameter: {s.get('parameter', {}).get('name'):<10} First: {s.get('datetimeFirst', {}).get('utc') if s.get('datetimeFirst') else 'None'} Last: {s.get('datetimeLast', {}).get('utc') if s.get('datetimeLast') else 'None'}")
