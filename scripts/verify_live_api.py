"""
Smokeprint Phase 4 Live API Verifier
Script: scripts/verify_live_api.py

Hits all HTTP API endpoints on the live deployment:
  1. GET /health
  2. GET /cases
  3. GET /cases/case_anand_vihar_20251102
  4. GET /cases/case_anand_vihar_20251102/shortlist
  5. GET /cases/case_anand_vihar_20251102/trace
  6. GET /backtest
  7. POST /cases/case_anand_vihar_20251102/recompute (Triggers Step Functions execution)
  8. GET /runs/<run_id> (Polls recompute execution status)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com"

def http_get(path: str):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmokePrint-Verifier"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            elapsed = time.time() - start
            content_type = resp.headers.get("Content-Type", "")
            return resp.status, data.decode("utf-8", errors="replace"), elapsed, content_type
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        return e.code, e.read().decode("utf-8", errors="replace"), elapsed, ""
    except Exception as e:
        elapsed = time.time() - start
        return 500, str(e), elapsed, ""

def http_post(path: str, payload: dict):
    url = f"{BASE_URL}{path}"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "SmokePrint-Verifier"},
        method="POST"
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            elapsed = time.time() - start
            return resp.status, data.decode("utf-8", errors="replace"), elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        return e.code, e.read().decode("utf-8", errors="replace"), elapsed
    except Exception as e:
        elapsed = time.time() - start
        return 500, str(e), elapsed

def run_verification():
    print("=" * 85)
    print(f"SMOKEPRINT LIVE HTTP API VERIFICATION: {BASE_URL}")
    print("=" * 85)

    # 1. GET /health
    print("\n--- [1] GET /health ---")
    status, body, elapsed, ct = http_get("/health")
    print(f"Status: {status} ({elapsed*1000:.1f}ms) | Content-Type: {ct}")
    print(f"Body: {body.strip()}")

    # 2. GET /cases
    print("\n--- [2] GET /cases ---")
    status, body, elapsed, ct = http_get("/cases")
    print(f"Status: {status} ({elapsed*1000:.1f}ms)")
    try:
        cases_json = json.loads(body)
        print(f"Count: {cases_json.get('count')} cases returned:")
        for c in cases_json.get("cases", []):
            print(f"  - {c.get('case_id')}: label={c.get('label')}, source={c.get('source')}, dispatch_refused={c.get('dispatch_refused')}")
    except Exception:
        print(f"Body: {body[:300]}...")

    # 3. GET /cases/case_anand_vihar_20251102
    print("\n--- [3] GET /cases/case_anand_vihar_20251102 ---")
    status, body, elapsed, ct = http_get("/cases/case_anand_vihar_20251102")
    print(f"Status: {status} ({elapsed*1000:.1f}ms)")
    try:
        c_detail = json.loads(body)
        print(f"Case ID: {c_detail.get('case_id')} | Station: {c_detail.get('station_name')}")
        print(f"Evidence: PM2.5 = {c_detail.get('evidence', {}).get('station_pm25')} ug/m3, Excess = {c_detail.get('evidence', {}).get('local_excess_pm25')} ug/m3")
        print(f"Top Candidate: {c_detail.get('shortlist', [{}])[0].get('name')} (Tier: {c_detail.get('shortlist', [{}])[0].get('confidence_tier')})")
    except Exception:
        print(f"Body: {body[:300]}...")

    # 4. GET /cases/case_anand_vihar_20251102/shortlist
    print("\n--- [4] GET /cases/case_anand_vihar_20251102/shortlist ---")
    status, body, elapsed, ct = http_get("/cases/case_anand_vihar_20251102/shortlist")
    print(f"Status: {status} ({elapsed*1000:.1f}ms) | Content-Type: {ct}")
    lines = body.strip().split("\n")
    print(f"Lines returned: {len(lines)}")
    for line in lines[:8]:
        print("  " + line)

    # 5. GET /cases/case_anand_vihar_20251102/trace
    print("\n--- [5] GET /cases/case_anand_vihar_20251102/trace ---")
    status, body, elapsed, ct = http_get("/cases/case_anand_vihar_20251102/trace")
    print(f"Status: {status} ({elapsed*1000:.1f}ms)")
    try:
        t_json = json.loads(body)
        print(f"Trace Mode: {t_json.get('mode')} | Model: {t_json.get('model')}")
        print(f"Validator Passed: {t_json.get('final_summary', {}).get('validator_passed')}")
        print(f"Critic Output Snippet: {t_json.get('final_summary', {}).get('final_output', {}).get('critic_audit', '')[:160]}...")
    except Exception:
        print(f"Body: {body[:300]}...")

    # 6. GET /backtest
    print("\n--- [6] GET /backtest ---")
    status, body, elapsed, ct = http_get("/backtest")
    print(f"Status: {status} ({elapsed*1000:.1f}ms)")
    try:
        bt = json.loads(body)
        print(f"Loaded Backtest summary keys: {list(bt.keys())}")
        for k in list(bt.keys())[:3]:
            print(f"  {k}: {bt[k].get('label')} -> P@3: {bt[k].get('p3', [0])[0]*100:.1f}%")
    except Exception:
        print(f"Body: {body[:300]}...")

    # 7. POST /cases/case_anand_vihar_20251102/recompute (Triggers Step Functions!)
    print("\n--- [7] POST /cases/case_anand_vihar_20251102/recompute ---")
    status, body, elapsed = http_post("/cases/case_anand_vihar_20251102/recompute", {})
    print(f"Status: {status} ({elapsed*1000:.1f}ms)")
    print(f"Body: {body.strip()}")
    
    run_id = None
    try:
        recomp_res = json.loads(body)
        run_id = recomp_res.get("run_id")
        exec_arn = recomp_res.get("execution_arn")
        print(f"Execution ARN: {exec_arn}")
        print(f"Run ID: {run_id}")
    except Exception:
        pass

    # 8. Poll GET /runs/{run_id} to observe Step Functions execution
    if run_id:
        print(f"\n--- [8] GET /runs/{run_id} (Polling Step Functions execution) ---")
        for poll in range(1, 10):
            time.sleep(1.5)
            status, body, elapsed, ct = http_get(f"/runs/{run_id}")
            try:
                run_data = json.loads(body)
                st = run_data.get("status")
                print(f"  Poll {poll}: status = {st} ({elapsed*1000:.1f}ms)")
                if st in ["SUCCEEDED", "FAILED"]:
                    print(f"\nExecution finished with status: {st}!")
                    print(f"Execution output: {json.dumps(run_data.get('output'), indent=2)}")
                    break
            except Exception as e:
                print(f"  Poll error: {e}")

    print("\n" + "=" * 85)
    print("LIVE API VERIFICATION COMPLETE")
    print("=" * 85)

if __name__ == "__main__":
    run_verification()
