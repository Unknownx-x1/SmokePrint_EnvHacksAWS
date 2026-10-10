# Programmatic Inspection Shortlist: `case_gurugram_20260630`

- **Station**: `Vikas Sadan, Gurugram - HSPCB`
- **Timestamp (UTC)**: `2026-06-30T06:00:00Z`
- **Station Receptor Ambient Telemetry**: PM2.5 = `314.0 ug/m3`, PM10 = `523.0 ug/m3`, NO2 = `19.9 ug/m3`, CO = `None (excluded by QC: sensor unit mismatch)`
- **Local Excess Over Regional Baseline**: `+267.0 ug/m3` (Regional Baseline: `47.0 ug/m3`)
- **Meteorological Advection**: `wind from 263.0°` at `2.56 m/s`
- **Footprint Discriminability**: `0.72` (`discriminable_corridor`)
- **Attribution Classification**: `Multiple Comparable Candidates` (Nocturnal inversion, 44.1° candidate offset, and light wind prevent single-source isolation)

---

## Ranked Priority Candidates Table

| Rank | Candidate ID | Name | Category | Bearing | Distance | Operating Status | Confidence Tier |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1** | `outcome_possible_fault` | **Instrument / Telemetry Fault (constant_ratio_lock, collapse_after_peak)** | `possible_fault` | N/A | N/A | `active_presumed` | **`high`** |
| **#2** | `outcome_insufficient_evidence` | **Insufficient Evidence for Site Inspection** | `insufficient_evidence` | N/A | N/A | `active_presumed` | **`medium`** |

---

## Detailed Shortlist Specifications

### Rank #1: Instrument / Telemetry Fault (constant_ratio_lock, collapse_after_peak) (`outcome_possible_fault`)
- **Category**: `possible_fault`
- **Bearing & Distance**: `N/A` at `N/A`
- **Confidence Tier**: **`HIGH`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `PM2.5/PM10 ratio locked at 0.6000 for 4h then abrupt collapse to NaN. Instrument logger fault., Automatic QC fault detector fired: constant_ratio_lock, collapse_after_peak., Zero wind-consistent response observed at downwind CAAQMS stations.`

### Rank #2: Insufficient Evidence for Site Inspection (`outcome_insufficient_evidence`)
- **Category**: `insufficient_evidence`
- **Bearing & Distance**: `N/A` at `N/A`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Telemetry unreliability precludes physical emitter attribution.`

---

*Generated programmatically by `core/ranking.py` & `scripts/generate_shortlist_markdown.py`. Strictly software-only inspection triage assistance.*