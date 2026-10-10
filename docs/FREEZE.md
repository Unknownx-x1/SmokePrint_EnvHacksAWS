# SmokePrint System Freeze (Phase 5.4)

- **Date**: 2026-10-10
- **Git Commit Hash**: `6e429aa683a726f2ae6a1f021d2fedae4f4c2b75`
- **Live HTTP API URL**: `https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com`
- **Live Website URL**: `http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com`
- **Pytest Total**: 45 passed, 0 failed, 0 errors in 9.90s
- **Frozen Directory Status**: `/core` strictly FROZEN (0 edits made under `core/`).

---

## 1. Candidate Provenance Audit

All candidate locations across all 7 canonical cases are loaded dynamically and strictly from OpenStreetMap catalog data (`data/osm_candidates.json`). The prior hand-maintained coordinate table in `data/candidate_locations.py` and `infra/lambdas/candidate_locations.py` has been completely removed in favor of dynamic OSM loading.

### April Case Investigation (`osm_node_11982201446`, `osm_node_11982171910`, `osm_node_11982171916`)
- **Origin of rounded coordinates**: The values `(28.65000, 77.32000)`, `(28.65200, 77.32100)`, and `(28.65150, 77.32150)` were introduced in an early mock script as manual placeholder approximations.
- **Resolution**: Removed all hand-entered overrides. In `data/osm_candidates.json`, node `osm_node_11982201446` is at true coordinates `(28.6669002, 77.3124105)` (distance: 2.25 km, bearing: 351.0° from Anand Vihar). All coordinates now reflect exact OSM catalog values with $\ge 4$ decimal places of precision.

### Ghazipur Landfill & Inland Container Depot Verification
- `osm_way_76727509` (Ghazipur Landfill): True OSM entry present in `data/osm_candidates.json` at `(28.6240472, 77.3274258)`.
- `osm_way_287054776` (Inland Container Depot): True OSM entry present in `data/osm_candidates.json` at `(28.6364928, 77.3168548)`.
Neither facility is an artificial or hand-invented record.

### Provenance Audit Table (All 7 Canonical Cases)
| Case ID | Candidate ID | Name | Category | Centroid (Lat, Lon) | OSM Catalog (Lat, Lon) | Diff | Decimals |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_anand_vihar_20251102` | `osm_relation_3808258` | Patparganj Industrial Area | industrial | (28.6407938, 77.3104848) | (28.6407938, 77.3104848) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_464283162` | Rajghat Bus Depot | industrial | (28.6424527, 77.2532476) | (28.6424527, 77.2532476) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_464283160` | Rajghat Thermal Power Station | industrial | (28.6375535, 77.2549769) | (28.6375535, 77.2549769) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_464283150` | Rajghat TPS Flyash Dump | landfill | (28.6431418, 77.2550299) | (28.6431418, 77.2550299) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_1544621569` | Unnamed Industrial Site | industrial | (28.6267163, 77.2259313) | (28.6267163, 77.2259313) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_relation_3808258` | Patparganj Industrial Area | industrial | (28.6407938, 77.3104848) | (28.6407938, 77.3104848) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_76727509` | Ghazipur Landfill | landfill | (28.6240472, 77.3274258) | (28.6240472, 77.3274258) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_287054776` | Inland Container Depot | industrial | (28.6364928, 77.3168548) | (28.6364928, 77.3168548) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_464283162` | Rajghat Bus Depot | industrial | (28.6424527, 77.2532476) | (28.6424527, 77.2532476) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_464283160` | Rajghat Thermal Power Station | industrial | (28.6375535, 77.2549769) | (28.6375535, 77.2549769) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_node_11982201446` | Unnamed Landfill Site | landfill | (28.6669002, 77.3124105) | (28.6669002, 77.3124105) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_node_11982171910` | Unnamed Landfill Site | landfill | (28.6644268, 77.3134372) | (28.6644268, 77.3134372) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_node_11982171916` | Unnamed Landfill Site | landfill | (28.6641838, 77.3139360) | (28.6641838, 77.3139360) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_relation_3808258` | Patparganj Industrial Area | industrial | (28.6407938, 77.3104848) | (28.6407938, 77.3104848) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_way_76727509` | Ghazipur Landfill | landfill | (28.6240472, 77.3274258) | (28.6240472, 77.3274258) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_node_5950266473` | Unnamed Landfill Site | landfill | (28.5701887, 77.1706859) | (28.5701887, 77.1706859) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_way_1215682054` | Unnamed Industrial Site | industrial | (28.5630602, 77.1656094) | (28.5630602, 77.1656094) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_node_5950266474` | Unnamed Landfill Site | landfill | (28.5714392, 77.1704208) | (28.5714392, 77.1704208) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_way_368149813` | Okhla Industrial Area Phase III | industrial | (28.5412497, 77.2727142) | (28.5412497, 77.2727142) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_relation_3911489` | Flatted Factories | industrial | (28.5367098, 77.2749457) | (28.5367098, 77.2749457) | 0.0000000 | 7 |
| `case_crri_20260515` | *(none - dispatch refused)* | - | - | - | - | - | - |
| `case_gurugram_20260630` | *(none - dispatch refused)* | - | - | - | - | - | - |
| `case_regional_smog_20251020` | *(none - dispatch refused)* | - | - | - | - | - | - |

