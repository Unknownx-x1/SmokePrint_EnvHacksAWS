import os
import glob
import json
import pandas as pd
import numpy as np
import zoneinfo

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# Load FIRMS fires
firms_data = []
if os.path.exists("data/firms_fires_6m.json"):
    with open("data/firms_fires_6m.json") as f:
        firms_data = json.load(f).get("detections", [])
print(f"Loaded {len(firms_data)} FIRMS detections.")

# Load clean 12m stations
files = glob.glob("data/stations_12m/station_*_12m.json")
stations = {}
st_meta = {}

for f in files:
    d = json.load(open(f))
    sid = d["station_id"]
    st_meta[sid] = {"name": d["name"], "coords": d["coordinates"]}
    
    p25 = pd.Series(d.get("data", {}).get("pm25", {}))
    p10 = pd.Series(d.get("data", {}).get("pm10", {}))
    no2 = pd.Series(d.get("data", {}).get("no2", {}))
    co  = pd.Series(d.get("data", {}).get("co", {}))
    
    df = pd.DataFrame({"pm25": p25, "pm10": p10, "no2": no2, "co": co})
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index().resample("1h").mean()
    stations[sid] = df

# Regional median across winter
df_p25_all = pd.DataFrame({sid: df["pm25"] for sid, df in stations.items() if "pm25" in df})
df_p10_all = pd.DataFrame({sid: df["pm10"] for sid, df in stations.items() if "pm10" in df})
df_no2_all = pd.DataFrame({sid: df["no2"] for sid, df in stations.items() if "no2" in df})

reg_med25 = df_p25_all.median(axis=1)
reg_med10 = df_p10_all.median(axis=1)
reg_med_no2 = df_no2_all.median(axis=1)

# Winter slice: Nov 1, 2025 to Feb 28, 2026
winter_start = pd.Timestamp("2025-11-01 00:00:00+00:00")
winter_end   = pd.Timestamp("2026-02-28 23:59:59+00:00")

candidate_events = []

for sid, df in stations.items():
    if "pm25" not in df or "pm10" not in df:
        continue
    sub = df.loc[winter_start:winter_end]
    sub_med25 = reg_med25.loc[winter_start:winter_end]
    
    excess25 = sub["pm25"] - sub_med25
    
    # Require localized excess: excess > 100 ug/m3, while regional median is moderate/typical for winter (120 - 250 ug/m3)
    # Require PM2.5 <= PM10 (valid physics), ratio > 0.40
    # Check persistence >= 3 hours
    run = []
    for ts, exc in excess25.items():
        val25 = sub.loc[ts, "pm25"]
        val10 = sub.loc[ts, "pm10"]
        val_no2 = sub.loc[ts, "no2"] if "no2" in sub.columns else np.nan
        m25 = sub_med25.loc[ts]
        
        valid_physics = pd.notna(val25) and pd.notna(val10) and (val25 <= val10 * 1.05 + 5.0) and (val25 >= 180)
        is_spike = valid_physics and (exc >= 80) and (m25 < 280)
        
        if is_spike:
            run.append(ts)
        else:
            if len(run) >= 3:
                mid_t = run[len(run)//2]
                candidate_events.append({
                    "sid": sid,
                    "name": st_meta[sid]["name"],
                    "coords": st_meta[sid]["coords"],
                    "start": run[0],
                    "end": run[-1],
                    "peak_ts": mid_t,
                    "duration_h": len(run),
                    "p25": round(float(sub.loc[mid_t, "pm25"]), 1),
                    "p10": round(float(sub.loc[mid_t, "pm10"]), 1),
                    "no2": round(float(sub.loc[mid_t, "no2"]), 1) if pd.notna(sub.loc[mid_t, "no2"]) else None,
                    "ratio": round(float(sub.loc[mid_t, "pm25"] / sub.loc[mid_t, "pm10"]), 2),
                    "excess25": round(float(excess25.loc[mid_t]), 1),
                    "reg_med25": round(float(sub_med25.loc[mid_t]), 1)
                })
            run = []
    if len(run) >= 3:
        mid_t = run[len(run)//2]
        candidate_events.append({
            "sid": sid,
            "name": st_meta[sid]["name"],
            "coords": st_meta[sid]["coords"],
            "start": run[0],
            "end": run[-1],
            "peak_ts": mid_t,
            "duration_h": len(run),
            "p25": round(float(sub.loc[mid_t, "pm25"]), 1),
            "p10": round(float(sub.loc[mid_t, "pm10"]), 1),
            "no2": round(float(sub.loc[mid_t, "no2"]), 1) if pd.notna(sub.loc[mid_t, "no2"]) else None,
            "ratio": round(float(sub.loc[mid_t, "pm25"] / sub.loc[mid_t, "pm10"]), 2),
            "excess25": round(float(excess25.loc[mid_t]), 1),
            "reg_med25": round(float(sub_med25.loc[mid_t]), 1)
        })

df_ev = pd.DataFrame(candidate_events)
print(f"Total persistent winter spike events found: {len(df_ev)}")

# Let's inspect events that have NO2 co-movement
if not df_ev.empty:
    with_no2 = df_ev[df_ev["no2"].notna() & (df_ev["no2"] > 40)]
    print(f"Events with elevated NO2 (>40 ug/m3): {len(with_no2)}")
    print(with_no2[["sid", "name", "peak_ts", "p25", "p10", "no2", "ratio", "excess25", "reg_med25"]].head(10).to_string())
