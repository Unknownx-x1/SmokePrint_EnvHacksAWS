import json
import sys

with open("data/osm_candidates.json", "r", encoding="utf-8") as f:
    cat = {c["id"]: c for c in json.load(f)}

for cid in ["osm_way_464283160", "osm_way_464283150", "osm_relation_3808258", "osm_way_76727509", "osm_way_287054776"]:
    c = cat.get(cid)
    if c:
        tags = {k: v for k, v in c.get("tags", {}).items() if not k.startswith("name:")}
        print(f"{cid}: name='{c.get('name')}', lat={c.get('lat')}, lon={c.get('lon')}, type={c.get('type')}, tags={tags}")
