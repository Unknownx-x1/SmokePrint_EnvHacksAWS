"""
Smokeprint Test: Single Source of Truth & Numeric Grounding
File: tests/test_single_source_of_truth.py

Ensures that every number and physical attribute presented by the agents (Investigator,
Critic) or the generated shortlist markdown is strictly read from and matches the
canonical case JSON (data/cases_out/{case_id}.json). Fails if any displayed number
differs from that canonical JSON.
"""

import os
import sys
import json
import re
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.orchestrator import run_case_with_agents
from scripts.generate_shortlist_markdown import generate_shortlist_markdown

def test_canonical_case_json_consistency():
    canonical_file = "data/cases_out/case_anand_vihar_20251102.json"
    assert os.path.exists(canonical_file), f"Canonical case JSON missing: {canonical_file}"

    with open(canonical_file, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    # 1. Assert telemetry and baseline numbers
    assert case_data["signature"]["pm25"] == 400.0
    assert case_data["signature"]["pm10"] == 536.0
    assert case_data["regional_median"] == 148.0
    assert case_data["local_excess"] == 252.0

    # 2. Assert wind parameters
    assert "wind" in case_data
    assert case_data["wind"]["wind_speed_ms"] == 2.44
    assert case_data["wind"]["wind_direction_deg"] == 268.0
    assert "wind from" in case_data["wind"]["wording"].lower()

    # 3. Assert geometry facts
    geom = case_data["geometry_facts"]
    assert geom["vivek_vihar"]["distance_km"] == 2.84
    assert geom["vivek_vihar"]["bearing_deg"] == 358.5
    assert geom["vivek_vihar"]["pm25"] == 421.0
    assert geom["vivek_vihar"]["excess"] == 273.0

    assert geom["patparganj"]["centroid_distance_km"] == 0.86
    assert geom["patparganj"]["centroid_bearing_deg"] == 218.9
    assert geom["patparganj"]["nearest_boundary_distance_km"] == 0.23
    assert geom["patparganj"]["nearest_boundary_bearing_deg"] == 178.0

    assert geom["rajghat"]["distance_km"] == 6.05
    assert geom["rajghat"]["bearing_deg"] == 260.2

    assert geom["ghazipur"]["distance_km"] == 2.77
    assert geom["ghazipur"]["bearing_deg"] == 156.3

def test_agent_outputs_match_canonical_case_json():
    canonical_file = "data/cases_out/case_anand_vihar_20251102.json"
    with open(canonical_file, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    result = run_case_with_agents("case_anand_vihar_20251102", force_fallback=True)
    critic_output = result["critic_output"]
    falsification_text = critic_output["falsification_summary"]

    # Assert correct numbers in Critic summary
    assert "400.0" in falsification_text or "400" in falsification_text
    assert "421.0" in falsification_text
    assert "273.0" in falsification_text
    assert "2.84" in falsification_text
    assert "358.5" in falsification_text
    assert "0.86" in falsification_text
    assert "218.9" in falsification_text
    assert "0.23" in falsification_text or "230.0" in falsification_text
    assert "6.05" in falsification_text
    assert "260.2" in falsification_text

    # Assert no obsolete/erroneous values appear in Critic summary
    assert "468" not in falsification_text, "Found discredited 468 peak in Critic output"
    assert "320.0 ug/m3" not in falsification_text, "Found discredited 320 excess in Critic output"
    assert "1.8 km NE" not in falsification_text, "Found ungrounded 1.8 km NE in Critic output"
    assert "268.2" not in falsification_text, "Found inaccurate 268.2 bearing in Critic output"
    assert "blowing from east" not in falsification_text.lower(), "Found non-meteorological wind wording"

    # Assert confidence tiers only (never calibrated probabilities in user-facing adjusted clusters)
    for cl in critic_output.get("adjusted_clusters", []):
        assert cl["confidence_tier"] in ["high", "medium", "low"], "Tier must be high, medium, or low"
        assert "calibrated_probability" not in cl, "Calibrated probability must not be shown"

def test_programmatic_shortlist_markdown():
    canonical_file = "data/cases_out/case_anand_vihar_20251102.json"
    target_md = "docs/case_anand_vihar_20251102_shortlist.md"

    generate_shortlist_markdown(canonical_file, target_md)
    with open(target_md, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Verify that correct numbers from canonical JSON are rendered
    assert "400.0" in md_text
    assert "252.0" in md_text
    assert "2.44" in md_text
    assert "wind from 268" in md_text.lower()
    assert "2.84 km" in md_text
    assert "multiple comparable candidates" in md_text.lower()

    # Verify no raw calibrated probabilities are shown as confidence
    assert not re.search(r"confidence:\s*0\.\d{2,}", md_text, re.IGNORECASE)
