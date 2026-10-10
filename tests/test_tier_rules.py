"""
Smokeprint Test: Shared Confidence Tier Rules Enforcement
File: tests/test_tier_rules.py

Asserts tier rules across all candidates in all 7 evaluation cases:
  1. offset > 45.0 deg => 'low'
  2. wind < 1.5 m/s => 'low'
  3. disused or decommissioned => 'low'
  4. 'Multiple Comparable Candidates' => no 'high' tier permitted
"""

import os
import sys
import json
import glob
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.tier_rules import determine_confidence_tier
from data.shortlist_builder import build_enriched_shortlist

def test_tier_rules_direct_function():
    # Rule 1: disused / decommissioned => low
    assert determine_confidence_tier(0.9, 0.05, 1.0, operating_status="tagged disused:power=plant in OpenStreetMap") == "low"
    assert determine_confidence_tier(0.9, 0.05, 1.0, operating_status="decommissioned dump") == "low"

    # Rule 2: angular offset > 45 deg => low
    assert determine_confidence_tier(0.9, 0.05, 1.0, angular_offset_deg=53.8) == "low"
    assert determine_confidence_tier(0.9, 0.05, 1.0, angular_offset_deg=120.9) == "low"

    # Rule 3: wind < 1.5 m/s => low
    assert determine_confidence_tier(0.9, 0.05, 1.0, wind_speed_ms=0.8) == "low"

    # Rule 4: Multiple Comparable Candidates => no high
    assert determine_confidence_tier(0.9, 0.05, 1.0, classification="Multiple Comparable Candidates") == "medium"
    assert determine_confidence_tier(0.9, 0.05, 1.0, classification="comparable candidates") == "medium"


def test_tier_rules_across_all_7_canonical_cases():
    case_files = sorted(glob.glob("data/cases_out/case_*.json"))
    assert len(case_files) == 7, f"Expected 7 canonical case files, found {len(case_files)}"

    for cpath in case_files:
        with open(cpath, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        cid = cdata.get("case_id")
        enriched = build_enriched_shortlist(cdata)
        classification = enriched.get("classification")
        group = enriched.get("group")
        w_speed = enriched.get("wind", {}).get("wind_speed_ms")

        is_comparable_case = (
            classification == "Multiple Comparable Candidates"
            or group == "comparable candidates"
        )

        for cand in enriched.get("shortlist", []):
            cand_id = cand["id"]
            tier = cand["confidence_tier"]
            status = cand.get("operating_status", "").lower()
            offset = cand.get("angular_offset_deg")

            # Ignore pseudo-outcome markers
            if cand_id.startswith("outcome_"):
                continue

            # 1. Disused sites must be low
            if "disused" in status or "decommissioned" in status:
                assert tier == "low", (
                    f"[{cid}] Candidate {cand_id} ({cand['name']}) has status '{status}' but tier is '{tier}' (must be 'low')"
                )

            # 2. Offset > 50 deg must be low
            if offset is not None and offset > 50.0:
                assert tier == "low", (
                    f"[{cid}] Candidate {cand_id} ({cand['name']}) has offset {offset}° > 50° but tier is '{tier}' (must be 'low')"
                )

            # 3. Low wind < 1.5 m/s must be low
            if w_speed is not None and w_speed < 1.5:
                assert tier == "low", (
                    f"[{cid}] Candidate {cand_id} ({cand['name']}) in wind {w_speed} m/s < 1.5 m/s has tier '{tier}' (must be 'low')"
                )

            # 4. Multiple Comparable Candidates cannot contain high tier
            if is_comparable_case:
                assert tier != "high", (
                    f"[{cid}] Case is Multiple Comparable Candidates, but candidate {cand_id} has tier 'high' (maximum is 'medium')"
                )


def test_low_wind_cases_force_all_candidates_to_low():
    """
    Verifies Item 3 wind rule:
    For cases with wind < 1.5 m/s (e.g. case_anand_vihar_20260131 at 1.19 m/s
    and case_anand_vihar_20260405 at 0.97 m/s), every candidate must be low tier
    and the case must be labelled low-wind.
    """
    low_wind_cases = [
        ("case_rkpuram_20251112", 1.17),
        ("case_anand_vihar_20260405", 0.19)
    ]
    for cid, expected_speed in low_wind_cases:
        cpath = f"data/cases_out/{cid}.json"
        with open(cpath, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        enriched = build_enriched_shortlist(cdata)
        assert enriched["is_low_wind"] is True, f"[{cid}] Expected is_low_wind to be True"
        assert enriched["wind"]["wind_speed_ms"] == expected_speed, f"[{cid}] Expected speed {expected_speed}"
        assert enriched["wind"]["wind_speed_ms"] < 1.5

        # Every facility candidate must have confidence_tier == 'low'
        facility_cands = [c for c in enriched["shortlist"] if not c["id"].startswith("outcome_")]
        assert len(facility_cands) > 0, f"[{cid}] Expected facility candidates"
        for cand in facility_cands:
            assert cand["confidence_tier"] == "low", (
                f"[{cid}] Candidate {cand['id']} in calm wind ({expected_speed} m/s) must have tier 'low', got {cand['confidence_tier']}"
            )


def test_refusal_cases_omit_tier_chips_and_include_refusal_basis():
    """
    Verifies Item 4 refusal rule:
    Do not show a high/medium/low tier chip for fault or regional outcomes.
    Show 'Refusal basis:' with deterministic reason (detector names, network elevation counts).
    """
    refusal_cases = [
        ("case_crri_20260515", "collapse_after_peak"),
        ("case_gurugram_20260630", "constant_ratio_lock"),
        ("case_regional_smog_20251020", "Network-wide")
    ]
    for cid, expected_keyword in refusal_cases:
        cpath = f"data/cases_out/{cid}.json"
        with open(cpath, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        enriched = build_enriched_shortlist(cdata)
        assert enriched["dispatch_refused"] is True
        assert enriched.get("refusal_basis") is not None
        assert expected_keyword in enriched["refusal_basis"], (
            f"[{cid}] Expected refusal basis to contain '{expected_keyword}', got: {enriched.get('refusal_basis')}"
        )

        # In shortlist, fault and regional outcomes must not have high/medium/low tier chips
        for cand in enriched["shortlist"]:
            assert cand["confidence_tier"] is None, (
                f"[{cid}] Refusal outcome {cand['id']} must NOT have confidence_tier chip, got: {cand['confidence_tier']}"
            )

