import requests
import json

overpass_endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]

bbox = "(28.20,76.70,28.95,77.60)"
query = f"""[out:json][timeout:60];
(
  nwr["man_made"="kiln"]{bbox};
  nwr["industrial"="brick_kiln"]{bbox};
  nwr["landuse"="landfill"]{bbox};
  nwr["amenity"="waste_disposal"]{bbox};
  nwr["landuse"="quarry"]{bbox};
  nwr["landuse"="construction"]{bbox};
  nwr["landuse"="industrial"]{bbox};
);
out center tags;
"""

headers = {
    "User-Agent": "SmokeprintAirQualityApp/1.0 (shivansh@hackathon.local)",
    "Accept": "application/json"
}

data = None
for ep in overpass_endpoints:
    print(f"Trying endpoint: {ep}")
    try:
        resp = requests.post(ep, data={"data": query}, headers=headers, timeout=45)
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            break
        else:
            print("Response:", resp.text[:200])
    except Exception as e:
        print("Failed:", e)

if data:
    elements = data.get("elements", [])
    print(f"\nTotal OSM elements: {len(elements)}")
    counts = {"brick_kiln": 0, "landfill": 0, "quarry": 0, "construction": 0, "industrial": 0, "other": 0}
    parsed = []
    for el in elements:
        tags = el.get("tags", {})
        el_id = f"osm_{el.get('type')}_{el.get('id')}"
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        name = tags.get("name", tags.get("description", "Unnamed Site"))
        
        if tags.get("man_made") == "kiln" or tags.get("industrial") == "brick_kiln":
            stype = "brick_kiln"
        elif tags.get("landuse") == "landfill" or tags.get("amenity") == "waste_disposal":
            stype = "landfill"
        elif tags.get("landuse") == "quarry":
            stype = "quarry"
        elif tags.get("landuse") == "construction":
            stype = "construction"
        elif tags.get("landuse") == "industrial" or "industrial" in tags:
            stype = "industrial"
        else:
            stype = "other"
            
        counts[stype] += 1
        parsed.append({
            "id": el_id,
            "type": stype,
            "name": name,
            "lat": lat,
            "lon": lon,
            "tags": tags
        })
        
    print("\nCandidate source counts by type:")
    for k, v in counts.items():
        print(f"  {k:<15}: {v}")
        
    with open("data/osm_candidates.json", "w") as f:
        json.dump(parsed, f, indent=2)
    print("\nSaved candidates to data/osm_candidates.json")
else:
    print("Could not fetch OSM data from any endpoint")
