import json

with open("data/osm_candidates.json") as f:
    candidates = json.load(f)

summary = {}
for c in candidates:
    ctype = c["type"]
    raw_id = c["id"]
    geom = raw_id.split("_")[1] # node, way, relation
    has_name = c["name"] != "Unnamed Site" and bool(c["name"].strip())
    
    if ctype not in summary:
        summary[ctype] = {"total": 0, "node": 0, "way": 0, "relation": 0, "named": 0}
    summary[ctype]["total"] += 1
    summary[ctype][geom] += 1
    if has_name:
        summary[ctype]["named"] += 1

print(f"Total candidates: {len(candidates)}")
print(f"{'Type':<15} {'Total':<8} {'Nodes (Pts)':<12} {'Ways (Poly)':<12} {'Relations':<12} {'Named Sites':<12}")
print("-" * 75)
for ctype, d in sorted(summary.items()):
    print(f"{ctype:<15} {d['total']:>6} {d['node']:>10} {d['way']:>12} {d['relation']:>12} {d['named']:>12}")
