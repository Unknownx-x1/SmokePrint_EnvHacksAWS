# SmokePrint System Freeze (Phase 5.6)

- **Date**: 2026-10-10
- **Git Commit Hash**: `8d4aaf3f55a4e6e572369936346aaa8d7f986987`
- **Live HTTP API URL**: `https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com`
- **Live Website URL**: `http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com`
- **Pytest Total**: 60 passed, 0 failed, 0 errors in 96.26s
- **Playwright E2E Total**: 13 passed (7 comprehensive app flows + 6 deep QA benchmarks)
- **Frozen Directory Status**: `/core` strictly FROZEN (0 edits made under `core/`).

---

## 1. Candidate Provenance Audit & Shortlist Discrepancy Resolution

All candidate locations across all 7 canonical cases are loaded dynamically and strictly from OpenStreetMap catalog data (`data/osm_candidates.json`). The prior hand-maintained coordinate table in `data/candidate_locations.py` and `infra/lambdas/candidate_locations.py` has been completely eliminated.

### Why Phase 5.4 and Phase 5.5 / Live API Candidate Lists Differed
In Phase 5.4, the table in `docs/FREEZE.md` was drafted from an outdated snapshot generated prior to isolating each episode's meteorological wind direction:
1. **`case_anand_vihar_20260131`**: The Phase 5.4 table incorrectly listed candidates evaluated against the November 2025 wind (263.0° / W) rather than the actual January 2026 wind (105.0° / ESE). Under 263.0° wind, Patparganj and Rajghat appeared upwind; under the true 105.0° wind, Patparganj (bearing 218.9°) and Rajghat (bearing 265.5°) are in the opposite quadrant and do not belong in the shortlist.
2. **`case_rkpuram_20251112`**: The Phase 5.4 table listed Okhla Industrial Area and Flatted Factories (bearings ~115° ESE), which were artifacts of cross-case contamination against a WNW wind (306.0°).

**Correct Source of Truth**: The Live API, `data/cases_out/*.json`, and `web/src/data/cases/*.json` are 100% correct, evaluating each case strictly against its own meteorological wind vector. The Phase 5.4 `docs/FREEZE.md` table was the wrong document and is corrected below.

### Centroid-vs-OSM Verification (Served by Live API)
Re-run live against `https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com`:
Every candidate matches `data/osm_candidates.json` with **exactly 0.0000000 difference** and $\ge 6$ decimal places of precision.

