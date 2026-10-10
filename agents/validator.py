"""
Smokeprint Agent Output Validator
Module: agents/validator.py

Strict validation barrier ensuring zero hallucination:
  1. Candidate ID Integrity: Rejects any output referencing unknown suspect IDs
     not present in the candidate catalog or tool output.
  2. Number Hallucination Barrier: Rejects any output containing numerical quantities
     (concentrations, distances, angles, scores, ratios) not returned by tools.
  3. Structural Schema Validation: Enforces required fields in agent briefs.
"""

import re
import math
from typing import Dict, Any, List, Tuple, Set, Optional

# Regular expression to extract numbers from natural language text
# Matches integers, decimals, percentages, scientific notation
NUMBER_REGEX = re.compile(r'(?<![a-zA-Z_\-])[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?%?')

# Regular expression to extract candidate IDs like 'osm_node_123', 'osm_way_456', 'osm_relation_789'
CANDIDATE_ID_REGEX = re.compile(r'\b(osm_(?:node|way|relation)_\d+)\b')

# Regular expression to extract list item bullets at line starts (e.g. '1. ', '2. ')
LIST_BULLET_REGEX = re.compile(r'(?:^|\n)\s*(\d+)\.\s+')

# Regular expression to strip pollutant names (PM2.5, PM10, NO2, CO, etc.) so their name digits are not extracted as quantities
POLLUTANT_REGEX = re.compile(r'\b(?:PM2\.5|PM10|NO2|CO|SO2|O3)\b', re.IGNORECASE)

def extract_numbers_from_text(text: str) -> List[float]:
    """Extracts all numeric quantities from text, stripping candidate IDs, pollutant labels, and list bullets."""
    # Strip candidate IDs so OSM entity IDs are not parsed as quantities
    sanitized = CANDIDATE_ID_REGEX.sub(' ', text)
    # Strip pollutant names like PM2.5, PM10 so name digits are not extracted as quantities
    sanitized = POLLUTANT_REGEX.sub(' ', sanitized)
    # Strip markdown list bullet numbers at start of lines (e.g. '1. ', '2. ') so they are not parsed as quantities
    sanitized = LIST_BULLET_REGEX.sub(r'\n', sanitized)
    numbers = []
    tokens = NUMBER_REGEX.findall(sanitized)
    for tok in tokens:
        clean = tok.rstrip('%').strip()
        if not clean or clean in ['.', '-', '+']:
            continue
        try:
            val = float(clean)
            numbers.append(val)
        except ValueError:
            continue
    return numbers

def extract_numbers_from_dict(d: Any) -> Set[float]:
    """Recursively collects all floating-point and integer numbers from a tool result dictionary."""
    num_set = set()
    if isinstance(d, (int, float)) and not isinstance(d, bool):
        num_set.add(round(float(d), 4))
    elif isinstance(d, str):
        # Extract numbers, years, and dates present in tool string fields (e.g. timestamps, tags)
        for num in extract_numbers_from_text(d):
            num_set.add(round(num, 4))
    elif isinstance(d, dict):
        for k, v in d.items():
            num_set.update(extract_numbers_from_dict(v))
    elif isinstance(d, list):
        for item in d:
            num_set.update(extract_numbers_from_dict(item))
    return num_set

def number_is_grounded(num: float, allowed_numbers: Set[float], tolerance: float = 0.05) -> bool:
    """
    Checks if a number is grounded in the tool context within relative or absolute tolerance.
    Also handles percentage representations (e.g. 0.25 vs 25%).
    Never whitelists calendar years or factual claims unless returned in tool fields.
    """
    # Only allow rank ordinals (1, 2, 3, 4, 5) if they match allowed numbers
    # (Do NOT unconditionally whitelist arbitrary floats like 2.0 or 0.0)
    for allowed in allowed_numbers:
        # Direct absolute tolerance
        if abs(num - allowed) <= tolerance:
            return True
        # Relative tolerance (5%)
        if allowed != 0 and abs(num - allowed) / abs(allowed) <= 0.05:
            return True
        # Percentage scaling (e.g., 0.25 vs 25.0)
        if abs(num - allowed * 100.0) <= 0.5 or (allowed != 0 and abs(num - allowed * 100.0) / (allowed * 100.0) <= 0.05):
            return True
        if abs(num * 100.0 - allowed) <= 0.5 or (allowed != 0 and abs(num * 100.0 - allowed) / allowed <= 0.05):
            return True

    return False

