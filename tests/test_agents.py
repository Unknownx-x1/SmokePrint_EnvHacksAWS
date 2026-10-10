"""
Smokeprint Agent and Validator Test Suite
Module: tests/test_agents.py

Tests:
  1. Validator passes on grounded tool context.
  2. Validator rejects output referencing unknown candidate IDs.
  3. Validator rejects output containing ungrounded / hallucinated numbers.
  4. Bedrock fallback mode generates certified rankings and valid trace.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.validator import validate_agent_output, extract_numbers_from_text, number_is_grounded
from agents.orchestrator import run_case_with_agents

@pytest.fixture
def mock_tool_context():
    return {
        "known_candidate_ids": [
            "osm_relation_3808258",
            "osm_way_464283160",
            "osm_way_464283162"
        ],
        "telemetry": {
            "station_pm25": 369.0,
            "station_pm10": 510.0,
            "no2_ugm3": 189.88,
            "wind_speed_ms": 2.56,
            "wind_direction_deg": 263.0
        },
        "distances": [0.86, 6.05, 6.14],
        "scores": [0.28, 0.19, 0.02, 0.38]
    }

def test_validator_accepts_grounded_output(mock_tool_context):
    valid_output = {
        "agent": "Investigator",
        "text": "Patparganj Industrial Area (osm_relation_3808258) is located 0.86 km away with score 0.28.",
        "hypotheses": [
            {"id": "osm_relation_3808258", "distance_km": 0.86, "score": 0.28}
        ]
    }
    is_valid, reasons = validate_agent_output(valid_output, mock_tool_context)
    assert is_valid, f"Expected valid output to pass, but failed with: {reasons}"
    assert len(reasons) == 0

def test_validator_rejects_unknown_suspect_id(mock_tool_context):
    invalid_output = {
        "agent": "Investigator",
        "text": "The culprit is a factory at osm_way_999999999 located 0.86 km away.",
        "hypotheses": [
            {"id": "osm_way_999999999", "distance_km": 0.86}
        ]
    }
    is_valid, reasons = validate_agent_output(invalid_output, mock_tool_context)
    assert not is_valid, "Validator should have rejected unknown suspect ID"
    assert any("unknown suspect ID" in r for r in reasons)

def test_validator_rejects_hallucinated_numbers(mock_tool_context):
    hallucinated_output = {
        "agent": "Investigator",
        "text": "Station PM2.5 jumped to 9942.5 ug/m3 and affected 450000 residents across 15.7 km.",
        "hypotheses": [
            {"id": "osm_relation_3808258", "distance_km": 0.86}
        ]
    }
    is_valid, reasons = validate_agent_output(hallucinated_output, mock_tool_context)
    assert not is_valid, "Validator should have rejected ungrounded numbers"
    assert any("numerical quantities not returned by tools" in r for r in reasons)

def test_validator_rejects_ungrounded_historical_date(mock_tool_context):
    unfounded_date_output = {
        "agent": "Critic",
        "text": "The facility at osm_way_464283160 was officially closed in 2015 and is non-operational.",
        "hypotheses": [
            {"id": "osm_way_464283160", "distance_km": 6.05}
        ]
    }
    is_valid, reasons = validate_agent_output(unfounded_date_output, mock_tool_context)
    assert not is_valid, "Validator must reject ungrounded historical year 2015"
    assert any("numerical quantities not returned by tools" in r and "2015" in r for r in reasons)

def test_validator_accepts_grounded_date_from_timestamp(mock_tool_context):
    # Context contains timestamp with year 2025
    mock_tool_context["timestamp_utc"] = "2025-11-02T21:00:00Z"
    grounded_output = {
        "agent": "Investigator",
        "text": "Event recorded in 2025 at Patparganj Industrial Area (osm_relation_3808258).",
        "hypotheses": [
            {"id": "osm_relation_3808258", "distance_km": 0.86}
        ]
    }
    is_valid, reasons = validate_agent_output(grounded_output, mock_tool_context)
    assert is_valid, f"Expected grounded year 2025 from timestamp to pass, but failed: {reasons}"

def test_validator_rejects_rajghat_ungrounded_narrative(mock_tool_context):
    mock_tool_context["osm_tags"] = "tagged disused:power=plant in OpenStreetMap"
    narrative_output = {
        "agent": "Critic",
        "text": "Rajghat was shut down in 2015 due to high pollution levels and lack of modern emissions control technology",
        "hypotheses": [
            {"id": "osm_way_464283160", "distance_km": 6.05}
        ]
    }
    is_valid, reasons = validate_agent_output(narrative_output, mock_tool_context)
    assert not is_valid, "Validator must reject ungrounded causal and historical claims"
    assert any("ungrounded" in r for r in reasons)

def test_validator_rejects_ratio_2_0(mock_tool_context):
    mock_tool_context["case_facts"] = {
        "signature": {"pm25": 369.0, "pm10": 510.0, "ratio_pm25_pm10": 0.724}
    }
    ratio_output = {
        "agent": "Critic",
        "text": "Observed PM2.5/PM10 ratio is 2.0 (impossible fine combustion).",
        "hypotheses": []
    }
    is_valid, reasons = validate_agent_output(ratio_output, mock_tool_context)
    assert not is_valid, "Validator must reject impossible PM2.5/PM10 ratio > 1.05 and mismatching canonical ratio"
    assert any("2.0 > 1.05 is physically impossible" in r or "does not equal canonical case value" in r for r in reasons)

def test_validator_rejects_verified_active(mock_tool_context):
    active_output = {
        "agent": "Critic",
        "text": "Patparganj Industrial Area (osm_relation_3808258). Operating status is 'active_presumed'. Verified active in OpenStreetMap.",
        "hypotheses": [
            {"id": "osm_relation_3808258", "distance_km": 0.86}
        ]
    }
    is_valid, reasons = validate_agent_output(active_output, mock_tool_context)
    assert not is_valid, "Validator must reject ungrounded 'Verified active' phrase"
    assert any("Verified active" in r for r in reasons)

def test_validator_rejects_old_critic_text_and_accepts_templated_critic_text(mock_tool_context):
    mock_tool_context["case_facts"] = {
        "signature": {"pm25": 369.0, "pm10": 510.0, "ratio_pm25_pm10": 0.724}
    }
    old_critic_text = (
        "Audited top suspect candidate facilities against verified tool data:\n\n"
        "2. **Chemical Signature (combustion smoke)**: Observed PM2.5/PM10 ratio is 0.82 (fine-particulate dominant (combustion-compatible ratio 0.82)).\n"
        "1. **Rajghat Thermal Power Station (osm_way_464283160)**: Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful. Tags: ['disused:power=plant'].\n"
        "1. **Patparganj Industrial Area (osm_relation_3808258)**: Operating status is 'active_presumed'. Verified active in OpenStreetMap.\n"
        "2. **Chemical Signature (combustion smoke)**: Observed PM2.5/PM10 ratio is 2.0 (fine-particulate dominant (combustion-compatible ratio 2.0)).\n\n"
        "Conclusion: Shortlist recommendations updated based strictly on verified operating status and footprint telemetry."
    )
    old_output = {
        "agent": "Critic",
        "critic_audit": old_critic_text,
        "hypotheses": [
            {"id": "osm_relation_3808258", "distance_km": 0.86},
            {"id": "osm_way_464283160", "distance_km": 6.05}
        ]
    }
    # 1. Old text must fail
    old_valid, old_reasons = validate_agent_output(old_output, mock_tool_context)
    assert not old_valid, f"Old critic text should fail validation, but passed: {old_reasons}"
    assert any("2.0 > 1.05" in r or "does not equal canonical" in r for r in old_reasons)
    assert any("Verified active" in r for r in old_reasons)

    # 2. Templated text must pass
    new_critic_text = (
        "Audited top suspect candidate facilities against verified tool data:\n\n"
        "1. **Chemical Signature**: Observed PM2.5/PM10 ratio is 0.724 (fine-particulate dominant).\n"
        "2. **Patparganj Industrial Area (osm_relation_3808258)**: Located 0.86 km upwind. Operating status is 'active_presumed (no disused/abandoned tag found in OpenStreetMap)'.\n"
        "3. **Rajghat Thermal Power Station (osm_way_464283160)**: Located 6.05 km upwind. Operating status is 'unverified_operating_status (decommissioned/disused)' (tagged disused:power=plant in OpenStreetMap, so inspection is unlikely to be useful).\n\n"
        "Conclusion: Shortlist recommendations updated based strictly on verified operating status and footprint telemetry."
    )
    mock_tool_context["osm_tags"] = "tagged disused:power=plant in OpenStreetMap"
    new_output = {
        "agent": "Critic",
        "critic_audit": new_critic_text,
        "hypotheses": [
            {"id": "osm_relation_3808258", "distance_km": 0.86},
            {"id": "osm_way_464283160", "distance_km": 6.05}
        ]
    }
    new_valid, new_reasons = validate_agent_output(new_output, mock_tool_context)
    assert new_valid, f"New templated critic text must pass validation, but failed: {new_reasons}"

def test_orchestrator_bedrock_fallback_execution():
    result = run_case_with_agents("case_anand_vihar_20251102", force_fallback=True)
    assert result["validator_passed"] is True
    assert result["ranking_changed_by_critic"] is True
    assert result["final_certified_rankings"][0]["name"] == "Patparganj Industrial Area Cluster"
    assert "osm_relation_3808258" in result["final_certified_rankings"][0]["member_candidate_ids"]
    assert os.path.exists("docs/agent_critic_trace.md")


