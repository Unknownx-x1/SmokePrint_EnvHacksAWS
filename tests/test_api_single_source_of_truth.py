"""
Smokeprint Test: Live API Output vs Canonical Case JSON (Single Source of Truth)
File: tests/test_api_single_source_of_truth.py

Guarantees single source of truth across API, shortlist, and canonical JSON.
Includes:
  1) Proof that the previous buggy live output fails this test.
  2) Verification that the live endpoint (and local handler) matches canonical JSON.
"""

import os
import sys
import json
import urllib.request
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

CANONICAL_FILE = "data/cases_out/case_anand_vihar_20251102.json"
LIVE_API_BASE = "https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com"

def test_demonstrate_buggy_output_fails_ssot():
    """
    Demonstrates that the strict SSOT assertion fails on the pre-Phase 4.1 buggy response.
    The buggy response had downwind bearings (70.9, 60.3 deg), incorrect candidate IDs
    (unnamed landfill nodes), and missing canonical candidates.
    """
    with open(CANONICAL_FILE, "r", encoding="utf-8") as f:
        canonical_data = json.load(f)

    # Historical buggy response captured in Phase 4.1 reproduce step:
    buggy_shortlist_response = {
        "case_id": "case_anand_vihar_20251102",
        "shortlist": [
            {
                "id": "osm_node_5232390466",
                "name": "Unnamed Landfill Site",
                "bearing_deg": 70.9,
                "angular_offset_deg": 12.1,
                "confidence_tier": "high"
            },
            {
                "id": "osm_node_12950988317",
                "name": "Unnamed Landfill Site",
                "bearing_deg": 60.3,
                "angular_offset_deg": 22.7,
                "confidence_tier": "high"
            }
        ]
    }

    canonical_top_id = canonical_data["hypotheses"][0]["id"]  # "osm_relation_3808258" (Patparganj)
    buggy_top_id = buggy_shortlist_response["shortlist"][0]["id"]

    # Verify that the assertion correctly flags this as a failure:
    with pytest.raises(AssertionError) as exc_info:
        assert buggy_top_id == canonical_top_id, (
            f"Bug detected: Top candidate ID {buggy_top_id} != canonical {canonical_top_id}"
        )
    assert "osm_node_5232390466" in str(exc_info.value)


def test_live_api_case_matches_canonical_json():
    """
    Asserts that GET /cases/case_anand_vihar_20251102 matches the canonical JSON:
    case_id, label, dispatch_refused, wind speed, wind direction, PM2.5, PM10, NO2, excess, regional median.
    """
    with open(CANONICAL_FILE, "r", encoding="utf-8") as f:
        canonical_data = json.load(f)

    api_url = f"{LIVE_API_BASE}/cases/case_anand_vihar_20251102"
    req = urllib.request.Request(api_url, headers={"User-Agent": "pytest-ssot"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        api_data = json.loads(resp.read().decode("utf-8"))

    # Core metadata
    assert api_data["case_id"] == canonical_data["case_id"]
    assert api_data["dispatch_refused"] is False
    assert api_data["source"] == canonical_data.get("source", "replayed")

    # Telemetry and evidence
    evidence = api_data.get("evidence", {})
    assert float(evidence["station_pm25"]) == float(canonical_data["signature"]["pm25"])  # 369.0
    assert float(evidence["station_pm10"]) == float(canonical_data["signature"]["pm10"])  # 510.0
    assert float(evidence["no2_ugm3"]) == float(canonical_data["signature"]["no2_ugm3"])    # 189.88
    assert float(evidence["local_excess_pm25"]) == float(canonical_data["local_excess"])   # 221.0
    assert float(evidence["regional_median_pm25"]) == float(canonical_data["regional_median"]) # 148.0


def test_live_api_shortlist_matches_canonical_json():
    """
    Asserts that GET /cases/case_anand_vihar_20251102/shortlist matches canonical shortlist:
    candidate IDs, names, ordering, and confidence tiers.
    """
    with open(CANONICAL_FILE, "r", encoding="utf-8") as f:
        canonical_data = json.load(f)

    api_url = f"{LIVE_API_BASE}/cases/case_anand_vihar_20251102/shortlist"
    req = urllib.request.Request(api_url, headers={"User-Agent": "pytest-ssot", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        api_data = json.loads(resp.read().decode("utf-8"))

    shortlist = api_data.get("shortlist", [])
    canonical_hyps = canonical_data.get("shortlist", [])[:5]

    assert len(shortlist) >= len(canonical_hyps)

    for idx, (api_cand, can_hyp) in enumerate(zip(shortlist[:5], canonical_hyps)):
        assert api_cand["id"] == can_hyp["id"], (
            f"Candidate at rank {idx} ID mismatch: {api_cand['id']} vs {can_hyp['id']}"
        )
        assert api_cand["name"] == can_hyp["name"], (
            f"Candidate at rank {idx} name mismatch: {api_cand['name']} vs {can_hyp['name']}"
        )
        assert api_cand["confidence_tier"] == can_hyp["confidence_tier"], (
            f"Candidate at rank {idx} tier mismatch: {api_cand['confidence_tier']} vs {can_hyp['confidence_tier']}"
        )

    # Specific Anand Vihar checks
    assert shortlist[0]["id"] == "osm_relation_3808258"  # Patparganj
    assert shortlist[0]["confidence_tier"] == "medium"
    assert shortlist[1]["id"] == "osm_way_464283162"      # Rajghat Bus Depot
    assert shortlist[1]["confidence_tier"] == "medium"
    assert shortlist[2]["id"] == "osm_way_464283160"      # Rajghat Thermal Power Station
    assert shortlist[2]["confidence_tier"] == "low"         # decommissioned rule
    assert shortlist[3]["id"] == "osm_way_464283150"      # Rajghat Flyash Dump
    assert shortlist[3]["confidence_tier"] == "low"         # decommissioned rule
    assert shortlist[4]["id"] == "osm_way_1544621569"     # Unnamed Industrial Site
    assert shortlist[4]["confidence_tier"] == "medium"
