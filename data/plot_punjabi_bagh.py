import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def plot_punjabi_bagh_spike():
    chosen_sid = 50
    chosen_time = pd.Timestamp("2026-04-28 05:00:00+00:00")
    
    # Load Punjabi Bagh data
    with open(f"data/stations_hourly/station_{chosen_sid}.json") as f:
        st_data = json.load(f)
    station_name = st_data["name"]
    
    # Load regional median across all 35 stations
    import glob
    files = glob.glob("data/stations_hourly/station_*.json")
    all_pm25 = {}
    for fpath in files:
        with open(fpath) as fp:
            d = json.load(fp)
            s = pd.Series(d.get("data", {}).get("pm25", {}))
            if len(s) > 1000:
                s.index = pd.to_datetime(s.index)
                s = s[s < 1000]
                all_pm25[d["station_id"]] = s
    df_all = pd.DataFrame(all_pm25).resample("1h").mean()
    regional_median = df_all.median(axis=1)
    
    # Window: 36 hours before and after
    w_start = chosen_time - pd.Timedelta(hours=30)
    w_end = chosen_time + pd.Timedelta(hours=30)
    
    p25 = pd.Series(st_data["data"]["pm25"])
    p25.index = pd.to_datetime(p25.index)
    p25 = p25.resample("1h").mean().loc[w_start:w_end]
    
    p10 = pd.Series(st_data["data"]["pm10"])
    p10.index = pd.to_datetime(p10.index)
    p10 = p10.resample("1h").mean().loc[w_start:w_end]
    
    med = regional_median.loc[w_start:w_end]
    excess = (p25 - med).clip(lower=0)
    
    # Load wind data for same window
    wind_speed = None
    wind_dir = None
    if os.path.exists("data/wind_hourly_6m.json"):
        with open("data/wind_hourly_6m.json") as wf:
            wdata = json.load(wf)
            wdf = pd.DataFrame(wdata["records"])
            wdf["time"] = pd.to_datetime(wdf["time"], utc=True)
            wdf = wdf.set_index("time")
            sub_wind = wdf.loc[w_start:w_end]
            wind_speed = sub_wind["wind_speed_ms"]
            wind_dir = sub_wind["wind_direction_deg"]
            
    # Matplotlib Plot
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True, dpi=160)
    fig.patch.set_facecolor("#ffffff")
    
    for ax in (ax1, ax2, ax3):
        ax.set_facecolor("#fafafa")
        ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
        ax.tick_params(colors="#334155", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#cbd5e1")
            
    # Panel 1: Raw Station PM2.5 vs Regional Background
    ax1.plot(p25.index, p25.values, color="#dc2626", linewidth=2.2, label=f"Station PM2.5: {station_name}")
    ax1.plot(med.index, med.values, color="#475569", linewidth=1.8, linestyle="--", label="Regional Background (Median of 35 Delhi-NCR Stations)")
    ax1.axvline(chosen_time, color="#b91c1c", linestyle=":", linewidth=1.6, label=f"Spike Peak ({chosen_time.strftime('%b %d, %H:%M UTC')})")
    ax1.scatter([chosen_time], [p25.loc[chosen_time]], color="#dc2626", s=50, zorder=5)
    ax1.annotate(f"Station: {p25.loc[chosen_time]:.0f} µg/m³\nReg. Median: {med.loc[chosen_time]:.0f} µg/m³",
                 xy=(chosen_time, p25.loc[chosen_time]), xytext=(chosen_time + pd.Timedelta(hours=3), p25.loc[chosen_time] - 70),
                 arrowprops=dict(facecolor="#b91c1c", shrink=0.08, width=1, headwidth=6),
                 fontsize=9, fontweight="bold", color="#991b1b",
                 bbox=dict(boxstyle="round,pad=0.3", fc="#fef2f2", ec="#fca5a5"))
    ax1.set_ylabel("PM2.5 (µg/m³)", fontsize=10, fontweight="bold", color="#1e293b")
    ax1.set_title(f"Smokeprint Real Spike Feasibility: Station Series vs Regional Background", fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    ax1.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)
    
    # Panel 2: Local Attributable Excess
    ax2.fill_between(excess.index, excess.values, color="#ef4444", alpha=0.25)
    ax2.plot(excess.index, excess.values, color="#b91c1c", linewidth=2.0, label=f"Local Excess = Station - Regional Median (Peak: +{excess.loc[chosen_time]:.0f} µg/m³)")
    ax2.axvline(chosen_time, color="#b91c1c", linestyle=":", linewidth=1.6)
    ax2.set_ylabel("Excess (µg/m³)", fontsize=10, fontweight="bold", color="#1e293b")
    ax2.set_title("Attributable Local Excess (Filters Regional Smog, Isolates Local Emitters)", fontsize=11, fontweight="bold", color="#0f172a", pad=8)
    ax2.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)
    
    # Panel 3: PM10 Co-movement Signature
    ax3.plot(p25.index, p25.values, color="#dc2626", linewidth=1.8, label="PM2.5 (Fine Combustion/Smoke)")
    ax3.plot(p10.index, p10.values, color="#2563eb", linewidth=1.8, label="PM10 (Coarse Particulates)")
    ax3.axvline(chosen_time, color="#b91c1c", linestyle=":", linewidth=1.6)
    ratio = p25.loc[chosen_time] / p10.loc[chosen_time] if p10.loc[chosen_time] > 0 else 0
    ax3.set_ylabel("Concentration (µg/m³)", fontsize=10, fontweight="bold", color="#1e293b")
    ax3.set_title(f"Co-Pollutant Signature at Spike: PM2.5/PM10 Ratio = {ratio:.2f} (Strong Combustion Signal)", fontsize=11, fontweight="bold", color="#0f172a", pad=8)
    ax3.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)
    
    ax3.set_xlabel("Date & Time (UTC)", fontsize=10, fontweight="bold", color="#1e293b")
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    fig.autofmt_xdate(rotation=0, ha="center")
    
    os.makedirs("docs", exist_ok=True)
    out_plot = "docs/real_spike_feasibility_plot.png"
    plt.tight_layout()
    plt.savefig(out_plot, dpi=160)
    plt.close()
    print(f"Generated Punjabi Bagh spike plot saved to {out_plot}")
    
    spike_summary = {
        "station_id": chosen_sid,
        "station_name": station_name,
        "peak_time_utc": chosen_time.isoformat(),
        "station_pm25": float(p25.loc[chosen_time]),
        "station_pm10": float(p10.loc[chosen_time]),
        "pm25_to_pm10_ratio": round(ratio, 2),
        "regional_median_pm25": float(med.loc[chosen_time]),
        "local_excess_pm25": float(excess.loc[chosen_time]),
        "plot_path": out_plot
    }
    with open("data/real_spike_event.json", "w") as fp:
        json.dump(spike_summary, fp, indent=2)
    return spike_summary

if __name__ == "__main__":
    plot_punjabi_bagh_spike()
