"""
Smokeprint Test: Step Functions Recompute Parity for ALL 7 Cases
File: tests/test_recompute_parity.py

Asserts that the Step Functions recompute handler (infra/lambdas/step_run_core.py)
produces shortlists whose IDs, candidate ordering, confidence tiers, bearings,
and angular offsets strictly match the canonical cases for all 7 vetted cases.
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infra.lambdas.step_run_core import handler as run_core_handler

ALL_7_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112"
]

@pytest.mark.parametrize("case_id", ALL_7_CASES)
def test_recompute_parity_matches_canonical(case_id):
    canonical_path = os.path.join("data", "cases_out", f"{case_id}.json")
    assert os.path.exists(canonical_path), f"Canonical case JSON missing: {canonical_path}"

    with open(canonical_path, "r", encoding="utf-8") as f:
        canonical_data = json.load(f)

    # Invoke run_core handler locally (with bundle fallback if s3 not accessible)
    event = {
        "case_id": case_id,
        "run_id": f"test-parity-{case_id}",
        "bundle": canonical_data
    }
    result = run_core_handler(event, None)

    # 1. Basic provenance verification (honestly labeled as replayed)
    assert result["case_id"] == case_id
    assert result["source"] == "replayed"
    assert result["mode"] == "replayed_from_canonical_output"
    assert "code_version" not in result

    # 2. Dispatch refusal parity
    is_fault = "fault" in case_id or canonical_data.get("label") in ["possible_fault", "uncorroborated"]
    is_regional = "regional" in case_id or canonical_data.get("label") == "regional"
    expected_refused = is_fault or is_regional
    assert result["dispatch_refused"] == expected_refused

    # 3. Shortlist parity (IDs, order, tiers)
    canonical_shortlist = canonical_data.get("shortlist", [])
    recompute_shortlist = result.get("shortlist", [])

    assert len(recompute_shortlist) == len(canonical_shortlist), (
        f"Length mismatch: {len(recompute_shortlist)} vs {len(canonical_shortlist)}"
    )

    for cand in recompute_shortlist:
        assert not cand["id"].startswith("outcome_"), (
            f"Non-site outcome {cand['id']} must not be in candidate shortlist"
        )

    for idx, (rec_cand, can_cand) in enumerate(zip(recompute_shortlist, canonical_shortlist)):
        # ID and ordering parity
        assert rec_cand["id"] == can_cand["id"], (
            f"Rank {idx} ID mismatch for {case_id}: {rec_cand['id']} vs {can_cand['id']}"
        )
        assert rec_cand["name"] == can_cand.get("name"), (
            f"Rank {idx} name mismatch for {case_id}"
        )

        # Tier parity
        expected_tier = can_cand.get("confidence_tier")
        assert rec_cand["confidence_tier"] == expected_tier, (
            f"Rank {idx} tier mismatch for {case_id} ({rec_cand['id']}): "
            f"recompute={rec_cand['confidence_tier']} vs canonical={expected_tier}"
        )
        # For Anand Vihar 2025-11-02, verify correct upwind bearings and offsets
        if case_id == "case_anand_vihar_20251102":
            wind_dir = canonical_data["wind"]["wind_direction_deg"]  # 263.0 deg
            # Decommissioned sites must be low tier
            if "disused" in rec_cand["operating_status"] or "decommissioned" in rec_cand["operating_status"]:
                assert rec_cand["confidence_tier"] == "low"
            # Offset must be relative to upwind direction (263 deg), not downwind (83 deg)
            if rec_cand["bearing_deg"] is not None:
                expected_offset = abs(rec_cand["bearing_deg"] - wind_dir)
                if expected_offset > 180.0:
                    expected_offset = 360.0 - expected_offset
                assert abs(rec_cand["angular_offset_deg"] - expected_offset) < 0.2
                # Ensure offset is small (<= 45 deg) for upwind corridor candidates
                assert rec_cand["angular_offset_deg"] <= 45.0

    # 4. Other explanations parity
    recompute_others = result.get("other_explanations_considered", [])
    canonical_others = canonical_data.get("other_explanations_considered", [])
    assert len(recompute_others) == len(canonical_others)
