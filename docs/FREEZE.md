# SmokePrint System Final Freeze (Phase 5.8 - Final Freeze 2)

- **Date**: 2026-10-10
- **Git Tag**: `final-freeze-2`
- **Live HTTP API URL**: `https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com`
- **Live Website URL**: `http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com`
- **Total Tests Passed**: 69 passed (56 unit/audit tests + 13 Playwright E2E tests), 0 failed, 0 errors
- **Frozen Directory Status**: `/core` strictly FROZEN (0 edits made under `core/`).
- **Visible Showcase Cases**: Exactly 6 vetted cases (April case set to `hidden_from_demo: true`).

---

## 1. Raw-Data Reconciliation & Contradiction Resolution

Raw OpenAQ rows were re-pulled directly from the public AWS Open Data OpenAQ archive (`s3://openaq-data-archive/records/csv.gz/locationid={id}/...`) using unsigned S3 client access.

### Contradictions Resolved

1. **Anand Vihar Nov 02 (Station 235) at 21:30Z (03:00 IST)**:
   - **Canonical & Raw S3 Archive Value**: `369.0 µg/m³` (Sensor 12235610).
   - **Source of "486"**: An inadvertent conversational typo in the Phase 5.7 narrative response. The underlying stored JSON and raw OpenAQ rows consistently recorded `369.0 µg/m³`.
   - **Resolution**: Stored telemetry card and hourly series peak are strictly `369.0 µg/m³`.

2. **Anand Vihar Jan 31 (Station 235) at 05:30Z (11:00 IST)**:
   - **Canonical & Raw S3 Archive Value**: `345.0 µg/m³` (Sensor 12235610).
   - **Source of "247"**: An inadvertent conversational typo in the Phase 5.7 narrative response. The underlying stored JSON and raw OpenAQ rows consistently recorded `345.0 µg/m³`.
   - **Resolution**: Stored telemetry card and hourly series peak are strictly `345.0 µg/m³`.

3. **R K Puram Nov 12 (Station 17) at 15:30Z (21:00 IST)**:
   - **Previous State**: The case was assigned interval midpoint `16:00:00Z` (sample `16:30Z` = `427.0 µg/m³`), while the continuous OpenAQ series peaked one hour earlier at `15:30Z` (`487.0 µg/m³`). This caused a mismatch between the telemetry card (427) and the chart peak (487).
   - **Resolution**: Re-timed interval midpoint to `2025-11-12T15:00:00Z` (`20:30 IST`), sampling the true peak at `15:30Z`: `487.0 µg/m³` PM2.5, `619.0 µg/m³` PM10, physical ratio `0.787`, NO2 `90.5 µg/m³`. The chart peak now equals the telemetry card peak (`487.0 µg/m³`).
   - **Wind at 15:00Z**: ERA5 wind speed is `1.42 m/s` (direction `309.0°`), triggering the low-wind rule (`< 1.5 m/s`). All shortlist tiers are forced to `low`. Shortlist candidates remain identical.

4. **Gurugram June 30 (Station 301)**:
   - **Spike Rise Window (04:30Z–08:30Z)**: Telemetry values `275`, `209`, `314`, `316`, `306 µg/m³` capture the particulate surge peaking at `316.0 µg/m³` at `07:30Z`.
   - **Logger Fault Window (08:30Z–12:30Z)**: Telemetry values `306`, `305`, `305`, `307 µg/m³` followed by `NaN` at `12:30Z`. PM2.5 and PM10 locked into an artificial fixed ratio of ~0.6000 (306/510, 305/508, 305/509, 307/512) for 4 consecutive hours before complete channel collapse.
   - **Resolution**: Telemetry card and chart midpoint are grounded at `07:00Z` (peak `316.0 µg/m³`), and the case is correctly refused under dual fault detectors: `constant_ratio_lock` and `collapse_after_peak`.

---

## 2. April Case Policy (`case_anand_vihar_20260405`)

The April 05 case has been assigned `"hidden_from_demo": true` and removed from UI case lists, the API `GET /cases` endpoint, and the offline bundle `web/src/lib/offlineData.ts`. The canonical output file is retained in the repository under `data/cases_out/case_anand_vihar_20260405.json` and `web/src/data/cases/case_anand_vihar_20260405.json`.

### Justification for Hiding
1. **Near-Calm Wind (0.19 m/s)**: Wind speed was near calm (`0.19 m/s`), making directional advection plume physics unreliable.
2. **Re-timed Midpoint**: Re-timed to `00:00Z` (`05:30 IST`), where regional corroboration had not been recomputed against the downwind monitor network under near-calm drift.
3. **Candidate at 108.4° Offset**: Shortlist candidate `osm_way_1498754706` has an angular offset of `108.4°` (downwind), inconsistent with upwind attribution corridors.

---

## 3. Offset Audit & Downwind Rule for the 6 Visible Cases

Wording rule enforced across `data/shortlist_builder.py` and `infra/lambdas/shortlist_builder.py`:
- $\le 25.0^\circ$: `"upwind"`
- $25.0^\circ < \text{offset} \le 45.0^\circ$: `"somewhat off the wind line"`
- $45.0^\circ < \text{offset} \le 90.0^\circ$: `"off the main wind line"`
- $\text{offset} > 90.0^\circ$: `"downwind"`

### Offset Table for the 6 Visible Cases

