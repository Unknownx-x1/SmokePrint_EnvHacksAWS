import json
from datetime import datetime

with open("data/active_stations.json", "r") as f:
    stations = json.load(f)

print(f"Total active stations saved: {len(stations)}")

# Check start and end dates
start_target = datetime.fromisoformat("2026-04-01T00:00:00")
end_target = datetime.fromisoformat("2026-10-01T00:00:00")

qualifying = []
for s in stations:
    first_str = s.get("first_utc")
    last_str = s.get("last_utc")
    if first_str and last_str:
        # e.g. 2016-02-05T14:55:00Z -> parse
        t_first = datetime.fromisoformat(first_str.replace("Z", "+00:00")).replace(tzinfo=None)
        t_last = datetime.fromisoformat(last_str.replace("Z", "+00:00")).replace(tzinfo=None)
        
        has_pm25 = "pm25" in s["parameters"]
        has_pm10 = "pm10" in s["parameters"]
        has_no2 = "no2" in s["parameters"]
        has_co = "co" in s["parameters"]
        
        spans_window = (t_first <= start_target) and (t_last >= end_target)
        if spans_window and has_pm25:
            qualifying.append({
                "id": s["id"],
                "name": s["name"],
                "has_all_4": has_pm25 and has_pm10 and has_no2 and has_co,
                "params": s["parameters"],
                "first": first_str,
                "last": last_str
            })

print(f"Stations whose operational span includes 2026-04-01 to 2026-10-01 with PM2.5: {len(qualifying)}")
all_4 = [q for q in qualifying if q["has_all_4"]]
print(f"Stations with all 4 (PM2.5, PM10, NO2, CO): {len(all_4)}")
for q in all_4[:10]:
    print(f"  [{q['id']}] {q['name']}")
