import json
import os

with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
    w12 = json.load(f)
recs = {r["time"]: r for r in w12["records"]}

case_configs = [
    ("case_anand_vihar_20251102", "2025-11-02T21:00"),
    ("case_anand_vihar_20260131", "2026-01-31T05:00"),
    ("case_anand_vihar_20260405", "2026-04-05T22:00"),
    ("case_crri_20260515", "2026-05-15T23:00"),
    ("case_gurugram_20260630", "2026-06-30T06:00"),
    ("case_regional_smog_20251020", "2025-10-20T17:00"),
    ("case_rkpuram_20251112", "2025-11-12T16:00"),
]

for cid, t in case_configs:
    with open(f"data/cases_out/{cid}.json", "r", encoding="utf-8") as f:
        cdata = json.load(f)
    old_wind = cdata.get("wind")
    r = recs.get(t)
    print("=" * 60)
    print("CASE:", cid)
    print("  OLD WIND in case JSON:", old_wind)
    print(f"  NEW ERA5 from wind_hourly_12m: speed={r['wind_speed_ms']} m/s, dir={r['wind_direction_deg']} deg, blh={r['boundary_layer_height_m']} m, time={t}")
    hyps = cdata.get("hypotheses", [])
    print(f"  CURRENT TIERS in case JSON: {[h.get('confidence_tier') for h in hyps]}")
