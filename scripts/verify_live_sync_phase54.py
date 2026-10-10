"""
Smokeprint Verification: Phase 5.4 Live API and Recompute Verification
File: scripts/verify_live_sync_phase54.py
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

LIVE_API_BASE = "https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com"

ALL_7_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_rkpuram_20251112",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
]

def http_get(url: str, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers={"User-Agent": "SmokePrint-Phase54", **headers})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post(url: str, payload=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "SmokePrint-Phase54", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("=" * 100)
    print("PHASE 5.4 LIVE API SYNC VERIFICATION FOR ALL 7 CANONICAL CASES")
    print(f"Live API Base: {LIVE_API_BASE}")
    print("=" * 100)

    discrepancies = []

    print(f"{'Case ID':<28} | {'Wind Speed / Dir':<18} | {'Classification':<15} | {'Cand':<4} | {'Tiers':<18} | {'LowWind':<7} | {'Refused':<7}")
    print("-" * 100)

    for case_id in ALL_7_CASES:
        canonical_path = f"data/cases_out/{case_id}.json"
        with open(canonical_path, "r", encoding="utf-8") as f:
            can_data = json.load(f)

        # GET /cases/{id}
        case_url = f"{LIVE_API_BASE}/cases/{case_id}"
        live_case = http_get(case_url)

        # GET /cases/{id}/shortlist
        shortlist_url = f"{LIVE_API_BASE}/cases/{case_id}/shortlist"
        live_shortlist_resp = http_get(shortlist_url, headers={"Accept": "application/json"})

        # Extract fields
        wind_info = live_case.get("wind", {})
        ws = wind_info.get("wind_speed_ms")
        wd = wind_info.get("wind_direction_deg")
        wind_str = f"{ws:.2f} m/s @ {wd:.1f}°" if ws is not None and wd is not None else "N/A"

        classification = live_case.get("classification") or live_case.get("label", "N/A")
        shortlist = live_shortlist_resp.get("shortlist", [])
        num_candidates = len(shortlist)
        tiers = [c.get("confidence_tier") for c in shortlist]
        tiers_str = ", ".join(str(t) for t in tiers) if tiers else "none"
        low_wind = bool(live_case.get("wind", {}).get("is_low_wind", False))
        refused = bool(live_case.get("dispatch_refused", False))

        print(f"{case_id:<28} | {wind_str:<18} | {str(classification):<15} | {num_candidates:<4} | {tiers_str:<18} | {str(low_wind):<7} | {str(refused):<7}")

        # Comparison with canonical JSON
        can_wind = can_data.get("wind", {})
        if abs(can_wind.get("wind_speed_ms", 0) - ws) > 0.05:
            discrepancies.append(f"{case_id}: wind speed mismatch: live {ws} vs canonical {can_wind.get('wind_speed_ms')}")
        if abs(can_wind.get("wind_direction_deg", 0) - wd) > 0.5:
            discrepancies.append(f"{case_id}: wind direction mismatch: live {wd} vs canonical {can_wind.get('wind_direction_deg')}")
        if refused != can_data.get("dispatch_refused"):
            discrepancies.append(f"{case_id}: dispatch_refused mismatch: live {refused} vs canonical {can_data.get('dispatch_refused')}")
        if low_wind != can_wind.get("is_low_wind"):
            discrepancies.append(f"{case_id}: low_wind mismatch: live {low_wind} vs canonical {can_wind.get('is_low_wind')}")
        if num_candidates != len(can_data.get("shortlist", [])):
            discrepancies.append(f"{case_id}: candidate count mismatch: live {num_candidates} vs canonical {len(can_data.get('shortlist', []))}")

        # Candidate by candidate ID check
        can_shortlist = can_data.get("shortlist", [])
        for idx, (live_c, can_c) in enumerate(zip(shortlist, can_shortlist)):
            if live_c["id"] != can_c["id"]:
                discrepancies.append(f"{case_id} rank {idx}: candidate ID mismatch: live {live_c['id']} vs canonical {can_c['id']}")
            if live_c.get("confidence_tier") != can_c.get("confidence_tier"):
                discrepancies.append(f"{case_id} {live_c['id']}: tier mismatch: live {live_c.get('confidence_tier')} vs canonical {can_c.get('confidence_tier')}")

    print("=" * 100)
    if not discrepancies:
        print("ALL 7 CANONICAL CASES PERFECTLY MATCH THE LIVE API (0 DISCREPANCIES)!")
    else:
        print(f"Found {len(discrepancies)} discrepancies:")
        for d in discrepancies:
            print(f"  - {d}")

    # Recompute test
    print("\n" + "=" * 100)
    print("TESTING POST /cases/case_anand_vihar_20251102/recompute")
    print("=" * 100)

    recompute_url = f"{LIVE_API_BASE}/cases/case_anand_vihar_20251102/recompute"
    start_resp = http_post(recompute_url, {})
    print(f"Triggered recompute response: {json.dumps(start_resp, indent=2)}")
    run_id = start_resp.get("run_id")

    # Poll runs/{run_id} until SUCCEEDED
    run_status_url = f"{LIVE_API_BASE}/runs/{run_id}"
    completed_run = None
    for attempt in range(15):
        time.sleep(2)
        status_resp = http_get(run_status_url)
        status = status_resp.get("status")
        print(f"  Poll #{attempt+1}: status={status}")
        if status in ["SUCCEEDED", "FAILED"]:
            completed_run = status_resp
            break

    if completed_run:
        print("\nFINAL RUN RESULT:")
        print(f"  Run ID: {completed_run.get('run_id')}")
        print(f"  Status: {completed_run.get('status')}")
        print(f"  Source: {completed_run.get('source')} (replayed)")
        print(f"  Mode: {completed_run.get('mode')}")
        print(f"  Replayed Note: {completed_run.get('replayed_note')}")
        output = completed_run.get("output", {})
        cand_count = len(output.get("shortlist", []))
        print(f"  Candidates in Shortlist: {cand_count}")
        for c in output.get("shortlist", []):
            print(f"    - {c['name']} ({c['id']}) | Tier: {c.get('confidence_tier')} | {c.get('reasons', [''])[0]}")
    else:
        print("Run polling timed out or run not completed.")

if __name__ == "__main__":
    main()
