import json

cases = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_rkpuram_20251112",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020"
]

print("=" * 90)
print("OFFSET TABLE FOR THE 6 VISIBLE CASES")
print("=" * 90)

for cid in cases:
    with open(f"data/cases_out/{cid}.json", "r", encoding="utf-8") as f:
        c = json.load(f)
    w = c.get("wind", {})
    ws = w.get("wind_speed_ms")
    wd = w.get("wind_direction_deg")
    sl = c.get("shortlist", [])
    refusal = c.get("refusal_basis") or c.get("refusal_reason")
    print(f"\nCase: {cid} | Wind: {ws} m/s @ {wd}° | Refused: {c.get('dispatch_refused')} | Shortlist count: {len(sl)}")
    if refusal:
        print(f"  Refusal Basis: {refusal}")
    for cand in sl:
        hid = cand["id"]
        name = cand["name"]
        dist = cand["distance_km"]
        bearing = cand["bearing_deg"]
        offset = cand["angular_offset_deg"]
        tier = cand["confidence_tier"]
        reasons = cand["reasons"]
        print(f"  - {hid:20} | {name[:30]:30} | {dist:5.2f} km | bearing {bearing:5.1f}° | offset {offset:5.1f}° | tier: {tier} | {reasons[0]}")
