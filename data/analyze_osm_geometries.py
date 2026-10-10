import json

with open("data/osm_candidates.json") as f:
    candidates = json.load(f)

industrial = [c for c in candidates if c["type"] == "industrial"]
print(f"Total industrial candidates: {len(industrial)}")

geo_counts = {"node": 0, "way": 0, "relation": 0}
tag_breakdown = {}

for ind in industrial:
    raw_id = ind["id"] # osm_way_123 or osm_node_123 or osm_relation_123
    geo_type = raw_id.split("_")[1]
    geo_counts[geo_type] = geo_counts.get(geo_type, 0) + 1
    
    tags = ind.get("tags", {})
    for k in ["landuse", "building", "industrial", "man_made"]:
        if k in tags:
            pair = f"{k}={tags[k]}"
            tag_breakdown[pair] = tag_breakdown.get(pair, 0) + 1

print("\nIndustrial Geometries (Point vs Polygon/Zone):")
for gtype, cnt in geo_counts.items():
    pct = round(100.0 * cnt / len(industrial), 1)
    label = "Point Emitter" if gtype == "node" else "Polygon / Boundary" if gtype == "way" else "Multi-polygon Zone"
    print(f"  {gtype:<10} ({label:<20}): {cnt:>4} ({pct:>5.1f}%)")

print("\nKey Tag Breakdown in Industrial:")
for t, cnt in sorted(tag_breakdown.items(), key=lambda x: -x[1])[:10]:
    print(f"  {t:<30}: {cnt}")
