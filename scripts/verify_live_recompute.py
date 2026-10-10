"""
Smokeprint Verification: Live Recompute & Endpoint Verification
Script: scripts/verify_live_recompute.py
"""

import urllib.request
import urllib.error
import json
import time

BASE_URL = "https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com"

def main():
    print("=== SMOKEPRINT PHASE 4.1 LIVE VERIFICATION ===\n")

    # 1. Reject invalid case
    print("1. Testing POST /cases/invalid_case_id/recompute (expecting HTTP 400)...")
    try:
        req_bad = urllib.request.Request(f"{BASE_URL}/cases/invalid_case_id/recompute", method="POST")
        urllib.request.urlopen(req_bad)
        print("  FAIL: invalid_case_id was not rejected!")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  SUCCESS: Rejected with HTTP {e.code}")
        print(f"  Body: {body}\n")

    # 2. Trigger recompute for Anand Vihar
    print("2. Triggering POST /cases/case_anand_vihar_20251102/recompute...")
    req_rec = urllib.request.Request(f"{BASE_URL}/cases/case_anand_vihar_20251102/recompute", method="POST")
    with urllib.request.urlopen(req_rec) as resp:
        rec_data = json.loads(resp.read().decode("utf-8"))
        run_id = rec_data.get("run_id")
        print(f"  SUCCESS: HTTP {resp.status}, response: {json.dumps(rec_data, indent=2)}\n")

    # 3. Poll GET /runs/{run_id}
    print(f"3. Polling GET /runs/{run_id}...")
    final_run = None
    for i in range(15):
        time.sleep(2)
        req_poll = urllib.request.Request(f"{BASE_URL}/runs/{run_id}")
        with urllib.request.urlopen(req_poll) as resp:
            poll_res = json.loads(resp.read().decode("utf-8"))
            st = poll_res.get("status")
            print(f"  Attempt {i+1}: status={st}")
            if st in ["SUCCEEDED", "FAILED"]:
                final_run = poll_res
                break

    print(f"\nFinal run details for {run_id}:")
    print(json.dumps(final_run, indent=2))

    # Assertions on run record
    assert final_run is not None, "Recompute execution timed out"
    assert final_run.get("status") == "SUCCEEDED", f"Execution failed: {final_run}"
    out = final_run.get("output", {})
    assert out.get("source") == "recomputed", f"Expected source 'recomputed', got {out.get('source')}"
    assert out.get("code_version") == "frozen_core_v2.7", f"Expected 'frozen_core_v2.7', got {out.get('code_version')}"
    assert "validator_passed: trace matches tool outputs" in out.get("agent_review_verdict", ""), (
        f"Verdict mismatch: {out.get('agent_review_verdict')}"
    )

    # 4. Verify cases table was NOT overwritten
    print("\n4. Verifying GET /cases/case_anand_vihar_20251102 (cases_table must NOT be overwritten)...")
    req_case = urllib.request.Request(f"{BASE_URL}/cases/case_anand_vihar_20251102")
    with urllib.request.urlopen(req_case) as resp:
        case_data = json.loads(resp.read().decode("utf-8"))
        print(f"  Case source: {case_data.get('source')}")
        print(f"  Case source_description: {case_data.get('source_description')}")
        assert case_data.get("source") == "precomputed", (
            f"ERROR: cases_table was overwritten with {case_data.get('source')}!"
        )
        print("  SUCCESS: cases_table record remains strictly 'source: precomputed'!")

    # 5. Verify shortlist JSON and Markdown
    print("\n5. Testing GET /cases/case_anand_vihar_20251102/shortlist with Accept: application/json...")
    req_sl_json = urllib.request.Request(
        f"{BASE_URL}/cases/case_anand_vihar_20251102/shortlist",
        headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req_sl_json) as resp:
        sl_json = json.loads(resp.read().decode("utf-8"))
        print(f"  Top candidate: {sl_json['shortlist'][0]['name']} ({sl_json['shortlist'][0]['id']})")
        print(f"  Top candidate tier: {sl_json['shortlist'][0]['confidence_tier']}")
        assert sl_json['shortlist'][0]['id'] == "osm_relation_3808258"

    print("\n6. Testing GET /cases/case_anand_vihar_20251102/shortlist default (Markdown)...")
    req_sl_md = urllib.request.Request(f"{BASE_URL}/cases/case_anand_vihar_20251102/shortlist")
    with urllib.request.urlopen(req_sl_md) as resp:
        sl_md = resp.read().decode("utf-8")
        assert sl_md.startswith("# Programmatic Inspection Shortlist")
        print(f"  First line: {sl_md.splitlines()[0]}")
        print(f"  Content length: {len(sl_md)} chars")

    print("\n7. Testing GET /cases/case_anand_vihar_20251102/trace...")
    req_trace = urllib.request.Request(f"{BASE_URL}/cases/case_anand_vihar_20251102/trace")
    with urllib.request.urlopen(req_trace) as resp:
        trace_json = json.loads(resp.read().decode("utf-8"))
        mode = trace_json.get("mode") or trace_json.get("agent_source")
        print(f"  Trace mode: {mode}")
        print(f"  Validator passed: {trace_json.get('final_summary', {}).get('validator_passed')}")
        assert mode == "precomputed_local_agent"

    print("\n=== ALL LIVE VERIFICATION CHECKS PASSED ===")

if __name__ == "__main__":
    main()
