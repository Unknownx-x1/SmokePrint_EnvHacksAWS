# Programmatic Inspection Shortlist: `case_anand_vihar_20251102`

- **Station**: `Anand Vihar, New Delhi - DPCC`
- **Timestamp (UTC)**: `2025-11-02T22:00:00Z`
- **Station Receptor Ambient Telemetry**: PM2.5 = `400.0 ug/m3`, PM10 = `536.0 ug/m3`, NO2 = `208.68 ug/m3`, CO = `None (excluded by QC: sensor unit mismatch)`
- **Local Excess Over Regional Baseline**: `+252.0 ug/m3` (Regional Baseline: `148.0 ug/m3`)
- **Meteorological Advection**: `wind from 268.0 deg` at `2.44 m/s`
- **Footprint Discriminability**: `0.25` (`discriminable_corridor`)
- **Downwind Neighbour Corroboration**: `Vivek Vihar, Delhi - DPCC` at `2.84 km` (bearing `358.5°`), PM2.5 = `380.0 ug/m3`
- **Attribution Classification**: `Multiple Comparable Candidates` (Nocturnal inversion, 44.1° candidate offset, and light wind prevent single-source isolation)

---

## Ranked Priority Candidates Table

| Rank | Candidate ID | Name | Category | Bearing | Distance | Operating Status | Confidence Tier |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1** | `osm_relation_3808258` | **Patparganj Industrial Area** | `industrial` | 218.9° | 0.86 km | `active_presumed` | **`medium`** |
| **#2** | `osm_way_464283162` | **Rajghat Bus Depot** | `industrial` | 265.5° | 6.15 km | `active_presumed` | **`medium`** |
| **#3** | `osm_way_464283160` | **Rajghat Thermal Power Station** | `industrial` | 260.2° | 6.05 km | `unverified_operating_status (decommissioned/disused)` | **`low`** |
| **#4** | `osm_way_464283150` | **Rajghat Thermal Power Station Flyash Dump** | `landfill` | 266.1° | 5.97 km | `unverified_operating_status (decommissioned/disused)` | **`low`** |
| **#5** | `osm_way_1544621569` | **Unnamed Industrial Site** | `industrial` | 255.7° | 9.07 km | `active_presumed` | **`medium`** |
| **#6** | `outcome_insufficient_evidence` | **Insufficient Evidence (Diffuse Background / Low Discriminability)** | `insufficient_evidence` | N/A | N/A | `active_presumed` | **`medium`** |
| **#7** | `outcome_possible_fault` | **Instrument / Sensor Bias Artifact** | `possible_fault` | N/A | N/A | `active_presumed` | **`medium`** |

---

## Detailed Shortlist Specifications

### Rank #1: Patparganj Industrial Area (`osm_relation_3808258`)
- **Category**: `industrial`
- **Bearing & Distance**: `218.9°` at `0.86 km`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 0.86 km upwind from station along plume advection corridor., Plume footprint likelihood: 1.0000 (relative to peak corridor density)., Prior weight: 0.295 (heuristic, uncalibrated).`

### Rank #2: Rajghat Bus Depot (`osm_way_464283162`)
- **Category**: `industrial`
- **Bearing & Distance**: `265.5°` at `6.15 km`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 6.15 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.6827 (relative to peak corridor density)., Prior weight: 0.295 (heuristic, uncalibrated).`

### Rank #3: Rajghat Thermal Power Station (`osm_way_464283160`)
- **Category**: `industrial`
- **Bearing & Distance**: `260.2°` at `6.05 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `unverified_operating_status (decommissioned/disused)`
- **Corroborating Evidence**: `Located 6.05 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.5962 (relative to peak corridor density)., Fine ratio (0.75) supports industrial combustion / furnace emissions.`

### Rank #4: Rajghat Thermal Power Station Flyash Dump (`osm_way_464283150`)
- **Category**: `landfill`
- **Bearing & Distance**: `266.1°` at `5.97 km`
- **Confidence Tier**: **`LOW`**
- **Operating Status**: `unverified_operating_status (decommissioned/disused)`
- **Corroborating Evidence**: `Located 6.04 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.6124 (relative to peak corridor density)., Candidate matches broad particulate emission profile.`

### Rank #5: Unnamed Industrial Site (`osm_way_1544621569`)
- **Category**: `industrial`
- **Bearing & Distance**: `255.7°` at `9.07 km`
- **Confidence Tier**: **`MEDIUM`**
- **Operating Status**: `active_presumed`
- **Corroborating Evidence**: `Located 9.07 km upwind from station along plume advection corridor., Plume footprint likelihood: 0.4135 (relative to peak corridor density)., Prior weight: 0.118 (heuristic, uncalibrated).`

---

*Generated programmatically by `core/ranking.py` & `scripts/generate_shortlist_markdown.py`. Strictly software-only inspection triage assistance.*