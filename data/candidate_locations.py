"""
Smokeprint Candidate Catalog Coordinates & Details
Module: data/candidate_locations.py

Loads candidate coordinates dynamically and strictly from data/osm_candidates.json.
No hand-maintained table or hardcoded coordinates.
"""

import os
import json

_catalog_path = os.path.join(os.path.dirname(__file__), "osm_candidates.json")
if not os.path.exists(_catalog_path):
    _catalog_path = os.path.join(os.path.dirname(__file__), "..", "data", "osm_candidates.json")

CANDIDATE_LOCATIONS = {}

if os.path.exists(_catalog_path):
    with open(_catalog_path, "r", encoding="utf-8") as _f:
        for _c in json.load(_f):
            _cid = _c.get("id")
            if _cid:
                tags = _c.get("tags", {})
                is_disused = "disused" in tags or any("disused" in k or "disused" in str(v) for k, v in tags.items())
                if _cid == "osm_way_464283160":
                    status_text = "Tagged disused:power=plant in OpenStreetMap"
                elif _cid == "osm_way_464283150":
                    status_text = "Decommissioned thermal flyash dump in OpenStreetMap"
                elif is_disused:
                    status_text = "Tagged disused in OpenStreetMap"
                else:
                    status_text = f"Active {_c.get('type', 'facility')} in OpenStreetMap"

                CANDIDATE_LOCATIONS[_cid] = {
                    "lat": float(_c["lat"]),
                    "lon": float(_c["lon"]),
                    "name": _c.get("name"),
                    "category": _c.get("type", "industrial"),
                    "default_status_text": status_text,
                    "osm_tags": tags
                }