| Case ID | Candidate ID | Name | Category | Centroid (Lat, Lon) | OSM Catalog (Lat, Lon) | Diff | Decimals |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_anand_vihar_20251102` | `osm_relation_3808258` | Patparganj Industrial Area | industrial | (28.6407938, 77.3104848) | (28.6407938, 77.3104848) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_464283162` | Rajghat Bus Depot | industrial | (28.6424527, 77.2532476) | (28.6424527, 77.2532476) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_464283160` | Rajghat Thermal Power Station | industrial | (28.6375535, 77.2549769) | (28.6375535, 77.2549769) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_464283150` | Rajghat TPS Flyash Dump | landfill | (28.6431418, 77.2550299) | (28.6431418, 77.2550299) | 0.0000000 | 7 |
| `case_anand_vihar_20251102` | `osm_way_1544621569` | Unnamed Industrial Site | industrial | (28.6267163, 77.2259313) | (28.6267163, 77.2259313) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_1498754706` | Unnamed Industrial Site | industrial | (28.6463588, 77.3230478) | (28.6463588, 77.3230478) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_76727509` | Ghazipur Landfill | landfill | (28.6240472, 77.3274258) | (28.6240472, 77.3274258) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_287054788` | Unnamed Industrial Site | industrial | (28.6404780, 77.3160381) | (28.6404780, 77.3160381) | 0.0000000 | 6 |
| `case_anand_vihar_20260131` | `osm_way_287054784` | Unnamed Industrial Site | industrial | (28.6401521, 77.3163257) | (28.6401521, 77.3163257) | 0.0000000 | 7 |
| `case_anand_vihar_20260131` | `osm_way_287054776` | Inland Container Depot | industrial | (28.6364928, 77.3168548) | (28.6364928, 77.3168548) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_node_11982201446` | Unnamed Landfill Site | landfill | (28.6669002, 77.3124105) | (28.6669002, 77.3124105) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_node_11982171910` | Unnamed Landfill Site | landfill | (28.6696109, 77.3073786) | (28.6696109, 77.3073786) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_node_11982171916` | Unnamed Landfill Site | landfill | (28.6695396, 77.3040884) | (28.6695396, 77.3040884) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_way_1498754706` | Unnamed Industrial Site | industrial | (28.6463588, 77.3230478) | (28.6463588, 77.3230478) | 0.0000000 | 7 |
| `case_anand_vihar_20260405` | `osm_way_661784209` | Unnamed Industrial Site | industrial | (28.6501902, 77.3266027) | (28.6501902, 77.3266027) | 0.0000000 | 7 |
| `case_crri_20260515` | *(none - dispatch refused)* | - | - | - | - | - | - |
| `case_gurugram_20260630` | *(none - dispatch refused)* | - | - | - | - | - | - |
| `case_regional_smog_20251020` | *(none - dispatch refused)* | - | - | - | - | - | - |
| `case_rkpuram_20251112` | `osm_node_5884780985` | Unnamed Landfill Site | landfill | (28.5718801, 77.1723405) | (28.5718801, 77.1723405) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_node_7150717314` | Unnamed Landfill Site | landfill | (28.5744153, 77.1686820) | (28.5744153, 77.1686820) | 0.0000000 | 6 |
| `case_rkpuram_20251112` | `osm_node_7150717317` | Unnamed Landfill Site | landfill | (28.5726485, 77.1696064) | (28.5726485, 77.1696064) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_node_6862917578` | Unnamed Landfill Site | landfill | (28.5650245, 77.1632678) | (28.5650245, 77.1632678) | 0.0000000 | 7 |
| `case_rkpuram_20251112` | `osm_node_5950266473` | Unnamed Landfill Site | landfill | (28.5657199, 77.1609365) | (28.5657199, 77.1609365) | 0.0000000 | 7 |

---

## 2. Offset Audit & Upwind Clarification

### Column Renaming & Offset Verification
The column previously labeled "Downwind Flag (>90)" is renamed to **"Within 90 deg of wind-from axis"**, including the explicit angular offset in degrees.

### Correction to "Strictly Upwind" Claim
The prior assertion that all candidates were "strictly upwind" was inaccurate. All 20 candidate evaluations fall within the 90° upwind semi-circle (max offset 79.4°, zero candidates are downwind $> 90^\circ$). However, they belong to 3 distinct aerodynamic corridors:
1. **$\le 25.0^\circ$ ("upwind")**: Direct plume centerline (9 candidates).
2. **$25.0^\circ < \text{offset} \le 45.0^\circ$ ("somewhat off the wind line")**: Sector edge transport (4 candidates).
3. **$45.0^\circ < \text{offset} \le 90.0^\circ$ ("off the main wind line")**: Crosswind quadrant (7 candidates).

| Case ID | Candidate ID | Name | Bearing | Wind-From | Offset (deg) | Within 90 deg of wind-from axis | Transport Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_anand_vihar_20251102` | `osm_relation_3808258` | Patparganj Industrial Area | 218.9° | 263.0° | 44.1° | Yes (44.1°) | somewhat off the wind line |
| `case_anand_vihar_20251102` | `osm_way_464283162` | Rajghat Bus Depot | 265.5° | 263.0° | 2.5° | Yes (2.5°) | upwind (direct plume line) |
| `case_anand_vihar_20251102` | `osm_way_464283160` | Rajghat Thermal Power Station | 260.2° | 263.0° | 2.8° | Yes (2.8°) | upwind (direct plume line) |
| `case_anand_vihar_20251102` | `osm_way_464283150` | Rajghat TPS Flyash Dump | 266.1° | 263.0° | 3.1° | Yes (3.1°) | upwind (direct plume line) |
| `case_anand_vihar_20251102` | `osm_way_1544621569` | Unnamed Industrial Site | 255.7° | 263.0° | 7.3° | Yes (7.3°) | upwind (direct plume line) |
| `case_anand_vihar_20260131` | `osm_way_1498754706` | Unnamed Industrial Site | 94.4° | 105.0° | 10.6° | Yes (10.6°) | upwind (direct plume line) |
| `case_anand_vihar_20260131` | `osm_way_76727509` | Ghazipur Landfill | 156.3° | 105.0° | 51.3° | Yes (51.3°) | off the main wind line |
| `case_anand_vihar_20260131` | `osm_way_287054788` | Unnamed Industrial Site | 180.0° | 105.0° | 75.0° | Yes (75.0°) | off the main wind line |
| `case_anand_vihar_20260131` | `osm_way_287054784` | Unnamed Industrial Site | 177.8° | 105.0° | 72.8° | Yes (72.8°) | off the main wind line |
| `case_anand_vihar_20260131` | `osm_way_287054776` | Inland Container Depot | 176.0° | 105.0° | 71.0° | Yes (71.0°) | off the main wind line |
| `case_anand_vihar_20260405` | `osm_node_11982201446` | Unnamed Landfill Site | 351.0° | 15.0° | 24.0° | Yes (24.0°) | upwind (direct plume line) |
| `case_anand_vihar_20260405` | `osm_node_11982171910` | Unnamed Landfill Site | 341.6° | 15.0° | 33.4° | Yes (33.4°) | somewhat off the wind line |
| `case_anand_vihar_20260405` | `osm_node_11982171916` | Unnamed Landfill Site | 335.2° | 15.0° | 39.8° | Yes (39.8°) | somewhat off the wind line |
| `case_anand_vihar_20260405` | `osm_way_1498754706` | Unnamed Industrial Site | 94.4° | 15.0° | 79.4° | Yes (79.4°) | off the main wind line |
| `case_anand_vihar_20260405` | `osm_way_661784209` | Unnamed Industrial Site | 70.1° | 15.0° | 55.1° | Yes (55.1°) | off the main wind line |
| `case_crri_20260515` | *(none - dispatch refused)* | - | - | 305.0° | - | - | - |
| `case_gurugram_20260630` | *(none - dispatch refused)* | - | - | 289.0° | - | - | - |
| `case_regional_smog_20251020` | *(none - dispatch refused)* | - | - | 71.0° | - | - | - |
| `case_rkpuram_20251112` | `osm_node_5884780985` | Unnamed Landfill Site | 303.9° | 306.0° | 2.1° | Yes (2.1°) | upwind (direct plume line) |
| `case_rkpuram_20251112` | `osm_node_7150717314` | Unnamed Landfill Site | 304.8° | 306.0° | 1.2° | Yes (1.2°) | upwind (direct plume line) |
| `case_rkpuram_20251112` | `osm_node_7150717317` | Unnamed Landfill Site | 301.7° | 306.0° | 4.3° | Yes (4.3°) | upwind (direct plume line) |
| `case_rkpuram_20251112` | `osm_node_6862917578` | Unnamed Landfill Site | 274.9° | 306.0° | 31.1° | Yes (31.1°) | somewhat off the wind line |
| `case_rkpuram_20251112` | `osm_node_5950266473` | Unnamed Landfill Site | 276.1° | 306.0° | 29.9° | Yes (29.9°) | somewhat off the wind line |

