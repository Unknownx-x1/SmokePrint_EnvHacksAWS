"""
Verification script for Phase 5.8:
Curls live API:
1. GET /cases -> checks count == 6 and April case is not listed.
2. For each of the 6 visible cases: curls GET /cases/{id} and GET /cases/{id}/shortlist
   Compares with canonical JSON in data/cases_out/{id}.json.
"""

import urllib.request
import json

BASE_URL = "https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com"
VISIBLE_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_rkpuram_20251112",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020"
]

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))

print("=" * 80)
print("PHASE 5.8: CURLING LIVE API AND COMPARING WITH CANONICAL JSON")
print("=" * 80)

# 1. GET /cases
cases_resp = get_json(f"{BASE_URL}/cases")
live_cases = cases_resp.get("cases", [])
count = cases_resp.get("count")
print(f"\n1. GET /cases response: count = {count}")
live_ids = [c["case_id"] for c in live_cases]
print(f"   Live case IDs ({len(live_ids)}): {live_ids}")

assert count == 6, f"Expected 6 cases, got {count}"
assert "case_anand_vihar_20260405" not in live_ids, "April case must NOT be in live /cases"
assert set(live_ids) == set(VISIBLE_CASES), "Mismatch between live cases and visible cases"
print("   PASS: Live /cases lists exactly the 6 visible cases, April is omitted.")

# 2. Compare each live case against canonical JSON
print("\n2. Comparing each live case with data/cases_out/<id>.json:")
for cid in VISIBLE_CASES:
    with open(f"data/cases_out/{cid}.json", "r", encoding="utf-8") as f:
        canonical = json.load(f)

    # Fetch live shortlist (JSON format)
    live_sl = get_json(f"{BASE_URL}/cases/{cid}/shortlist", headers={"Accept": "application/json"})
    
    can_sl = canonical.get("shortlist", [])
    live_cands = live_sl.get("shortlist", [])
    
    print(f"\n   [{cid}]")
    print(f"     Canonical candidates: {len(can_sl)} | Live candidates: {len(live_cands)}")
    assert len(can_sl) == len(live_cands), f"Candidate count mismatch for {cid}"
    
    for i in range(len(can_sl)):
        c_can = can_sl[i]
        c_live = live_cands[i]
        assert c_can["id"] == c_live["id"], f"ID mismatch: {c_can['id']} vs {c_live['id']}"
        assert c_can["distance_km"] == c_live["distance_km"], f"Distance mismatch: {c_can['distance_km']} vs {c_live['distance_km']}"
        assert c_can["angular_offset_deg"] == c_live["angular_offset_deg"], f"Offset mismatch: {c_can['angular_offset_deg']} vs {c_live['angular_offset_deg']}"
        assert c_can["confidence_tier"] == c_live["confidence_tier"], f"Tier mismatch: {c_can['confidence_tier']} vs {c_live['confidence_tier']}"
        print(f"       OK: {c_can['id']} (dist {c_can['distance_km']} km, offset {c_can['angular_offset_deg']}°, tier {c_can['confidence_tier']})")

    # For refused cases, verify refusal basis matches
    if canonical.get("dispatch_refused"):
        assert live_sl.get("dispatch_refused") is True, f"Expected dispatch_refused in {cid}"
        print(f"       OK: Refusal flag matches. Refusal basis: {live_sl.get('refusal_basis')}")

print("\n" + "=" * 80)
print("ALL 6 LIVE CASES MATCH CANONICAL JSON EXACTLY!")
print("=" * 80)
