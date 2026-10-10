import json
import os

with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
    w12 = json.load(f)
recs = {r["time"]: r for r in w12["records"]}

refusal_bases = {
    "case_crri_20260515": "Detector: collapse_after_peak (abrupt telemetry collapse to 0.0 ug/m3; 0/3 neighbouring stations responded). Single-station instrument artifact.",
    "case_gurugram_20260630": "Detectors: constant_ratio_lock, collapse_after_peak (PM2.5/PM10 ratio locked at exactly 0.6000 for 4 consecutive hours; abrupt drop to NaN). Instrument logger fault.",
    "case_regional_smog_20251020": "Network-wide regional smog elevation: 21/22 reporting stations (95.5%) simultaneously elevated across airshed. Airshed-wide regional smog event."
}

case_times = {
    "case_anand_vihar_20251102": "2025-11-02T21:00",
    "case_anand_vihar_20260131": "2026-01-31T05:00",
    "case_anand_vihar_20260405": "2026-04-05T22:00",
    "case_crri_20260515": "2026-05-15T23:00",
    "case_gurugram_20260630": "2026-06-30T06:00",
    "case_regional_smog_20251020": "2025-10-20T17:00",
    "case_rkpuram_20251112": "2025-11-12T16:00",
}

for cid, t in case_times.items():
    cpath = f"data/cases_out/{cid}.json"
    web_cpath = f"web/src/data/cases/{cid}.json"
    with open(cpath, "r", encoding="utf-8") as f:
        cdata = json.load(f)

    r = recs[t]
    speed = float(r["wind_speed_ms"])
    deg = float(r["wind_direction_deg"])
    blh = float(r["boundary_layer_height_m"])
    is_low = speed < 1.5

    cdata["wind"] = {
        "wind_speed_ms": speed,
        "wind_direction_deg": deg,
        "wording": f"wind from {deg:.1f} deg",
        "boundary_layer_height_m": blh,
        "is_low_wind": is_low,
        "source": f"ERA5 hourly reanalysis ({t} UTC)"
    }
    cdata["is_low_wind"] = is_low

    if cid in refusal_bases:
        cdata["refusal_basis"] = refusal_bases[cid]
        cdata["refusal_reason"] = refusal_bases[cid]
        cdata["dispatch_refused"] = True
        # For refusal cases, do not show high/medium/low tier chips for fault or regional outcomes
        for h in cdata.get("hypotheses", []):
            h["confidence_tier"] = None
    else:
        # For candidate cases with wind < 1.5 m/s, every candidate must be low tier
        if is_low:
            for h in cdata.get("hypotheses", []):
                if not h.get("id", "").startswith("outcome_"):
                    h["confidence_tier"] = "low"

    # Save to data/cases_out and web/src/data/cases
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(cdata, f, indent=2)
    with open(web_cpath, "w", encoding="utf-8") as f:
        json.dump(cdata, f, indent=2)

print("Updated all 7 cases with exact ERA5 wind, low-wind tiers, and refusal basis.")
