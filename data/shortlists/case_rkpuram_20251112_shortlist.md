# Programmatic Inspection Shortlist: `case_rkpuram_20251112`

- **Station**: `R K Puram, Delhi - DPCC`
- **Timestamp (UTC)**: `2025-11-12T16:00:00Z`
- **Station Receptor Ambient Telemetry**: PM2.5 = `427.0 ug/m3`, PM10 = `549.0 ug/m3`, NO2 = `152.47 ug/m3`, CO = `None (excluded by QC: sensor unit mismatch)`
- **Local Excess Over Regional Baseline**: `+183.0 ug/m3` (Regional Baseline: `244.0 ug/m3`)
- **Meteorological Advection**: `wind from 263.0°` at `2.56 m/s`
- **Footprint Discriminability**: `0.84` (`discriminable_corridor`)
- **Attribution Classification**: `Multiple Comparable Candidates` (Nocturnal inversion, 44.1° candidate offset, and light wind prevent single-source isolation)

---

## Ranked Priority Candidates Table

| Rank | Candidate ID | Name | Category | Bearing | Distance | Operating Status | Confidence Tier |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1** | `osm_way_1366766563` | **Unnamed Construction Site** | `construction` | 66.0° | 0.28 km | `active_presumed` | **`low`** |
| **#2** | `osm_way_351800403` | **Unnamed Construction Site** | `construction` | 65.3° | 0.25 km | `active_presumed` | **`low`** |
| **#3** | `osm_node_5884780985` | **Unnamed Landfill Site** | `landfill` | 303.9° | 1.72 km | `active_presumed` | **`medium`** |
| **#4** | `osm_node_7150717314` | **Unnamed Landfill Site** | `landfill` | 304.8° | 2.17 km | `active_presumed` | **`medium`** |
| **#5** | `osm_node_7150717317` | **Unnamed Landfill Site** | `landfill` | 301.7° | 1.99 km | `active_presumed` | **`medium`** |
| **#6** | `outcome_insufficient_evidence` | **Insufficient Evidence (Diffuse Background / Low Discriminability)** | `insufficient_evidence` | N/A | N/A | `active_presumed` | **`medium`** |
| **#7** | `outcome_possible_fault` | **Instrument / Sensor Bias Artifact** | `possible_fault` | N/A | N/A | `active_presumed` | **`medium`** |

---

## Detailed Shortlist Specifications

### Rank #1: Unnamed Construction Site (`osm_way_1366766563`)
- **Category**: `construction`
- **Bearing & Distance**: `66.0°` at `0.28 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 0.28 km upwind from station along plume advection corridor., Plume footprint likelihood: 1.0000 (relative to peak corridor density)., Prior weight: 0.087 (heuristic, uncalibrated).`

### Rank #2: Unnamed Construction Site (`osm_way_351800403`)
- **Category**: `construction`
- **Bearing & Distance**: `65.3°` at `0.25 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 0.25 km upwind from station along plume advection corridor., Plume footprint likelihood: 1.0000 (relative to peak corridor density)., Prior weight: 0.087 (heuristic, uncalibrated).`

### Rank #3: Unnamed Landfill Site (`osm_node_5884780985`)
- **Category**: `landfill`
- **Bearing & Distance**: `303.9°` at `1.72 km`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 1.72 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.1919 (relative to peak corridor density)., Prior weight: 0.600 (heuristic, uncalibrated).`

### Rank #4: Unnamed Landfill Site (`osm_node_7150717314`)
- **Category**: `landfill`
- **Bearing & Distance**: `304.8°` at `2.17 km`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 2.17 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.1586 (relative to peak corridor density)., Prior weight: 0.600 (heuristic, uncalibrated).`

### Rank #5: Unnamed Landfill Site (`osm_node_7150717317`)
- **Category**: `landfill`
- **Bearing & Distance**: `301.7°` at `1.99 km`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 1.99 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.1586 (relative to peak corridor density)., Prior weight: 0.600 (heuristic, uncalibrated).`

---

*Generated programmatically by `core/ranking.py` & `scripts/generate_shortlist_markdown.py`. Strictly software-only inspection triage assistance.*