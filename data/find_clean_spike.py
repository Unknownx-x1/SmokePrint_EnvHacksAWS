import glob
import json
import pandas as pd

files = glob.glob("data/stations_hourly/station_*.json")
candidates = []
for f in files:
    d = json.load(open(f))
    sid, name = d["station_id"], d["name"]
    p25 = pd.Series(d.get("data", {}).get("pm25", {}))
    p10 = pd.Series(d.get("data", {}).get("pm10", {}))
    no2 = pd.Series(d.get("data", {}).get("no2", {}))
    if len(p25) > 1000 and len(p10) > 1000:
        p25.index = pd.to_datetime(p25.index)
        p10.index = pd.to_datetime(p10.index)
        p25 = p25[p25 < 800]
        p10 = p10[p10 < 1200]
        df = pd.DataFrame({"pm25": p25, "pm10": p10}).dropna()
        spikes = df[(df["pm25"] > 160) & (df["pm10"] > 220)]
        if not spikes.empty:
            for ts, row in spikes.iterrows():
                candidates.append({
                    "station_id": sid,
                    "name": name,
                    "time": ts,
                    "pm25": row["pm25"],
                    "pm10": row["pm10"]
                })

df_c = pd.DataFrame(candidates)
print(f"Total concurrent high spike timestamps: {len(df_c)}")
if not df_c.empty:
    print(df_c.head(10))
