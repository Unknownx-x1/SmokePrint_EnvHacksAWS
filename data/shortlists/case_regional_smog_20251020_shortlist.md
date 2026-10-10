# Programmatic Inspection Shortlist: `case_regional_smog_20251020`

- **Station**: `Airshed Regional Baseline`
- **Timestamp (UTC)**: `2025-10-20T17:00:00Z`
- **Station Receptor Ambient Telemetry**: PM2.5 = `None ug/m3`, PM10 = `None ug/m3`, NO2 = `None ug/m3`, CO = `None (excluded by QC: sensor unit mismatch)`
- **Local Excess Over Regional Baseline**: `+0.0 ug/m3` (Regional Baseline: `678.0 ug/m3`)
- **Meteorological Advection**: `wind from 263.0°` at `2.56 m/s`
- **Footprint Discriminability**: `0.63` (`discriminable_corridor`)
- **Downwind Neighbour Corroboration**: `Vivek Vihar, Delhi - DPCC` at `2.82 km` (bearing `358.5°`), PM2.5 = `None ug/m3`
- **Attribution Classification**: `Multiple Comparable Candidates` (Nocturnal inversion, 44.1° candidate offset, and light wind prevent single-source isolation)

---

## Ranked Priority Candidates Table

| Rank | Candidate ID | Name | Category | Bearing | Distance | Operating Status | Confidence Tier |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1** | `outcome_regional` | **Airshed Regional Smog (No Point Source Dispatch)** | `regional` | N/A | N/A | `active_presumed` | **`high`** |
| **#2** | `outcome_insufficient_evidence` | **Insufficient Evidence for Local Inspection** | `insufficient_evidence` | N/A | N/A | `active_presumed` | **`medium`** |

---

## Detailed Shortlist Specifications

### Rank #1: Airshed Regional Smog (No Point Source Dispatch) (`outcome_regional`)
- **Category**: `regional`
- **Bearing & Distance**: `N/A` at `N/A`
- **Confidence Tier**: **`HIGH`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Widespread regional event: 95.5% of stations elevated above 150.0 ug/m3. Airshed median is 678.0 ug/m3. Regional smog event, no localized dispatch., Network-wide elevation across 95.5% of reporting stations., Regional median baseline is 678.0 ug/m3 with spread IQR 142.0 ug/m3.`

### Rank #2: Insufficient Evidence for Local Inspection (`outcome_insufficient_evidence`)
- **Category**: `insufficient_evidence`
- **Bearing & Distance**: `N/A` at `N/A`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Excess is statistically indistinguishable from broad regional background.`

---

*Generated programmatically by `core/ranking.py` & `scripts/generate_shortlist_markdown.py`. Strictly software-only inspection triage assistance.*