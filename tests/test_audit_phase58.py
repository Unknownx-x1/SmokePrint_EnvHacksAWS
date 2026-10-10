"""
SmokePrint Phase 5.8 Reconciliation & Final Freeze Tests
File: tests/test_audit_phase58.py

Tests:
1. Every plotted point in hourly_series equals a raw OpenAQ row (sensor id + timestamp + value).
2. For every visible single-station case, the chart peak equals the telemetry card's peak.
3. April case has hidden_from_demo: true and is excluded from ALL_CASE_IDS in offline copy.
4. Regional smog case max station is QC-clean Sector-125 Noida (881.0 ug/m3).
5. All candidates with angular offset > 90 deg have 'downwind' label.
6. Across the 6 visible cases, 0 candidates exceed 90 deg offset.
"""

import os
import json
import pytest

VISIBLE_CASE_IDS = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_rkpuram_20251112",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020"
]

def test_raw_openaq_reconciliation_every_plotted_point():
    """Verify that every plotted point in hourly_series matches a raw OpenAQ row in station data."""
    for cid in VISIBLE_CASE_IDS:
        cpath = f"data/cases_out/{cid}.json"
        with open(cpath, "r", encoding="utf-8") as f:
            c = json.load(f)

        hs = c.get("hourly_series")
        if not hs:
            # Regional smog has no single-station hourly series
            assert cid == "case_regional_smog_20251020"
            continue

        sid = hs["station_id"]
        sensor_id = hs["sensor_id"]
        source_file = f"data/stations_12m/station_{sid}_12m.json"
        assert os.path.exists(source_file), f"Source file {source_file} missing"

        with open(source_file, "r", encoding="utf-8") as sf:
            raw_station = json.load(sf)

        assert raw_station["sensors"]["pm25"] == sensor_id
        raw_pm25 = raw_station["data"]["pm25"]

        # Check every plotted reading
        readings = hs["readings"]
        assert len(readings) == 5, f"Expected 5 continuous readings in {cid}"
        for r in readings:
            ts_utc = r["timestamp_utc"]
            val = r["pm25_ugm3"]
            if val is not None:
                assert ts_utc in raw_pm25, f"Timestamp {ts_utc} not in raw station data"
                assert raw_pm25[ts_utc] == val, f"Value mismatch at {ts_utc}: plotted {val} vs raw {raw_pm25[ts_utc]}"

def test_chart_peak_equals_telemetry_card_peak():
    """Verify that for every visible single-station case, the chart peak equals the telemetry card peak."""
    for cid in VISIBLE_CASE_IDS:
        cpath = f"data/cases_out/{cid}.json"
        with open(cpath, "r", encoding="utf-8") as f:
            c = json.load(f)

        hs = c.get("hourly_series")
        if not hs:
            continue

        plotted_values = [r["pm25_ugm3"] for r in hs["readings"] if r["pm25_ugm3"] is not None]
        assert plotted_values, f"No valid values in hourly_series for {cid}"
        chart_peak = max(plotted_values)

        # Telemetry card value is in signature.pm25
        card_pm25 = c.get("signature", {}).get("pm25")
        assert card_pm25 is not None, f"Missing signature.pm25 in {cid}"
        assert chart_peak == card_pm25, (
            f"[{cid}] Chart peak ({chart_peak}) does not equal telemetry card peak ({card_pm25})"
        )

def test_april_case_hidden_from_demo():
    """Verify April case is hidden from demo in canonical output and excluded from offline bundle."""
    # 1. Canonical file in repo
    cpath = "data/cases_out/case_anand_vihar_20260405.json"
    assert os.path.exists(cpath), "April case file should remain in repo"
    with open(cpath, "r", encoding="utf-8") as f:
        c = json.load(f)
    assert c.get("hidden_from_demo") is True, "April case must have hidden_from_demo: true"

    # 2. Offline bundle
    with open("web/src/lib/offlineData.ts", "r", encoding="utf-8") as f:
        content = f.read()

    assert "case_anand_vihar_20260405" not in content, "April case must NOT be in offlineData.ts"

    # Check ALL_CASE_IDS has exactly 6 cases
    import re
    match = re.search(r'export const ALL_CASE_IDS = (\[.*?\]);', content, re.DOTALL)
    assert match, "Could not find ALL_CASE_IDS in offlineData.ts"
    case_ids = json.loads(match.group(1))
    assert len(case_ids) == 6
    assert set(case_ids) == set(VISIBLE_CASE_IDS)

def test_regional_case_qc_clean_highest_station():
    """Verify regional smog case uses the highest QC-clean station (Sector 125 Noida, 881.0 ug/m3)."""
    cpath = "data/cases_out/case_regional_smog_20251020.json"
    with open(cpath, "r", encoding="utf-8") as f:
        c = json.load(f)

    summary = c.get("regional_smog_summary", {})
    assert summary.get("max_station_name") == "Sector - 125, Noida, UP - UPPCB"
    assert summary.get("max_station_pm25") == 881.0
    assert summary.get("network_median_pm25") == 678.0
    assert summary.get("reporting_stations") == 22
    assert summary.get("stations_over_200") == 21
    assert summary.get("elevated_pct") == 95.5

def test_offset_labels_downwind_rule():
    """Verify candidates with angular offset > 90 deg are labeled 'downwind', and 0 in visible cases."""
    # In the hidden April case, candidate osm_way_1498754706 has offset 108.4 deg and is labeled downwind
    with open("data/cases_out/case_anand_vihar_20260405.json", "r", encoding="utf-8") as f:
        c_apr = json.load(f)
    downwind_cands = [cand for cand in c_apr.get("shortlist", []) if cand.get("angular_offset_deg", 0) > 90.0]
    assert len(downwind_cands) == 1
    assert downwind_cands[0]["angular_offset_deg"] == 108.4
    assert any("downwind" in r.lower() for r in downwind_cands[0]["reasons"])

    # Across all 6 visible cases, 0 candidates should exceed 90 deg offset
    for cid in VISIBLE_CASE_IDS:
        cpath = f"data/cases_out/{cid}.json"
        with open(cpath, "r", encoding="utf-8") as f:
            c = json.load(f)
        for cand in c.get("shortlist", []):
            offset = cand.get("angular_offset_deg")
            assert offset is not None
            assert offset <= 90.0, f"Candidate {cand['id']} in {cid} has offset {offset} > 90 deg"
