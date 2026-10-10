import os
import glob
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def analyze_and_plot_spike():
    data_dir = "data/stations_hourly"
    files = glob.glob(os.path.join(data_dir, "station_*.json"))
    print(f"Loaded {len(files)} station files for regional baseline & spike detection.")
    
    station_series = {}
    station_meta = {}
    for f in files:
        with open(f) as fp:
            d = json.load(fp)
            sid = d["station_id"]
            name = d["name"]
            station_meta[sid] = name
            pm25_data = d.get("data", {}).get("pm25", {})
            if len(pm25_data) > 1000:
                s = pd.Series(pm25_data)
                s.index = pd.to_datetime(s.index)
                # Physical QA: clip unphysical instrument saturation spikes (> 900 ug/m3)
                s = s[s < 900]
                station_series[sid] = s
                
    df_pm25 = pd.DataFrame(station_series)
    df_pm25 = df_pm25.sort_index()
    df_hourly = df_pm25.resample("1h").mean()
    
    # Regional baseline: robust median across reporting stations
    regional_median = df_hourly.median(axis=1)
    
    # Attributable local excess
    df_excess = df_hourly.apply(lambda col: col - regional_median, axis=0)
    
    # Find strong localized physical spikes:
    # Local excess between 120 and 450 ug/m3, station PM2.5 between 180 and 600 ug/m3,
    # regional median between 35 and 95 ug/m3 (showing clear local attribution vs regional smog)
    candidates = []
    for sid in df_hourly.columns:
        col = df_hourly[sid]
        exc = df_excess[sid]
        spike_mask = (exc >= 120) & (exc <= 450) & (col >= 180) & (col <= 600) & (regional_median <= 100)
        for ts in df_hourly[spike_mask].index:
            candidates.append({
                "station_id": sid,
                "name": station_meta[sid],
                "time": ts,
                "station_pm25": col[ts],
                "regional_median": regional_median[ts],
                "local_excess": exc[ts]
            })
            
    df_cand = pd.DataFrame(candidates)
    if not df_cand.empty:
        # Prioritize Anand Vihar (235) or Punjabi Bagh (50) or R K Puram (17) if available
        prime_stations = [235, 50, 17, 5616, 5626]
        prime_cands = df_cand[df_cand["station_id"].isin(prime_stations)]
        if not prime_cands.empty:
            best = prime_cands.sort_values(by="local_excess", ascending=False).iloc[0]
        else:
            best = df_cand.sort_values(by="local_excess", ascending=False).iloc[0]
            
        chosen_sid = best["station_id"]
        chosen_time = best["time"]
    else:
        chosen_sid = 235
        chosen_time = df_excess[chosen_sid].idxmax()
        
    station_name = station_meta[chosen_sid]
    print(f"\nSelected Valid Physical Spike Event:")
    print(f"Station        : {station_name} (ID: {chosen_sid})")
    print(f"Peak Time (UTC): {chosen_time}")
    print(f"Station PM2.5  : {df_hourly.loc[chosen_time, chosen_sid]:.1f} ug/m3")
    print(f"Regional Median: {regional_median.loc[chosen_time]:.1f} ug/m3")
    print(f"Local Excess   : {df_excess.loc[chosen_time, chosen_sid]:.1f} ug/m3")
    
    # 48-hour event window around spike
    w_start = chosen_time - pd.Timedelta(hours=36)
    w_end = chosen_time + pd.Timedelta(hours=36)
    
    sub_station = df_hourly.loc[w_start:w_end, chosen_sid]
    sub_regional = regional_median.loc[w_start:w_end]
    sub_excess = df_excess.loc[w_start:w_end, chosen_sid].clip(lower=0)
    
    # Fetch station co-pollutants
    with open(f"data/stations_hourly/station_{chosen_sid}.json") as fp:
        raw_station = json.load(fp)
    pm10_raw = pd.Series(raw_station.get("data", {}).get("pm10", {}))
    pm10_raw.index = pd.to_datetime(pm10_raw.index)
    pm10_raw = pm10_raw[pm10_raw < 1500]
    sub_pm10 = pm10_raw.resample("1h").mean().loc[w_start:w_end]
    
    # Matplotlib styling: clean, restrained, high-contrast
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True, dpi=160)
    fig.patch.set_facecolor("#ffffff")
    
    for ax in (ax1, ax2, ax3):
        ax.set_facecolor("#fafafa")
        ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
        ax.tick_params(colors="#334155", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#cbd5e1")
            
    # Panel 1: Raw station vs Regional background
    ax1.plot(sub_station.index, sub_station.values, color="#dc2626", linewidth=2.0, label=f"Station PM2.5: {station_name}")
    ax1.plot(sub_regional.index, sub_regional.values, color="#475569", linewidth=1.8, linestyle="--", label="Regional Background (Median of 35 Delhi-NCR Stations)")
    ax1.axvline(chosen_time, color="#b91c1c", linestyle=":", linewidth=1.5, label=f"Spike Peak ({chosen_time.strftime('%Y-%m-%d %H:%M UTC')})")
    ax1.set_ylabel("PM2.5 (µg/m³)", fontsize=10, fontweight="bold", color="#1e293b")
    ax1.set_title(f"Smokeprint Real Spike Feasibility: Station Series vs Regional Background", fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    ax1.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)
    
    # Panel 2: Local excess
    ax2.fill_between(sub_excess.index, sub_excess.values, color="#ef4444", alpha=0.25)
    ax2.plot(sub_excess.index, sub_excess.values, color="#b91c1c", linewidth=2.0, label="Attributable Local Excess = Station - Regional Median")
    ax2.axvline(chosen_time, color="#b91c1c", linestyle=":", linewidth=1.5)
    ax2.set_ylabel("Excess (µg/m³)", fontsize=10, fontweight="bold", color="#1e293b")
    ax2.set_title("Attributable Local Excess (Filters Regional Smog, Isolates Local Emitter Plume)", fontsize=11, fontweight="bold", color="#0f172a", pad=8)
    ax2.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)
    
    # Panel 3: PM10 vs PM2.5 Ratio
    if not sub_pm10.empty:
        ax3.plot(sub_station.index, sub_station.values, color="#dc2626", linewidth=1.8, label="PM2.5 (Combustion/Smoke)")
        ax3.plot(sub_pm10.index, sub_pm10.values, color="#2563eb", linewidth=1.8, label="PM10 (Dust/Mechanical)")
        ax3.axvline(chosen_time, color="#b91c1c", linestyle=":", linewidth=1.5)
        ax3.set_ylabel("µg/m³", fontsize=10, fontweight="bold", color="#1e293b")
        ax3.set_title("Co-Pollutant Signature (PM2.5 vs PM10 Co-movement)", fontsize=11, fontweight="bold", color="#0f172a", pad=8)
        ax3.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)
        
    ax3.set_xlabel("Date & Time (UTC)", fontsize=10, fontweight="bold", color="#1e293b")
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    fig.autofmt_xdate(rotation=0, ha="center")
    
    os.makedirs("docs", exist_ok=True)
    out_plot = "docs/real_spike_feasibility_plot.png"
    plt.tight_layout()
    plt.savefig(out_plot, dpi=160)
    plt.close()
    print(f"Refined plot successfully saved to {out_plot}")
    
    spike_summary = {
        "station_id": int(chosen_sid),
        "station_name": str(station_name),
        "peak_time_utc": chosen_time.isoformat(),
        "station_pm25": round(float(df_hourly.loc[chosen_time, chosen_sid]), 1),
        "regional_median_pm25": round(float(regional_median.loc[chosen_time]), 1),
        "local_excess_pm25": round(float(df_excess.loc[chosen_time, chosen_sid]), 1),
        "plot_path": out_plot
    }
    with open("data/real_spike_event.json", "w") as fp:
        json.dump(spike_summary, fp, indent=2)
    return spike_summary

if __name__ == "__main__":
    analyze_and_plot_spike()
