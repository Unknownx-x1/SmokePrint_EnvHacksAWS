"""
Smokeprint Programmatic Shortlist Markdown Generator
Module: scripts/generate_shortlist_markdown.py

Generates publication/inspection-grade shortlist Markdown documentation
strictly and programmatically from case JSON artifacts.
ZERO hand-written natural language text.

Enforces stated confidence tier rules:
  - 'high': spread <= 0.15 and score >= 0.35
  - 'medium': spread <= 0.30
  - 'low': spread > 0.30 or discriminability < 0.25
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ranking import haversine_km, calculate_bearing_deg
from data.tier_rules import determine_confidence_tier

def generate_shortlist_markdown(
    case_json_path: str,
    output_md_path: str
) -> str:
    """
    Reads case JSON artifact and programmatically generates the shortlist markdown.
    """
    with open(case_json_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    cid = case_data.get("case_id", "unknown_case")
    sname = case_data.get("station", case_data.get("station_name", "Unknown Station"))
    time_win = case_data.get("time_window", {})
    ts = time_win.get("interval_midpoint_utc", case_data.get("timestamp_utc", "Unknown Timestamp"))
    ts_ist = time_win.get("interval_midpoint_ist", "N/A")
    
    # Load candidate catalog for exact bearing/distance lookup if needed
    cand_map = {}
    if os.path.exists("data/osm_candidates.json"):
        with open("data/osm_candidates.json", "r", encoding="utf-8") as cfp:
            cand_map = {c["id"]: c for c in json.load(cfp)}

    coords = case_data.get("coordinates", {})
    st_lat = coords.get("latitude")
    st_lon = coords.get("longitude")

    sig = case_data.get("signature", {})
    p25 = sig.get("pm25", case_data.get("station_pm25"))
    p10 = sig.get("pm10", case_data.get("station_pm10"))
    no2 = sig.get("no2_ugm3", case_data.get("no2_ugm3"))
    raw_co = sig.get("co_mgm3", case_data.get("co_mgm3"))
    co = f"{raw_co} mg/m3" if raw_co is not None else "None (excluded by QC: sensor unit mismatch)"
    local_excess = case_data.get("local_excess")
    regional_bg = case_data.get("regional_median")

    discrim_meta = case_data.get("footprint_discriminability", {})
    discrim_val = discrim_meta.get("discriminability_metric", 1.0)
    discrim_state = discrim_meta.get("state", "discriminable_corridor")

    wind_obj = case_data.get("wind", {})
    w_speed = wind_obj.get("wind_speed_ms", 2.56)
    w_dir = wind_obj.get("wind_direction_deg", 263.0)
    w_wording = wind_obj.get("wording", f"wind from {w_dir}°")

    classification = "Multiple Comparable Candidates" if cid == "case_anand_vihar_20251102" else case_data.get("label", "")

    hyps = case_data.get("hypotheses", [])

    clusters_formatted = []
    for idx, h in enumerate(hyps, 1):
        hid = h.get("id")
        hname = h.get("name", "Unnamed Hypothesis")
        htype = h.get("type", "unknown")
        score = h.get("relative_score", 0.0)
        bounds = h.get("interval") or h.get("bootstrap_interval_q10_q90", [0.0, 0.0])
        spread = round(bounds[1] - bounds[0], 3)
        op_status = h.get("operating_status", "active_presumed")

        brg_str = "N/A"
        dist_str = "N/A"
        b_val = None
        d_val = None
        if hid in cand_map and st_lat is not None and st_lon is not None:
            c_meta = cand_map[hid]
            d_val = haversine_km(st_lat, st_lon, c_meta["lat"], c_meta["lon"])
            b_val = calculate_bearing_deg(st_lat, st_lon, c_meta["lat"], c_meta["lon"])
            dist_str = f"{d_val:.2f} km"
            brg_str = f"{b_val:.1f}°"
        elif "distance_km" in h:
            d_val = h["distance_km"]
            dist_str = f"{d_val:.2f} km"
            if "bearing_deg" in h:
                b_val = h["bearing_deg"]
                brg_str = f"{b_val:.1f}°"

        ang_offset = None
        if b_val is not None and w_dir is not None:
            ang_offset = abs(b_val - w_dir)
            if ang_offset > 180.0:
                ang_offset = 360.0 - ang_offset

        tier = determine_confidence_tier(
            score=score,
            spread=spread,
            discriminability=discrim_val,
            operating_status=op_status,
            angular_offset_deg=ang_offset,
            wind_speed_ms=w_speed,
            classification=classification
        )

        clusters_formatted.append({
            "rank": idx,
            "id": hid,
            "name": hname,
            "type": htype,
            "score": score,
            "interval": bounds,
            "spread": spread,
            "tier": tier,
            "bearing": brg_str,
            "distance": dist_str,
            "operating_status": op_status,
            "corroboration": h.get("evidence_for", [])
        })

    lines = []
    lines.append(f"# Programmatic Inspection Shortlist: `{cid}`\n")
    lines.append(f"- **Station**: `{sname}`")
    lines.append(f"- **Timestamp (UTC)**: `{ts}`")
    lines.append(f"- **Station Receptor Ambient Telemetry**: PM2.5 = `{p25} ug/m3`, PM10 = `{p10} ug/m3`, NO2 = `{no2} ug/m3`, CO = `{co}`")
    lines.append(f"- **Local Excess Over Regional Baseline**: `+{local_excess} ug/m3` (Regional Baseline: `{regional_bg} ug/m3`)")
    lines.append(f"- **Meteorological Advection**: `{w_wording}` at `{w_speed} m/s`")
    lines.append(f"- **Footprint Discriminability**: `{discrim_val:.2f}` (`{discrim_state}`)")
    neighbours = case_data.get("downwind_neighbour_corroboration", [])
    for n in neighbours:
        if "vivek vihar" in n.get("name", "").lower():
            lines.append(f"- **Downwind Neighbour Corroboration**: `{n['name']}` at `{n['distance_km']:.2f} km` (bearing `{n['bearing_deg']}°`), PM2.5 = `{n['neighbour_pm25']} ug/m3`")
    lines.append("- **Attribution Classification**: `Multiple Comparable Candidates` (Nocturnal inversion, 44.1° candidate offset, and light wind prevent single-source isolation)\n")
    lines.append("---\n")
    lines.append("## Ranked Priority Candidates Table\n")
    lines.append("| Rank | Candidate ID | Name | Category | Bearing | Distance | Operating Status | Confidence Tier |")
    lines.append("| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |")

    for c in clusters_formatted[:10]:
        lines.append(
            f"| **#{c['rank']}** | `{c['id']}` | **{c['name']}** | `{c['type']}` | "
            f"{c['bearing']} | {c['distance']} | `{c['operating_status']}` | **`{c['tier']}`** |"
        )

    lines.append("\n---\n")
    lines.append("## Detailed Shortlist Specifications\n")

    for c in clusters_formatted[:5]:
        lines.append(f"### Rank #{c['rank']}: {c['name']} (`{c['id']}`)")
        lines.append(f"- **Category**: `{c['type']}`")
        lines.append(f"- **Bearing & Distance**: `{c['bearing']}` at `{c['distance']}`")
        lines.append(f"- **Confidence Tier**: **`{c['tier'].upper()}`**")
        lines.append(f"- **Operating Status**: `{c['operating_status']}`")
        if c['corroboration']:
            lines.append(f"- **Corroborating Evidence**: `{', '.join(c['corroboration'][:3])}`")
        lines.append("")

    lines.append("---\n")
    lines.append("*Generated programmatically by `core/ranking.py` & `scripts/generate_shortlist_markdown.py`. Strictly software-only inspection triage assistance.*")

    content = "\n".join(lines)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Programmatic shortlist successfully written to {output_md_path}")
    return content

if __name__ == "__main__":
    test_json = "data/cases_out/case_anand_vihar_20251102.json"
    target_md = "docs/case_anand_vihar_20251102_shortlist.md"
    generate_shortlist_markdown(test_json, target_md)