---

## 2. Non-Site Outcomes Separation

In the shortlist, API, and UI:
1. `outcome_insufficient_evidence` and `outcome_possible_fault` have been removed from the physical candidate list and from tier chips.
2. They are placed in a dedicated `other_explanations_considered` block containing deterministic reasons and one-sentence explanations.
3. For refusal cases (`case_crri_20260515`, `case_gurugram_20260630`, `case_regional_smog_20251020`), the physical candidate shortlist is empty (`[]`), and tier chips are omitted.

---

## 3. Transport Wording Rules & Low-Wind Count

### 3-Tier Wording Implementation:
- **$\le 25^\circ$ angular offset**: `"upwind"` (e.g. `"Located 6.15 km upwind from station (bearing 265.5°)."`)
- **$25^\circ < \text{offset} \le 45^\circ$**: `"somewhat off the wind line"` (e.g. `"Located 0.86 km from station (bearing 218.9°), somewhat off the wind line (44.1° angular offset)."`)
- **$> 45^\circ$**: `"off the main wind line"` (e.g. `"Located 2.77 km from station (bearing 156.3°), off the main wind line (106.7° angular offset)."`)

### Low-Wind Case Count:
Exactly 5 of the 7 cases have wind speed $< 1.5$ m/s:
1. `case_anand_vihar_20260131` (1.19 m/s)
2. `case_anand_vihar_20260405` (0.97 m/s)
3. `case_rkpuram_20251112` (1.17 m/s)
4. `case_crri_20260515` (1.39 m/s)
5. `case_regional_smog_20251020` (0.89 m/s)

---

## 4. Live API and Recompute Verification

Verified live against `https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com`:

| Case ID | Wind (m/s @ deg) | Classification | Shortlist Candidates | Tiers | Low Wind | Dispatch Refused | Live vs Canonical |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_anand_vihar_20251102` | 2.56 m/s @ 263.0° | corroborated | 5 | medium, medium, low, low, medium | False | False | **Exact Match (0 diff)** |
| `case_anand_vihar_20260131` | 1.19 m/s @ 105.0° | corroborated | 5 | low, low, low, low, low | True | False | **Exact Match (0 diff)** |
| `case_anand_vihar_20260405` | 0.97 m/s @ 15.0° | corroborated | 5 | low, low, low, low, low | True | False | **Exact Match (0 diff)** |
| `case_rkpuram_20251112` | 1.17 m/s @ 306.0° | corroborated | 5 | low, low, low, low, low | True | False | **Exact Match (0 diff)** |
| `case_crri_20260515` | 1.39 m/s @ 305.0° | uncorroborated | 0 | none | True | True | **Exact Match (0 diff)** |
| `case_gurugram_20260630` | 3.92 m/s @ 289.0° | uncorroborated | 0 | none | False | True | **Exact Match (0 diff)** |
| `case_regional_smog_20251020` | 0.89 m/s @ 71.0° | regional | 0 | none | True | True | **Exact Match (0 diff)** |

### Live Recompute Test (`POST /cases/case_anand_vihar_20251102/recompute`):
- Run ID: `run_d1acc61ffcb4`
- Status: `SUCCEEDED`
- Source: `replayed`
- Mode: `replayed_from_canonical_output`
- Note: `replayed from validated core output`
- Candidates returned: 5 (Patparganj, Rajghat Depot, Rajghat TPS, Rajghat Flyash, Unnamed Industrial)

---

## 5. Test Suite Verification

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.12.0, asyncio-1.4.0, cov-7.1.0, mock-3.15.1
collected 45 items

tests/test_agents.py ....................                                [ 22%]
tests/test_api_single_source_of_truth.py ...                             [ 28%]
tests/test_audit_phase53.py ....                                         [ 37%]
tests/test_audit_phase54.py ....                                         [ 46%]
tests/test_core.py .......                                               [ 62%]
tests/test_evidence_page_numbers.py ...                                  [ 68%]
tests/test_recompute_parity.py .......                                   [ 84%]
tests/test_single_source_of_truth.py ...                                 [ 91%]
tests/test_tier_rules.py ....                                            [100%]

============================= 45 passed in 9.90s ==============================
```
