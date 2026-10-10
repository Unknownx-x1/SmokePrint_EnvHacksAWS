import json
import math

with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
    osm_catalog = {c["id"]: c for c in json.load(f)}

CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112"
]

print("===============================================================================")
print("CANDIDATE PROVENANCE AUDIT: CHECKING CANONICAL CASES AGAINST OSM_CANDIDATES.JSON")
print("===============================================================================")

total_candidates = 0
discrepancies = []
round_coords = []

for c in CASES:
    with open(f"data/cases_out/{c}.json", "r", encoding="utf-8") as f:
        cd = json.load(f)
    print(f"\nCASE: {c}")
    shortlist = cd.get("shortlist", [])
    for cand in shortlist:
        cid = cand.get("id")
        if cid.startswith("outcome_"):
            continue
        total_candidates += 1
        c_lat = cand.get("lat")
        c_lon = cand.get("lon")
        c_name = cand.get("name")
        c_type = cand.get("type")
        
        osm_entry = osm_catalog.get(cid)
        if not osm_entry:
            print(f"  [MISSING IN OSM] {cid} ({c_name})")
            discrepancies.append((c, cid, "MISSING_IN_OSM", None, None))
            continue
        
        o_lat = osm_entry.get("lat")
        o_lon = osm_entry.get("lon")
        o_type = osm_entry.get("type")
        o_name = osm_entry.get("name")

        # Precision / roundness check (<= 3 decimal places)
        lat_dec = len(str(c_lat).split(".")[1]) if "." in str(c_lat) else 0
        lon_dec = len(str(c_lon).split(".")[1]) if "." in str(c_lon) else 0
        is_round = (lat_dec <= 3) or (lon_dec <= 3) or (str(c_lat).endswith("00")) or (str(c_lon).endswith("00"))

        lat_diff = abs(c_lat - o_lat) if c_lat is not None and o_lat is not None else None
        lon_diff = abs(c_lon - o_lon) if c_lon is not None and o_lon is not None else None
        has_diff = (lat_diff is not None and lat_diff > 1e-5) or (lon_diff is not None and lon_diff > 1e-5)

        flag_str = ""
        if has_diff:
            flag_str += f" [DIFF: dLat={lat_diff:.5f}, dLon={lon_diff:.5f}]"
            discrepancies.append((c, cid, "COORD_MISMATCH", (c_lat, c_lon), (o_lat, o_lon)))
        if is_round:
            flag_str += f" [ROUND/LOW_PRECISION: lat_dec={lat_dec}, lon_dec={lon_dec}]"
            round_coords.append((c, cid, (c_lat, c_lon)))

        print(f"  - {cid:<22} | {c_name:<30} | Case: ({c_lat}, {c_lon}) | OSM: ({o_lat}, {o_lon}) | {flag_str if flag_str else 'OK'}")

print(f"\nTotal site candidates evaluated: {total_candidates}")
print(f"Discrepancies found: {len(discrepancies)}")
print(f"Round/low precision coordinates found: {len(round_coords)}")
