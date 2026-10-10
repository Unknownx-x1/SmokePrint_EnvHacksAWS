"""
Smokeprint Investigator Agent
Module: agents/investigator.py

The Investigator agent orchestrates case investigation by querying station telemetry,
initiating backward atmospheric dispersion, and assembling initial candidate hypotheses.
Built with the Strands Agents SDK.
"""

import os
import sys
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strands import Agent
from agents.tools import (
    get_case_telemetry,
    run_plume_trajectory,
    compute_initial_rankings,
    check_chemical_plume_coherence
)

INVESTIGATOR_SYSTEM_PROMPT = """
You are the Smokeprint Lead Investigator Agent.
Your role is to investigate local air quality spikes at monitoring stations across Delhi-NCR.
You must strictly query deterministic tools to obtain ground truth:
  1. Retrieve case telemetry with get_case_telemetry(case_id).
  2. Simulate the atmospheric transport plume with run_plume_trajectory(...).
  3. Retrieve initial Bayesian rankings with compute_initial_rankings(case_id).
  4. Verify chemical plume coherence with check_chemical_plume_coherence(...).

CRITICAL CONSTRAINTS:
- NEVER hallucinate suspect IDs. You may ONLY cite IDs returned by tools (e.g. 'osm_way_123', 'osm_relation_456').
- NEVER invent numbers, concentrations, distances, or scores. Cite ONLY values returned by tools.
- Output your initial investigation brief summarizing the event, the upwind transport corridor, and the top candidate suspects.
"""

def create_investigator_agent(model: Optional[Any] = None) -> Agent:
    """Instantiates the Strands Investigator Agent with tool suite."""
    tools = [
        get_case_telemetry,
        run_plume_trajectory,
        compute_initial_rankings,
        check_chemical_plume_coherence
    ]
    return Agent(
        name="Investigator",
        model=model,
        tools=tools,
        system_prompt=INVESTIGATOR_SYSTEM_PROMPT
    )
