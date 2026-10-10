"""
Smokeprint Phase 5.3 Audit Tests
File: tests/test_audit_phase53.py

Tests:
  (a) Critic text for each case names only candidates present in that case's shortlist
  (b) "upwind" never appears when offset > 45
  (c) Each case's stored wind equals the ERA5 row at its own timestamp
  (d) Low-wind cases contain no rank numbers
"""

import os
import sys
import re
import json
import glob
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.shortlist_builder import build_enriched_shortlist

ALL_7_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112"
]

def load_canonical_case(case_id: str):
    path = f"data/cases_out/{case_id}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_agent_trace(case_id: str):
    path = f"data/agent_traces/{case_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_a_critic_names_only_shortlist_candidates():
    """Fail the audit if Critic names a candidate not in that case's shortlist."""
    for case_id in ALL_7_CASES:
        trace = load_agent_trace(case_id)
        if not trace:
            continue
        cdata = load_canonical_case(case_id)
        enriched = build_enriched_shortlist(cdata)
        shortlist_ids = {c["id"] for c in enriched.get("shortlist", []) if not c["id"].startswith("outcome_")}

        # Get critic text
        critic_text = ""
        for attempt in trace.get("attempts", []):
            critic_text += " " + attempt.get("critic_response", "")

        # Look for osm candidate IDs
        found_ids = set(re.findall(r'\b(osm_(?:relation|way|node)_\d+)\b', critic_text))
        
        # All found candidate IDs in Critic text must be in that case's shortlist
        unlisted = found_ids - shortlist_ids
        assert not unlisted, (
            f"[{case_id}] Critic text names candidates not in case shortlist: {unlisted}. "
            f"Case shortlist IDs: {shortlist_ids}"
        )

def test_b_upwind_wording_never_appears_when_offset_greater_than_45():
    """'upwind' must only be used when angular offset <= 45 deg; otherwise 'off the main wind line'."""
    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        enriched = build_enriched_shortlist(cdata)
        
        for cand in enriched.get("shortlist", []):
            offset = cand.get("angular_offset_deg")
            reasons = cand.get("reasons", [])
            for r in reasons:
                if offset is not None and offset > 45.0:
                    assert "upwind" not in r.lower(), (
                        f"[{case_id}] Candidate {cand['id']} has offset {offset:.1f}° > 45° but reason uses 'upwind': '{r}'"
                    )

def test_c_case_wind_equals_era5_row_at_own_timestamp():
    """Each case's stored wind must equal the ERA5 row at its own timestamp."""
    with open("data/wind_hourly_12m.json", "r", encoding="utf-8") as f:
        era5 = {r["time"]: r for r in json.load(f)["records"]}

    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        tw = cdata.get("time_window", {})
        m_utc = tw.get("interval_midpoint_utc")
        assert m_utc, f"[{case_id}] Missing interval_midpoint_utc"
        
        era5_key = m_utc[:13] + ":00"
        era5_row = era5.get(era5_key)
        assert era5_row, f"[{case_id}] No ERA5 record for {era5_key}"

        w = cdata.get("wind", {})
        assert w.get("wind_speed_ms") == pytest.approx(era5_row["wind_speed_ms"], rel=1e-3), (
            f"[{case_id}] Wind speed mismatch: stored={w.get('wind_speed_ms')} vs ERA5={era5_row['wind_speed_ms']}"
        )
        assert w.get("wind_direction_deg") == pytest.approx(era5_row["wind_direction_deg"], rel=1e-3), (
            f"[{case_id}] Wind direction mismatch: stored={w.get('wind_direction_deg')} vs ERA5={era5_row['wind_direction_deg']}"
        )

def test_d_low_wind_cases_contain_no_rank_numbers():
    """Low-wind cases (< 1.5 m/s) contain no rank numbers ('#1', '1.', 'Rank 1')."""
    for case_id in ALL_7_CASES:
        cdata = load_canonical_case(case_id)
        w = cdata.get("wind", {})
        ws = w.get("wind_speed_ms", 2.56)
        if ws < 1.5:
            trace = load_agent_trace(case_id)
            if trace:
                for attempt in trace.get("attempts", []):
                    c_resp = attempt.get("critic_response", "")
                    assert not re.search(r'\b[1-9]\.\s+\*\*', c_resp), (
                        f"[{case_id}] Low-wind critic response contains numbered ranking: {c_resp}"
                    )
                    assert "#1" not in c_resp and "Rank 1" not in c_resp, (
                        f"[{case_id}] Low-wind critic response contains rank wording"
                    )