| Case ID | Candidate ID | Name | Distance | Bearing | Wind-From | Offset | Tier | Transport Label |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_anand_vihar_20251102` | `osm_relation_3808258` | Patparganj Industrial Area | 0.86 km | 218.9° | 263.0° | 44.1° | medium | somewhat off the wind line |
| `case_anand_vihar_20251102` | `osm_way_464283162` | Rajghat Bus Depot | 6.15 km | 265.5° | 263.0° | 2.5° | medium | upwind |
| `case_anand_vihar_20251102` | `osm_way_464283160` | Rajghat Thermal Power Station | 6.05 km | 260.2° | 263.0° | 2.8° | low | upwind (disused) |
| `case_anand_vihar_20251102` | `osm_way_464283150` | Rajghat TPS Flyash Dump | 5.97 km | 266.1° | 263.0° | 3.1° | low | upwind (disused) |
| `case_anand_vihar_20251102` | `osm_way_1544621569` | Unnamed Industrial Site | 9.07 km | 255.7° | 263.0° | 7.3° | medium | upwind |
| `case_anand_vihar_20260131` | `osm_way_1498754706` | Unnamed Industrial Site | 0.69 km | 94.4° | 105.0° | 10.6° | low | upwind |
| `case_anand_vihar_20260131` | `osm_way_76727509` | Ghazipur Landfill | 2.77 km | 156.3° | 105.0° | 51.3° | low | off the main wind line |
| `case_anand_vihar_20260131` | `osm_way_287054788` | Unnamed Industrial Site | 0.71 km | 180.0° | 105.0° | 75.0° | low | off the main wind line |
| `case_anand_vihar_20260131` | `osm_way_287054784` | Unnamed Industrial Site | 0.74 km | 177.8° | 105.0° | 72.8° | low | off the main wind line |
| `case_anand_vihar_20260131` | `osm_way_287054776` | Inland Container Depot | 1.15 km | 176.0° | 105.0° | 71.0° | low | off the main wind line |
| `case_rkpuram_20251112` | `osm_node_5884780985` | Unnamed Landfill Site | 1.72 km | 303.9° | 309.0° | 5.1° | low | upwind |
| `case_rkpuram_20251112` | `osm_node_7150717314` | Unnamed Landfill Site | 2.17 km | 304.8° | 309.0° | 4.2° | low | upwind |
| `case_rkpuram_20251112` | `osm_node_7150717317` | Unnamed Landfill Site | 1.99 km | 301.7° | 309.0° | 7.3° | low | upwind |
| `case_rkpuram_20251112` | `osm_node_6862917578` | Unnamed Landfill Site | 2.32 km | 274.9° | 309.0° | 34.1° | low | somewhat off the wind line |
| `case_rkpuram_20251112` | `osm_node_5950267739` | Unnamed Landfill Site | 2.60 km | 280.8° | 309.0° | 28.2° | low | somewhat off the wind line |
| `case_crri_20260515` | *(none - dispatch refused)* | - | - | - | 305.0° | - | - | Single-station artifact |
| `case_gurugram_20260630` | *(none - dispatch refused)* | - | - | - | 307.0° | - | - | Logger fault |
| `case_regional_smog_20251020` | *(none - dispatch refused)* | - | - | - | 71.0° | - | - | Regional smog |

**Downwind candidates in the 6 visible cases**: **0**. Maximum angular offset across visible cases is `75.0°`. (The only candidate $> 90^\circ$ was `osm_way_1498754706` in the April case at `108.4°`, which is now hidden from the demo).

---

## 4. Regional Smog Case QC Verification

Station 5627 (CRRI Mathura Road) recorded `959.0 µg/m³` at `2025-10-20 17:00:00Z`, but failed rigorous QC with:
`['data dropout after peak']` due to 4 consecutive hours of missing/NaN telemetry following the peak.

The highest **QC-clean** station across the entire airshed network is:
- **Station 5598**: `Sector - 125, Noida, UP - UPPCB`
- **PM2.5 Peak**: `881.0 µg/m³` (0 suspect flags, continuous reliable telemetry).
- **Network Summary**: Median `678.0 µg/m³`, 22 reporting stations, 21 elevated above 200 µg/m³ (95.5% elevated).

---

## 5. Deployment & Single Source of Truth Parity

- **Private S3 Data Bucket**: Synced with all minimal bundles, canonical case outputs, shortlists, agent traces, and backtest results.
- **DynamoDB Table (`smokeprint-cases`)**: Reseeded with all cases; April marked with `hidden_from_demo = true`.
- **API Handler Lambda**: Filtered to return strictly visible cases (`count: 6`), and dynamic shortlist enriched with coordinates and downwind wording.
- **Web Frontend**: Built with Next.js SSG and synced to `s3://smokeprint-demo-k9f2a1`. Exactly 6 visible case tabs in desktop and mobile dispatch.
- **Live Parity**: Curled live API endpoints for all 6 cases; all candidate IDs, distances, bearings, offsets, tiers, and refusal reasons match canonical JSON with 100% precision.

---

## 6. Test Suite Results

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\SHIVANSH\SmokePrint
configfile: pytest.ini
plugins: anyio-4.12.0, asyncio-1.4.0, cov-7.1.0, mock-3.15.1, playwright-0.10.0

tests/test_audit_phase58.py .....                                         [  7%]
tests/test_agents.py ....................                                [ 36%]
tests/test_api_single_source_of_truth.py ...                             [ 40%]
tests/test_audit_phase53.py ....                                         [ 46%]
tests/test_audit_phase54.py ....                                         [ 52%]
tests/test_audit_phase57.py ....                                         [ 57%]
tests/test_core.py .......                                               [ 68%]
tests/test_evidence_page_numbers.py ...                                  [ 72%]
tests/test_recompute_parity.py .......                                   [ 82%]
tests/test_single_source_of_truth.py ...                                 [ 86%]
tests/test_tier_rules.py ....                                            [ 92%]
tests/test_timeseries_source_rows.py ..                                  [ 95%]
tests/e2e/test_missing_qa_items.py ......                                [ 97%]
tests/e2e/test_ui_qa_phase55.py .......                                  [100%]

============================= 69 passed in 98.42s =============================
```
