import json
import re
import urllib.request

CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112"
]

print("===============================================================================")
print("ITEM 1: CROSS-CASE AUDIT & SHORTLIST / CRITIC CANDIDATE PARITY")
print("===============================================================================")
for c in CASES:
    with open(f"data/cases_out/{c}.json", "r", encoding="utf-8") as f:
        cd = json.load(f)
    with open(f"data/agent_traces/{c}.json", "r", encoding="utf-8") as f:
        td = json.load(f)
    w = cd.get("wind", {})
    ws = w.get("wind_speed_ms")
    wd = w.get("wind_direction_deg")
    is_low = cd.get("is_low_wind", False)
    refused = cd.get("dispatch_refused", False)
    print(f"\nCASE: {c}")
    print(f"  Wind: {ws} m/s, from-direction: {wd}° (Low-wind: {is_low}, Refused: {refused})")
    print("  Canonical Shortlist:")
    shortlist_ids = []
    for cand in cd.get("shortlist", []):
        shortlist_ids.append(cand["id"])
        lat = cand.get("lat")
        lon = cand.get("lon")
        lat_str = f"{lat:.5f}" if lat is not None else "None"
        lon_str = f"{lon:.5f}" if lon is not None else "None"
        dist = cand.get("distance_km")
        dist_str = f"{dist:.2f}" if dist is not None else "None"
        bearing = cand.get("bearing_deg")
        bearing_str = f"{bearing:.1f}" if bearing is not None else "None"
        offset = cand.get("angular_offset_deg")
        offset_str = f"{offset:.1f}" if offset is not None else "None"
        tier = cand.get("confidence_tier")
        print(f"    - [{cand['id']}] {cand['name']} | centroid=({lat_str}, {lon_str}) | dist={dist_str} km | bearing={bearing_str}° | offset={offset_str}° | tier={tier}")

    critic_text = ""
    for att in td.get("attempts", []):
        critic_text += " " + att.get("critic_response", "")
    critic_cands = sorted(list(set(re.findall(r"\b(osm_(?:relation|way|node)_\d+)\b", critic_text))))
    print(f"  Critic Named Candidates: {critic_cands}")
    unlisted = [x for x in critic_cands if x not in shortlist_ids]
    if unlisted:
        print(f"  --> AUDIT VERDICT: FAIL - Critic names unlisted candidates: {unlisted}")
    else:
        print(f"  --> AUDIT VERDICT: PASS - All Critic named candidates exist in canonical shortlist.")

print("\n===============================================================================")
print("ITEM 3: TIMESTAMP & ERA5 AUDIT TABLE")
print("===============================================================================")
with open("data/demo_cases_vetted.json", "r", encoding="utf-8") as f:
    vetted_cases = list(json.load(f).values())
vetted_map = {vc["case_id"]: vc for vc in vetted_cases}

with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
    era5_records = {r["time"]: r for r in json.load(f)["records"]}

print(f"{'Case ID':<28} | {'Vetted IST':<19} | {'Vetted UTC':<17} | {'Midpoint Conv':<13} | {'ERA5 UTC':<16} | {'Speed / Dir':<16} | {'Status'}")
print("-" * 125)
for c in CASES:
    vc = vetted_map[c]
    with open(f"data/cases_out/{c}.json", "r", encoding="utf-8") as f:
        cd = json.load(f)
    tw = cd["time_window"]
    ist = tw["interval_midpoint_ist"].replace(" IST", "")
    utc = tw["interval_midpoint_utc"]
    era5_key = utc[:13] + ":00"
    era5_row = era5_records.get(era5_key, {})
    e_spd = era5_row.get("wind_speed_ms")
    e_dir = era5_row.get("wind_direction_deg")
    w = cd["wind"]
    match = (w["wind_speed_ms"] == e_spd) and (w["wind_direction_deg"] == e_dir)
    status = "ALIGNED" if match else "MISMATCH"
    print(f"{c:<28} | {ist:<19} | {utc:<17} | {'1h-midpoint':<13} | {era5_key:<16} | {e_spd:>4.2f}m/s / {e_dir:>5.1f}° | {status}")

print("\n===============================================================================")
print("ITEM 8: FINAL API / CASE OUTPUT SUMMARY")
print("===============================================================================")
print(f"{'Case ID':<28} | {'Classification':<15} | {'Wind':<18} | {'Tiers Present':<15} | {'Candidates':<10} | {'Low-Wind':<9} | {'Refused'}")
print("-" * 115)
for c in CASES:
    with open(f"data/cases_out/{c}.json", "r", encoding="utf-8") as f:
        cd = json.load(f)
    w = cd["wind"]
    wind_str = f"{w['wind_speed_ms']:.2f}m/s @ {w['wind_direction_deg']:.0f}°"
    tiers = [cand["confidence_tier"] for cand in cd.get("shortlist", [])]
    tier_summary = ",".join(sorted(set(str(t) for t in tiers)))
    cand_count = len(cd.get("shortlist", []))
    low_w = cd.get("is_low_wind", False)
    refused = cd.get("dispatch_refused", False)
    cls = cd.get("classification", cd.get("label", ""))
    print(f"{c:<28} | {cls:<15} | {wind_str:<18} | {tier_summary:<15} | {cand_count:<10} | {str(low_w):<9} | {str(refused)}")
