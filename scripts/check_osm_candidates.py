import json

with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

catalog_ids = {c["id"]: c for c in catalog}

search_ids = [
    "osm_node_11982201446", "osm_node_11982171910", "osm_node_11982171916",
    "osm_way_76727509", "osm_way_287054776", "osm_way_1498754706", "osm_way_287054788", "osm_way_287054784",
    "osm_relation_3808258", "osm_way_464283162", "osm_way_464283160", "osm_way_464283150", "osm_way_1544621569",
    "osm_node_5884780985", "osm_node_7150717314", "osm_node_7150717317", "osm_node_6862917578", "osm_node_5950266473",
    "osm_way_661784209", "osm_way_802304540", "osm_way_76700057", "osm_way_72004862"
]

print("=== Checking search IDs against data/osm_candidates.json ===")
for sid in search_ids:
    if sid in catalog_ids:
        c = catalog_ids[sid]
        print(f"FOUND {sid}: name='{c.get('name')}' lat={c.get('lat')} lon={c.get('lon')} type={c.get('type')}")
    else:
        print(f"NOT FOUND: {sid}")

print("\n=== Searching by keyword in catalog ===")
for c in catalog:
    n = (c.get("name") or "").lower()
    t = (c.get("type") or "").lower()
    tags = str(c.get("tags", {})).lower()
    if any(k in n or k in tags for k in ["ghazipur", "container", "inland", "depot", "thermal", "patparganj", "119822"]):
        print(f"MATCH: {c['id']} | name='{c.get('name')}' | type={c.get('type')} | lat={c.get('lat')} lon={c.get('lon')}")
