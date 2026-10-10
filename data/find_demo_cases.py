import os
import glob
import json
import pandas as pd
import numpy as np
import zoneinfo

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

def find_cases():
    files = glob.glob("data/stations_qc/station_*_qc.json")
    print(f"Loading {len(files)} clean QC stations...")
    
    st_meta = {}
    p25_dict = {}
    p10_dict = {}
    no2_dict = {}
    co_dict  = {}
    
    for f in files:
        with open(f) as fp:
            d = json.load(fp)
        sid = d["station_id"]
        st_meta[sid] = {
            "name": d["name"],
            "coords": d["coordinates"]
        }
        rec = pd.DataFrame(d["records"])
        if "pm25" in rec.columns and rec["pm25"].count() > 1000:
            rec["ts"] = pd.to_datetime(rec["timestamp_utc"])
            rec = rec.set_index("ts")
            p25_dict[sid] = rec["pm25"]
            if "pm10" in rec.columns:
                p10_dict[sid] = rec["pm10"]
            if "no2" in rec.columns:
                no2_dict[sid] = rec["no2"]
            if "co" in rec.columns:
                co_dict[sid] = rec["co"]

    df25 = pd.DataFrame(p25_dict).resample("1h").mean()
    df10 = pd.DataFrame(p10_dict).resample("1h").mean()
    df_no2 = pd.DataFrame(no2_dict).resample("1h").mean()
    df_co  = pd.DataFrame(co_dict).resample("1h").mean()
    
    # Regional baseline
    regional_med25 = df25.median(axis=1)
    regional_med10 = df10.median(axis=1)
    
    # Excess
    excess25 = df25.apply(lambda col: col - regional_med25, axis=0)
    excess10 = df10.apply(lambda col: col - regional_med10, axis=0)
    
    print("\nScanning for Candidate Demo Cases...")
    
    # Helper to check persistence (>= 3 consecutive hours)
    def check_persistent(station_id, series_excess, min_val=80, min_len=3):
        col = series_excess[station_id].dropna()
        runs = []
        cur_run = []
        for ts, val in col.items():
            if val >= min_val:
                cur_run.append(ts)
            else:
                if len(cur_run) >= min_len:
                    runs.append(cur_run)
                cur_run = []
        if len(cur_run) >= min_len:
            runs.append(cur_run)
        return runs

    # 1. Search for DUST-LIKE Case:
    # High PM10 excess, moderate PM2.5, Ratio PM2.5/PM10 between 0.15 and 0.35, persists >= 3h
    dust_candidates = []
    for sid in df10.columns:
        if sid not in df25.columns:
            continue
        p10_runs = check_persistent(sid, excess10, min_val=150, min_len=3)
        for run in p10_runs:
            t_mid = run[len(run)//2]
            p25_val = df25.loc[t_mid, sid]
            p10_val = df10.loc[t_mid, sid]
            med25 = regional_med25.loc[t_mid]
            med10 = regional_med10.loc[t_mid]
            if pd.notna(p25_val) and pd.notna(p10_val) and p10_val > 0:
                ratio = p25_val / p10_val
                if 0.12 <= ratio <= 0.35 and med10 < 250:
                    dust_candidates.append({
                        "sid": sid,
                        "name": st_meta[sid]["name"],
                        "run_start": run[0],
                        "run_end": run[-1],
                        "duration_h": len(run),
                        "peak_ts": t_mid,
                        "p25": round(p25_val, 1),
                        "p10": round(p10_val, 1),
                        "ratio": round(ratio, 2),
                        "excess10": round(excess10.loc[t_mid, sid], 1),
                        "excess25": round(excess25.loc[t_mid, sid], 1),
                        "regional_med10": round(med10, 1)
                    })

    # 2. Search for COMBUSTION-LIKE Case:
    # High PM2.5 excess, Ratio PM2.5/PM10 between 0.55 and 0.85, persists >= 3h, moderate regional background
    combustion_candidates = []
    for sid in df25.columns:
        if sid not in df10.columns:
            continue
        p25_runs = check_persistent(sid, excess25, min_val=90, min_len=3)
        for run in p25_runs:
            t_mid = run[len(run)//2]
            p25_val = df25.loc[t_mid, sid]
            p10_val = df10.loc[t_mid, sid]
            med25 = regional_med25.loc[t_mid]
            no2_val = df_no2.loc[t_mid, sid] if sid in df_no2.columns and t_mid in df_no2.index else np.nan
            if pd.notna(p25_val) and pd.notna(p10_val) and p10_val > 0:
                ratio = p25_val / p10_val
                if 0.52 <= ratio <= 0.88 and med25 < 120 and p25_val <= p10_val:
                    combustion_candidates.append({
                        "sid": sid,
                        "name": st_meta[sid]["name"],
                        "run_start": run[0],
                        "run_end": run[-1],
                        "duration_h": len(run),
                        "peak_ts": t_mid,
                        "p25": round(p25_val, 1),
                        "p10": round(p10_val, 1),
                        "no2": round(no2_val, 1) if pd.notna(no2_val) else None,
                        "ratio": round(ratio, 2),
                        "excess25": round(excess25.loc[t_mid, sid], 1),
                        "regional_med25": round(med25, 1)
                    })

    # 3. Search for REGIONAL SMOG / INVERSION Event (Should be rejected as Regional):
    # Regional median PM2.5 is very high (>= 220 ug/m3), most stations elevated, local excess is low
    regional_events = []
    high_reg = regional_med25[regional_med25 >= 200]
    for ts, r_val in high_reg.items():
        reporting = df25.loc[ts].dropna()
        if len(reporting) >= 20:
            elevated_pct = (reporting >= 180).sum() / len(reporting)
            if elevated_pct >= 0.85: # 85%+ of stations elevated together
                regional_events.append({
                    "ts": ts,
                    "regional_med25": round(r_val, 1),
                    "reporting_stations": len(reporting),
                    "elevated_pct": round(elevated_pct * 100, 1),
                    "mean_val": round(reporting.mean(), 1)
                })

    df_dust = pd.DataFrame(dust_candidates)
    df_comb = pd.DataFrame(combustion_candidates)
    df_reg  = pd.DataFrame(regional_events)
    
    print(f"Dust candidates found       : {len(df_dust)}")
    print(f"Combustion candidates found : {len(df_comb)}")
    print(f"Regional events found       : {len(df_reg)}")

    # Pick top quality representative cases
    selected = {}
    if not df_dust.empty:
        selected["dust"] = df_dust.sort_values(by="excess10", ascending=False).iloc[0].to_dict()
    if not df_comb.empty:
        # Pick one with NO2 present
        with_no2 = df_comb[df_comb["no2"].notna()]
        if not with_no2.empty:
            selected["combustion_1"] = with_no2.sort_values(by="excess25", ascending=False).iloc[0].to_dict()
            if len(with_no2) > 1:
                selected["combustion_2"] = with_no2.sort_values(by="excess25", ascending=False).iloc[1].to_dict()
        else:
            selected["combustion_1"] = df_comb.sort_values(by="excess25", ascending=False).iloc[0].to_dict()
            
    if not df_reg.empty:
        selected["regional"] = df_reg.sort_values(by="regional_med25", ascending=False).iloc[0].to_dict()

    # Analyze neighbouring stations for each selected case
    for case_type, c in selected.items():
        if case_type == "regional":
            continue
        sid = c["sid"]
        ts = c["peak_ts"]
        # Distance to other stations
        c_lat = st_meta[sid]["coords"]["latitude"]
        c_lon = st_meta[sid]["coords"]["longitude"]
        
        station_diffs = []
        for other_sid, other_meta in st_meta.items():
            if other_sid == sid or other_sid not in df25.columns:
                continue
            o_lat = other_meta["coords"]["latitude"]
            o_lon = other_meta["coords"]["longitude"]
            dist_km = 111.0 * np.sqrt((c_lat - o_lat)**2 + ((c_lon - o_lon) * np.cos(np.radians(c_lat)))**2)
            val = df25.loc[ts, other_sid] if ts in df25.index else np.nan
            exc = excess25.loc[ts, other_sid] if ts in excess25.index else np.nan
            if pd.notna(val) and dist_km <= 25:
                station_diffs.append({
                    "id": other_sid,
                    "name": other_meta["name"],
                    "dist_km": round(dist_km, 1),
                    "pm25": round(val, 1),
                    "excess25": round(exc, 1)
                })
        c["neighbours"] = sorted(station_diffs, key=lambda x: x["dist_km"])[:6]

    with open("data/demo_candidate_cases.json", "w") as fp:
        json.dump(selected, fp, indent=2, default=str)
        
    print("\nSELECTED CANDIDATE DEMO CASES:")
    for k, v in selected.items():
        print(f"\n--- CASE: {k.upper()} ---")
        for prop, val in v.items():
            if prop != "neighbours":
                print(f"  {prop}: {val}")
        if "neighbours" in v:
            print("  Neighbouring Station Responses:")
            for n in v["neighbours"][:4]:
                print(f"    - {n['name'][:25]} ({n['dist_km']} km away): PM2.5={n['pm25']} ug/m3 (Excess: {n['excess25']})")

if __name__ == "__main__":
    find_cases()
