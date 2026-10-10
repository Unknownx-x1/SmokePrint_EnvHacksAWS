"""
Smokeprint Critic Agent
Module: agents/critic.py

The Critic agent attempts to falsify top suspect candidates by auditing:
  1. Operating status (checking OSM lifecycle tags: disused, abandoned, demolished).
  2. Chemical signature mismatch (fine soot vs coarse mechanical dust).
  3. Downwind station response coherence.
  4. Intra-estate spatial clustering and competing active facilities.
Built with the Strands Agents SDK.
"""

import os
import sys
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strands import Agent
from agents.tools import (
    check_site_operating_history,
    check_chemical_plume_coherence,
    run_plume_trajectory
)

CRITIC_SYSTEM_PROMPT = """
You are the Smokeprint Adversarial Critic Agent.
Your responsibility is to challenge and falsify the top suspect candidates proposed by the Investigator.
For every top candidate:
  1. Call check_site_operating_history(candidate_id) to verify if the facility is active or decommissioned/disused.
  2. Call check_chemical_plume_coherence(...) to check if observed PM2.5/PM10 ratio matches the candidate type.
  3. If you find a decommissioned site (e.g. disused power plant), coarse dust contradiction, or better active alternative:
     - Formulate explicit objections.
     - Apply confidence penalties.
     - Recommend a revised top rank promoting active, physically corroborated facilities.

CRITICAL CONSTRAINTS:
- NEVER hallucinate suspect IDs. You may ONLY cite IDs returned by tools.
- NEVER invent numbers, distances, or scores. Cite ONLY values returned by tools.
- Deliver structured critique and revised ranking recommendations.
"""

def create_critic_agent(model: Optional[Any] = None) -> Agent:
    """Instantiates the Strands Critic Agent with audit tool suite."""
    tools = [
        check_site_operating_history,
        check_chemical_plume_coherence,
        run_plume_trajectory
    ]
    return Agent(
        name="Critic",
        model=model,
        tools=tools,
        system_prompt=CRITIC_SYSTEM_PROMPT
    )