---

## 3. TimeSeriesChart Data Source & Grounding

`TimeSeriesChart` plots **strictly real OpenAQ hourly telemetry rows**:
- **Source Storage**: `data/stations_12m/station_{station_id}_12m.json`
- **Field Extracted**: `data.pm25[timestamp_utc]` (QC'd continuous telemetry, unit `ug/m3`)
- **Sensor Verification**: Verified against station sensor definitions:
  - Station 235 (Anand Vihar): Sensor `12235610`
  - Station 17 (RK Puram): Sensor `12234787`
  - Station 5627 (CRRI Mathura Rd): Sensor `12234678`
  - Station 301 (Gurugram Sec-51): Sensor `14258988`
- **Midpoint Convention**: Labeled `"hourly means, interval midpoint, IST"` (interval window T-2h to T+2h).
- **Zero Interpolation**: No synthetic points, smoothing, or bezier curves. Polyline connects exact source rows.
- **Regional Episode Handling**: For `case_regional_smog_20251020`, `hourly_series` is `None`; the component renders a dedicated "Peak vs Regional Baseline" comparison card across the 33-station background network.
- **Automated Verification**: `tests/test_timeseries_source_rows.py` asserts every plotted point across all cases exists in source JSON files.

---

## 4. UI Copy & Officer Experience Audit

All developer/internal terminology has been eliminated from public interfaces:
1. **Header Badge**: Removed "FROZEN CORE" and "FROZEN CORE v2.7"; replaced with **"REGULATORY AUDIT ACTIVE"** (desktop) and **"SYSTEM ACTIVE"** (mobile).
2. **Mobile Dispatch Briefing**: Replaced developer string "FIELD MOBILE (390px)" with **"MOBILE INSPECTION DISPATCH"**.
3. **Action Prompts**: Replaced "Open in Field Mobile (390px)" with **"Open Mobile Inspection Dispatch →"**.
4. **Execution Status**: Replayed Step Functions states display officer-facing audit confirmation (**"STATUS: SUCCEEDED (source: replayed)"**).

---

## 5. End-to-End & Deep QA Verification

### QA Diagnostics Report:
1. **Console Errors & Warnings**: **Zero errors, zero warnings** across all 5 public pages (`/`, `/officer/`, `/field/.../`, `/evidence/`, `/architecture/`).
2. **Network Throttling Benchmarks**:
   - Fast 3G load time (`/officer/`): **2.63s** (target < 10.0s).
   - Slow 3G load time (`/field/.../`): **1.74s** (target < 15.0s).
3. **WebGL-Unavailable Fallback**: When WebGL APIs are unavailable or disabled, `OfficerMap` degrades gracefully to **Atmospheric Schematic Mode**, displaying coordinates, prevailing wind vector, and candidate counts without throwing unhandled exceptions.
4. **Keyboard Focus & Accessibility**: Tab order cycles sequentially through navigation links, case tabs, and interactive buttons with visible focus rings.
5. **Favicon & Titles**:
   - `favicon.ico`: 200 OK (32x32 dark icon with plume emblem).
   - Document `<title>`: Descriptive across all routes (`Smokeprint | Delhi-NCR Air Inspection Decision System`).
6. **CORS & Mixed Content**: Modern browsers allow HTTP website to HTTPS API calls without Mixed Content blockage. In-page evaluation from HTTP origin returned HTTP 200 with `Access-Control-Allow-Origin: *`.

### 7 Automated Playwright E2E Tests:
- `test_landing_page`: Asserts single required headline, replay animation loop, navigation links, and zero errors on desktop (1280x800) and mobile (390x844).
- `test_officer_page_all_cases_and_features`: Asserts all 7 case switcher tabs, detail panel updates, deep-linking (`?caseId=...`), Rajghat disused explanation row expand, TimeSeriesChart rendering with OpenAQ sensor IDs, non-site outcomes block, and "Replay on AWS" execution polling.
- `test_offline_fallback_badge_and_data`: Asserts that when live API requests are blocked, the OFFLINE badge appears and all 7 cases function seamlessly from bundled data.
- `test_field_page_all_7_cases`: Asserts mobile layout at 390px with zero horizontal scroll, touch targets $\ge 44$px, refused case cards ("NO DISPATCH RECOMMENDED"), and friendly 404 page for unknown IDs.
- `test_evidence_page_numbers_match_backtest_json`: Asserts 100% exact numerical match with `docs/backtest_results.json`, caveat text visibility, and mobile table layout.
- `test_architecture_page`: Asserts architecture diagram rendering and navigational links on desktop and mobile.
- `test_routing_trailing_slashes_and_forbidden_strings`: Asserts HTTP 200 on all routes with and without trailing slashes, reload survival, browser back/forward history, and zero instances of `undefined`, `NaN`, `null`, `[object Object]`, or raw JSON.

**Command to rerun all tests**:
```bash
pytest tests/ -v
```

---

## 6. Final Test Suite Results

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0
configfile: pytest.ini
collected 60 items

tests/e2e/test_missing_qa_items.py::test_console_errors_and_warnings_per_page PASSED [  1%]
tests/e2e/test_missing_qa_items.py::test_3g_throttle_load_times PASSED   [  3%]
tests/e2e/test_missing_qa_items.py::test_webgl_unavailable_fallback PASSED [  5%]
tests/e2e/test_missing_qa_items.py::test_keyboard_focus_order_and_visible_focus PASSED [  6%]
tests/e2e/test_missing_qa_items.py::test_favicon_and_titles PASSED       [  8%]
tests/e2e/test_missing_qa_items.py::test_cors_http_site_to_https_api PASSED [ 10%]
tests/e2e/test_ui_qa_phase55.py::test_landing_page PASSED                [ 11%]
tests/e2e/test_ui_qa_phase55.py::test_officer_page_all_cases_and_features PASSED [ 13%]
tests/e2e/test_ui_qa_phase55.py::test_offline_fallback_badge_and_data PASSED [ 15%]
tests/e2e/test_ui_qa_phase55.py::test_field_page_all_7_cases PASSED      [ 16%]
tests/e2e/test_ui_qa_phase55.py::test_evidence_page_numbers_match_backtest_json PASSED [ 18%]
tests/e2e/test_ui_qa_phase55.py::test_architecture_page PASSED           [ 20%]
tests/e2e/test_ui_qa_phase55.py::test_routing_trailing_slashes_and_forbidden_strings PASSED [ 21%]
tests/test_agents.py ....................                                [ 38%]
tests/test_api_single_source_of_truth.py ...                             [ 43%]
tests/test_audit_phase53.py ....                                         [ 50%]
tests/test_audit_phase54.py ....                                         [ 56%]
tests/test_core.py .......                                               [ 68%]
tests/test_evidence_page_numbers.py ...                                  [ 73%]
tests/test_recompute_parity.py .......                                   [ 85%]
tests/test_single_source_of_truth.py ...                                 [ 90%]
tests/test_tier_rules.py ....                                            [ 96%]
tests/test_timeseries_source_rows.py ..                                  [100%]

======================== 60 passed in 96.26s (0:01:36) ========================
```
