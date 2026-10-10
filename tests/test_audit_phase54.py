"""
Smokeprint Test: Phase 5.4 Candidate Provenance, Non-Site Outcomes, and Wording Rules
File: tests/test_audit_phase54.py
"""

import os
import json
import pytest

ALL_7_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_rkpuram_20251112",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
]

def load_canonical_case(case_id: str):
    path = os.path.join("data", "cases_out", f"{case_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_osm_catalog():
    path = os.path.join("data", "osm_candidates.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_every_displayed_candidate_centroid_equals_osm_catalog_value():
    osm_catalog = load_osm_catalog()
    osm_by_id = {c["id"]: c for c in osm_catalog}

    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        shortlist = cdata.get("shortlist", [])

        for cand in shortlist:
            cid = cand["id"]
            assert cid in osm_by_id, f"Candidate {cid} in {case_id} not found in osm_candidates.json"
            osm_entry = osm_by_id[cid]

            cand_lat = cand["lat"]
            cand_lon = cand["lon"]
            osm_lat = osm_entry["lat"]
            osm_lon = osm_entry["lon"]

            assert abs(cand_lat - osm_lat) < 1e-6, (
                f"Latitude mismatch for {cid} in {case_id}: {cand_lat} vs {osm_lat}"
            )
            assert abs(cand_lon - osm_lon) < 1e-6, (
                f"Longitude mismatch for {cid} in {case_id}: {cand_lon} vs {osm_lon}"
            )

            # Precision check: verify high-precision coordinates (not round numbers)
            lat_str = str(cand_lat).rstrip("0")
            lon_str = str(cand_lon).rstrip("0")
            lat_dec = len(lat_str.split(".")[1]) if "." in lat_str else 0
            lon_dec = len(lon_str.split(".")[1]) if "." in lon_str else 0
            assert lat_dec >= 4, f"Coordinate {cand_lat} for {cid} has low precision ({lat_dec} decimals)"
            assert lon_dec >= 4, f"Coordinate {cand_lon} for {cid} has low precision ({lon_dec} decimals)"

def test_non_site_outcomes_separated_from_shortlist():
    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        shortlist = cdata.get("shortlist", [])

        # Non-site outcome IDs must NOT be in shortlist
        for cand in shortlist:
            assert not cand["id"].startswith("outcome_"), (
                f"Non-site outcome {cand['id']} present in shortlist for {case_id}"
            )
            assert cand.get("confidence_tier") in ["high", "medium", "low", None]

        # Other explanations considered block must exist
        others = cdata.get("other_explanations_considered", [])
        assert isinstance(others, list)
        assert len(others) >= 2, f"Expected other explanations for {case_id}, got {len(others)}"

        for expl in others:
            assert expl["id"].startswith("outcome_")
            assert "deterministic_reason" in expl
            assert "sentence" in expl
            assert len(expl["sentence"].split(".")) >= 1

def test_transport_wording_3_tier_thresholds():
    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        shortlist = cdata.get("shortlist", [])

        for cand in shortlist:
            offset = cand.get("angular_offset_deg")
            reasons = cand.get("reasons", [])
            if offset is not None and reasons:
                geom_reason = reasons[0]
                if offset <= 25.0:
                    assert "upwind" in geom_reason
                elif 25.0 < offset <= 45.0:
                    assert "somewhat off the wind line" in geom_reason
                else:
                    assert "off the main wind line" in geom_reason

def test_low_wind_cases_exact_count():
    low_wind_cases = []
    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        if cdata.get("wind", {}).get("is_low_wind") or cdata.get("wind", {}).get("wind_speed_ms", 99) < 1.5:
            low_wind_cases.append(case_id)

    expected_low_wind = [
        "case_anand_vihar_20260131",
        "case_anand_vihar_20260405",
        "case_crri_20260515",
        "case_regional_smog_20251020",
        "case_rkpuram_20251112"
    ]
    assert sorted(low_wind_cases) == sorted(expected_low_wind)
    assert len(low_wind_cases) == 5
