import json
import glob
from data.tier_rules import determine_confidence_tier

changed_total = 0
for fpath in glob.glob("data/cases_out/case_*.json"):
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    cid = data["case_id"]
    discrim = data.get("footprint_discriminability", {}).get("discriminability_metric", 1.0)
    w_speed = data.get("wind", {}).get("wind_speed_ms")
    w_dir = data.get("wind", {}).get("wind_direction_deg")
    classification = data.get("classification") or data.get("label")
    print(f"\n{cid} (wind={w_speed} m/s, discrim={discrim}, class={classification}):")
    
    modified = False
    for h in data.get("hypotheses", [])[:5]:
        status = h.get("operating_status")
        score = h.get("relative_score", 0.0)
        bounds = h.get("interval", [0.0, 0.0])
        spread = bounds[1] - bounds[0] if bounds else 0.0
        
        # calculate angular offset if bearing is in evidence
        ang_offset = None
        for ev in h.get("evidence_for", []):
            if "bearing" in ev.lower() and "deg" in ev.lower():
                # e.g. "bearing 260.2 deg"
                try:
                    parts = ev.split("bearing")[1].split("deg")[0].strip().split()
                    b_val = float(parts[0])
                    if w_dir is not None:
                        diff = abs(b_val - w_dir)
                        ang_offset = 360.0 - diff if diff > 180.0 else diff
                except Exception:
                    pass

        expected_tier = determine_confidence_tier(
            score=score,
            spread=spread,
            discriminability=discrim,
            operating_status=status,
            angular_offset_deg=ang_offset,
            wind_speed_ms=w_speed,
            classification=classification
        )
        old_tier = h.get("confidence_tier")
        print(f"  {h['id']} ({h.get('name')}): old={old_tier} -> expected={expected_tier} (status={status})")
        if old_tier != expected_tier:
            h["confidence_tier"] = expected_tier
            modified = True
            changed_total += 1
            
    if modified:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  --> Updated {fpath}")

print(f"\nDone. Total tiers updated across canonical JSONs: {changed_total}")
