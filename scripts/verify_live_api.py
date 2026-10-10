import json
import urllib.request

API_BASE = "https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com"
CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112"
]

print("Fetching and comparing live API responses against canonical JSON...\n")

header = f"{'Case ID':<30} | {'Wind (spd/dir/ts)':<26} | {'Class / Refusal':<25} | {'Cand IDs (API vs Canon)':<25} | {'Tiers (API vs Canon)':<22} | {'Low Wind':<8} | {'Match?'}"
print(header)
print("-" * len(header))

all_matched = True

for cid in CASES:
    url = f"{API_BASE}/cases/{cid}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmokePrint-Audit/5.7"})
    with urllib.request.urlopen(req) as resp:
        api_data = json.loads(resp.read().decode("utf-8"))

    with open(f"data/cases_out/{cid}.json", "r", encoding="utf-8") as f:
        canon_data = json.load(f)

    # API wind
    api_wind = api_data.get("wind", {})
    canon_wind = canon_data.get("wind", {})

    api_spd = api_wind.get("wind_speed_ms")
    api_dir = api_wind.get("wind_direction_deg")
    api_ts = api_wind.get("timestamp_utc") or api_data.get("time_window", {}).get("interval_midpoint_utc", "")
    api_low = api_wind.get("is_low_wind", False)

    canon_spd = canon_wind.get("wind_speed_ms")
    canon_dir = canon_wind.get("wind_direction_deg")
    canon_ts = canon_wind.get("timestamp_utc") or canon_data.get("time_window", {}).get("interval_midpoint_utc", "")
    canon_low = canon_wind.get("is_low_wind", False)

    # Candidates & Tiers
    api_cands = [c.get("id") for c in api_data.get("shortlist", [])]
    canon_cands = [c.get("id") for c in canon_data.get("shortlist", [])]

    api_tiers = [c.get("confidence_tier") for c in api_data.get("shortlist", [])]
    canon_tiers = [c.get("confidence_tier") for c in canon_data.get("shortlist", [])]

    # Classification / refusal
    api_refused = api_data.get("dispatch_refused", False)
    canon_refused = canon_data.get("dispatch_refused", False)
    api_cls = api_data.get("classification") or ("Refused" if api_refused else "Local")
    canon_cls = canon_data.get("classification") or ("Refused" if canon_refused else "Local")

    # Match check
    wind_match = (api_spd == canon_spd and api_dir == canon_dir and api_low == canon_low)
    cands_match = (api_cands == canon_cands)
    tiers_match = (api_tiers == canon_tiers)
    refused_match = (api_refused == canon_refused)
    
    match = wind_match and cands_match and tiers_match and refused_match
    if not match:
        all_matched = False

    wind_str = f"{api_spd}m/s {api_dir}° @ {api_ts[:16]}"
    cls_str = f"{api_cls[:20]} (refused={api_refused})"
    cands_str = f"{len(api_cands)} cands (canon: {len(canon_cands)})"
    tiers_str = f"{api_tiers[:3]}..." if len(api_tiers) > 3 else f"{api_tiers}"
    low_str = str(api_low)
    status_str = "MATCH" if match else "MISMATCH"

    print(f"{cid:<30} | {wind_str:<26} | {cls_str:<25} | {cands_str:<25} | {tiers_str:<22} | {low_str:<8} | {status_str}")

print("\nAll cases match canonical data perfectly:", all_matched)