def validate_agent_output(
    agent_output: Dict[str, Any],
    tool_context: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validates agent output against tool context.
    
    Returns:
      (is_valid: bool, rejection_reasons: List[str])
    """
    rejection_reasons = []

    # 1. Allowed Suspect IDs
    known_ids: Set[str] = set(tool_context.get("known_candidate_ids", []))
    if "hypotheses" in tool_context:
        for h in tool_context["hypotheses"]:
            if "id" in h:
                known_ids.add(h["id"])
    if "candidate_catalog" in tool_context:
        for c in tool_context["candidate_catalog"]:
            if "id" in c:
                known_ids.add(c["id"])

    # Add standard non-site IDs
    known_ids.update([
        "outcome_possible_fault",
        "outcome_regional",
        "outcome_insufficient_evidence"
    ])

    # 2. Extract referenced IDs in output
    text_corpus = ""
    referenced_ids = set()

    # Check structured hypotheses list in agent output
    output_hyps = agent_output.get("ranked_hypotheses", agent_output.get("hypotheses", []))
    for h in output_hyps:
        if isinstance(h, dict) and "id" in h:
            referenced_ids.add(h["id"])

    # Extract any IDs embedded in text / reasoning strings
    def collect_text(obj: Any):
        nonlocal text_corpus
        if isinstance(obj, str):
            text_corpus += " " + obj
        elif isinstance(obj, dict):
            for v in obj.values():
                collect_text(v)
        elif isinstance(obj, list):
            for item in obj:
                collect_text(item)

    collect_text(agent_output)

    text_ids = set(CANDIDATE_ID_REGEX.findall(text_corpus))
    referenced_ids.update(text_ids)

    # Check for unknown IDs
    unknown_ids = referenced_ids - known_ids
    if unknown_ids:
        rejection_reasons.append(
            f"REJECTED: Output references unknown suspect ID(s) not in tool results: {sorted(list(unknown_ids))}"
        )

    # 3. Numeric Grounding Verification
    allowed_numbers = extract_numbers_from_dict(tool_context)
    output_numbers = extract_numbers_from_text(text_corpus)

    unrounded_numbers = []
    for num in output_numbers:
        if not number_is_grounded(num, allowed_numbers):
            unrounded_numbers.append(num)

    if unrounded_numbers:
        # Cap report to first 5 ungrounded numbers
        rejection_reasons.append(
            f"REJECTED: Output contains numerical quantities not returned by tools: {unrounded_numbers[:5]}"
        )

    # 4. Domain Validation: PM2.5/PM10 Ratio Constraints (<= 1.05 and must equal case JSON value)
    ratio_matches = list(re.finditer(
        r'(?:pm2\.5[ /_]pm10\s*ratio|pm2\.5\s*to\s*pm10\s*ratio|ratio\s*(?:is|=|:)?)\s*([0-9]*\.?[0-9]+)',
        text_corpus,
        re.IGNORECASE
    ))
    
    # Extract canonical ratio from case JSON or telemetry
    canonical_ratio = None
    case_facts = tool_context.get("case_facts", {})
    sig_facts = case_facts.get("signature", {})
    if sig_facts.get("ratio_pm25_pm10") is not None:
        canonical_ratio = float(sig_facts["ratio_pm25_pm10"])
    elif sig_facts.get("pm25") and sig_facts.get("pm10"):
        canonical_ratio = round(float(sig_facts["pm25"]) / float(sig_facts["pm10"]), 3)
    elif tool_context.get("telemetry", {}).get("station_pm25") and tool_context.get("telemetry", {}).get("station_pm10"):
        t_pm25 = float(tool_context["telemetry"]["station_pm25"])
        t_pm10 = float(tool_context["telemetry"]["station_pm10"])
        canonical_ratio = round(t_pm25 / t_pm10, 3)

    for rm in ratio_matches:
        try:
            r_val = float(rm.group(1))
            # Rule 1: Ratio must be <= 1.05
            if r_val > 1.05:
                rejection_reasons.append(
                    f"REJECTED: PM2.5/PM10 ratio {r_val} > 1.05 is physically impossible (must be <= 1.05)"
                )
            # Rule 2: Ratio must equal canonical case value
            if canonical_ratio is not None and abs(r_val - canonical_ratio) > 0.03:
                rejection_reasons.append(
                    f"REJECTED: Cited PM2.5/PM10 ratio {r_val} does not equal canonical case value {canonical_ratio}"
                )
        except ValueError:
            pass

    # 5. Operating Status Grounding & Prohibited Phrases
    if "verified active" in text_corpus.lower():
        rejection_reasons.append(
            "REJECTED: Output contains ungrounded status phrase 'Verified active' (must use exact operating_status text e.g. 'active_presumed (no disused/abandoned tag found in OpenStreetMap)')"
        )

    # 4. Facility Historical & Causal Narrative Grounding Verification
    # Rejects ungrounded closure years, historical events, or facility-specific causes
    # (e.g. 'shut down in 2015 due to high pollution levels and lack of modern emissions control technology')
    tool_text_corpus = ""
    def collect_tool_text(obj: Any):
        nonlocal tool_text_corpus
        if isinstance(obj, str):
            tool_text_corpus += " " + obj.lower()
        elif isinstance(obj, dict):
            for v in obj.values():
                collect_tool_text(v)
        elif isinstance(obj, list):
            for item in obj:
                collect_tool_text(item)

    collect_tool_text(tool_context)

    # Detect facility closure / operation causal narrative clauses
    facility_cause_matches = re.finditer(
        r'\b(?:shut down|closed|decommissioned|operated|demolished)\b[^.,;\n]*?\b(?:in|due to|because of|owing to)\b([^.,;\n]*)',
        text_corpus,
        re.IGNORECASE
    )
    for fm in facility_cause_matches:
        clause_text = fm.group(0).strip()
        cause_body = fm.group(1).strip().lower()

        cause_words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', cause_body)
                       if w not in ["that", "this", "from", "with", "have", "been", "were", "what", "which", "will", "would", "being", "their", "there"]]
        ungrounded = [w for w in cause_words if w not in tool_text_corpus]
        if ungrounded:
            rejection_reasons.append(
                f"REJECTED: Output contains ungrounded facility closure/historical cause not returned by tools: '{clause_text}' (ungrounded terms: {ungrounded})"
            )
            break

    # Detect historical year assertions (19xx, 20xx) linked to shutdown / closure claims
    history_matches = re.finditer(
        r'\b(?:shut down|closed|decommissioned|built|founded|established)\b[^.,;\n]*?\b(19\d\d|20[0-2]\d)\b',
        text_corpus,
        re.IGNORECASE
    )
    for hm in history_matches:
        hist_claim = hm.group(0).strip()
        year_str = re.search(r'\b(19\d\d|20[0-2]\d)\b', hist_claim).group(1)
        if year_str not in tool_text_corpus or ("closed_date" not in tool_text_corpus and "closure_year" not in tool_text_corpus):
            rejection_reasons.append(
                f"REJECTED: Output contains ungrounded historical closure/event year claim not returned in tool fields: '{hist_claim}'"
            )
            break

    is_valid = len(rejection_reasons) == 0
    return is_valid, rejection_reasons
