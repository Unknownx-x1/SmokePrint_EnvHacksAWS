# Programmatic Inspection Shortlist: `case_anand_vihar_20260131`

- **Station**: `Anand Vihar, New Delhi - DPCC`
- **Timestamp (UTC)**: `2026-01-31T05:00:00Z`
- **Station Receptor Ambient Telemetry**: PM2.5 = `345.0 ug/m3`, PM10 = `491.0 ug/m3`, NO2 = `103.21 ug/m3`, CO = `None (excluded by QC: sensor unit mismatch)`
- **Local Excess Over Regional Baseline**: `+143.0 ug/m3` (Regional Baseline: `202.0 ug/m3`)
- **Meteorological Advection**: `wind from 263.0°` at `2.56 m/s`
- **Footprint Discriminability**: `0.69` (`discriminable_corridor`)
- **Downwind Neighbour Corroboration**: `Vivek Vihar, Delhi - DPCC` at `2.84 km` (bearing `358.5°`), PM2.5 = `377.0 ug/m3`
- **Attribution Classification**: `Multiple Comparable Candidates` (Nocturnal inversion, 44.1° candidate offset, and light wind prevent single-source isolation)

---

## Ranked Priority Candidates Table

| Rank | Candidate ID | Name | Category | Bearing | Distance | Operating Status | Confidence Tier |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1** | `osm_way_1498754706` | **Unnamed Industrial Site** | `industrial` | 94.4° | 0.69 km | `active_presumed` | **`low`** |
| **#2** | `osm_way_287054784` | **Unnamed Industrial Site** | `industrial` | 177.8° | 0.74 km | `active_presumed` | **`low`** |
| **#3** | `osm_way_287054788` | **Unnamed Industrial Site** | `industrial` | 180.0° | 0.71 km | `active_presumed` | **`low`** |
| **#4** | `osm_way_802304540` | **Unnamed Industrial Site** | `industrial` | 82.5° | 1.45 km | `active_presumed` | **`low`** |
| **#5** | `osm_way_661784209` | **Unnamed Industrial Site** | `industrial` | 70.1° | 1.10 km | `active_presumed` | **`low`** |
| **#6** | `outcome_insufficient_evidence` | **Insufficient Evidence (Diffuse Background / Low Discriminability)** | `insufficient_evidence` | N/A | N/A | `active_presumed` | **`medium`** |
| **#7** | `outcome_possible_fault` | **Instrument / Sensor Bias Artifact** | `possible_fault` | N/A | N/A | `active_presumed` | **`medium`** |

---

## Detailed Shortlist Specifications

### Rank #1: Unnamed Industrial Site (`osm_way_1498754706`)
- **Category**: `industrial`
- **Bearing & Distance**: `94.4°` at `0.69 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 0.69 km upwind from station along plume advection corridor., Plume footprint likelihood: 1.0000 (relative to peak corridor density)., Prior weight: 0.118 (heuristic, uncalibrated).`

### Rank #2: Unnamed Industrial Site (`osm_way_287054784`)
- **Category**: `industrial`
- **Bearing & Distance**: `177.8°` at `0.74 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 0.74 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.4681 (relative to peak corridor density)., Prior weight: 0.118 (heuristic, uncalibrated).`

### Rank #3: Unnamed Industrial Site (`osm_way_287054788`)
- **Category**: `industrial`
- **Bearing & Distance**: `180.0°` at `0.71 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 0.71 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.4681 (relative to peak corridor density)., Prior weight: 0.118 (heuristic, uncalibrated).`

### Rank #4: Unnamed Industrial Site (`osm_way_802304540`)
- **Category**: `industrial`
- **Bearing & Distance**: `82.5°` at `1.45 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 1.45 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.3690 (relative to peak corridor density)., Prior weight: 0.118 (heuristic, uncalibrated).`

### Rank #5: Unnamed Industrial Site (`osm_way_661784209`)
- **Category**: `industrial`
- **Bearing & Distance**: `70.1°` at `1.10 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 1.1 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.3131 (relative to peak corridor density)., Prior weight: 0.118 (heuristic, uncalibrated).`

---

*Generated programmatically by `core/ranking.py` & `scripts/generate_shortlist_markdown.py`. Strictly software-only inspection triage assistance.*