import os
import glob
import json
import pandas as pd
import numpy as np
from qc import run_qc_on_station

WINTER_START = pd.Timestamp("2025-10-01 00:00:00+00:00")
WINTER_END   = pd.Timestamp("2026-02-28 23:59:59+00:00")
WINTER_EXPECTED_HOURS = 151 * 24 # 3,624 hours

FULL_START = pd.Timestamp("2025-10-01 00:00:00+00:00")
FULL_END   = pd.Timestamp("2026-09-30 23:59:59+00:00")
FULL_EXPECTED_HOURS = 365 * 24 # 8,760 hours

def evaluate():
    files = glob.glob("data/stations_12m/station_*_12m.json")
    print(f"Loaded {len(files)} 12-month station files for QC coverage evaluation...")
    
    winter_results = []
    full_results = []
    
    for f in files:
        with open(f) as fp:
            st = json.load(fp)
            
        clean_st, stats = run_qc_on_station(st)
        if not clean_st:
            continue
            
        records = clean_st["records"]
        df = pd.DataFrame(records)
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        df = df.set_index("timestamp_utc")
        
        # 1. Evaluate Winter Window
        df_winter = df.loc[WINTER_START:WINTER_END]
        w_p25 = df_winter["pm25"].dropna().count() if "pm25" in df_winter.columns else 0
        w_p10 = df_winter["pm10"].dropna().count() if "pm10" in df_winter.columns else 0
        w_no2 = df_winter["no2"].dropna().count() if "no2" in df_winter.columns else 0
        w_co  = df_winter["co"].dropna().count() if "co" in df_winter.columns else 0
        
        w_cov = {
            "pm25": round(100.0 * w_p25 / WINTER_EXPECTED_HOURS, 2),
            "pm10": round(100.0 * w_p10 / WINTER_EXPECTED_HOURS, 2),
            "no2":  round(100.0 * w_no2 / WINTER_EXPECTED_HOURS, 2),
            "co":   round(100.0 * w_co  / WINTER_EXPECTED_HOURS, 2)
        }
        winter_results.append({
            "station_id": st["station_id"],
            "name": st["name"],
            "counts": {"pm25": int(w_p25), "pm10": int(w_p10), "no2": int(w_no2), "co": int(w_co)},
            "coverage": w_cov
        })
        
        # 2. Evaluate Full 12-Month Window
        df_full = df.loc[FULL_START:FULL_END]
        f_p25 = df_full["pm25"].dropna().count() if "pm25" in df_full.columns else 0
        f_p10 = df_full["pm10"].dropna().count() if "pm10" in df_full.columns else 0
        f_no2 = df_full["no2"].dropna().count() if "no2" in df_full.columns else 0
        f_co  = df_full["co"].dropna().count() if "co" in df_full.columns else 0
        
        f_cov = {
            "pm25": round(100.0 * f_p25 / FULL_EXPECTED_HOURS, 2),
            "pm10": round(100.0 * f_p10 / FULL_EXPECTED_HOURS, 2),
            "no2":  round(100.0 * f_no2 / FULL_EXPECTED_HOURS, 2),
            "co":   round(100.0 * f_co  / FULL_EXPECTED_HOURS, 2)
        }
        full_results.append({
            "station_id": st["station_id"],
            "name": st["name"],
            "counts": {"pm25": int(f_p25), "pm10": int(f_p10), "no2": int(f_no2), "co": int(f_co)},
            "coverage": f_cov
        })

    # Summary calculations
    def summarize(res_list, exp_hours, label):
        n = len(res_list)
        p25_80 = [r for r in res_list if r["coverage"]["pm25"] >= 80.0]
        both_80 = [r for r in res_list if r["coverage"]["pm25"] >= 80.0 and r["coverage"]["pm10"] >= 80.0]
        all4_80 = [r for r in res_list if all(r["coverage"][p] >= 80.0 for p in ["pm25", "pm10", "no2", "co"])]
        
        print("\n" + "="*70)
        print(f"COVERAGE SUMMARY (QC APPLIED): {label.upper()}")
        print(f"Expected Hours: {exp_hours:,}")
        print("="*70)
        print(f"Total Stations Evaluated             : {n}")
        print(f"Stations with PM2.5 >= 80%           : {len(p25_80):>2} / {n} ({round(100*len(p25_80)/n, 1)}%)")
        print(f"Stations with PM2.5 & PM10 >= 80%    : {len(both_80):>2} / {n} ({round(100*len(both_80)/n, 1)}%)")
        print(f"Stations with all 4 pollutants >= 80%: {len(all4_80):>2} / {n} ({round(100*len(all4_80)/n, 1)}%)")
        print("="*70)
        return {
            "window": label,
            "expected_hours": exp_hours,
            "stations_evaluated": n,
            "stations_pm25_ge_80": len(p25_80),
            "stations_both_pm_ge_80": len(both_80),
            "stations_all_4_ge_80": len(all4_80),
            "details": res_list
        }

    sum_winter = summarize(winter_results, WINTER_EXPECTED_HOURS, "Winter Window (Oct 2025 - Feb 2026)")
    sum_full   = summarize(full_results, FULL_EXPECTED_HOURS, "Full 12 Months (Oct 2025 - Sep 2026)")
    
    with open("data/coverage_12m_qc_summary.json", "w") as fp:
        json.dump({"winter": sum_winter, "full_12m": sum_full}, fp, indent=2)

if __name__ == "__main__":
    evaluate()
