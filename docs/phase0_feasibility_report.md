# Phase 0 Data Feasibility Report: Delhi-NCR Airshed

**Project**: Smokeprint (AWS x WeMakeDevs Hackathon — Air Track)  
**Execution Timestamp**: 2026-10-08  
**Airshed Bounding Box**: `[28.20°N, 76.70°E]` to `[28.95°N, 77.60°E]`  
**Verification Window**: 2026-04-01T00:00:00Z to 2026-10-01T00:00:00Z (183 days / 4,392 hourly slots)  

---

## 1. OpenAQ Monitoring Station Coverage & Gate Check

- **Total Operational Stations in Delhi-NCR**: 84 active stations identified across CPCB, DPCC, HSPCB, UPPCB, and IMD networks.
- **Stations Evaluated with Timeseries Pull**: 35 representative stations across Delhi, Gurugram, Noida, Ghaziabad, Faridabad, and Greater Noida.
- **Coverage Criteria**: $\ge 80\%$ valid hourly readings over the 6-month period ($\ge 3,514$ hours).

### Summary Statistics
| Metric | Count | % of Evaluated |
| :--- | :--- | :--- |
| Stations with **PM2.5 $\ge 80\%$ coverage** | **28** | **80.0%** |
| Stations with **PM2.5 & PM10 $\ge 80\%$ coverage** | **20** | **57.1%** |
| Stations with **all 4 pollutants (PM2.5, PM10, NO2, CO) $\ge 80\%$ coverage** | **15** | **42.9%** |

### Top Exemplar Stations (85%–93% Full Coverage)
- **Sector 62, Noida (UPPCB, ID 5616)**: PM2.5 = 93.35%, PM10 = 93.49%
- **CRRI Mathura Road (CPCB, ID 5627)**: PM2.5 = 93.33%, PM10 = 92.51%
- **DTU, New Delhi (CPCB, ID 5626)**: PM2.5 = 91.53%, PM10 = 91.87%
- **Punjabi Bagh, Delhi (DPCC, ID 50)**: PM2.5 = 88.50%, PM10 = 89.78%, NO2 = 90.53%, CO = 90.51%
- **R K Puram, Delhi (DPCC, ID 17)**: PM2.5 = 88.09%, PM10 = 88.16%, NO2 = 90.10%, CO = 88.89%
- **Anand Vihar, New Delhi (DPCC, ID 235)**: PM2.5 = 87.23%, PM10 = 83.67%, NO2 = 88.50%, CO = 86.98%

> **GATE DECISION: PASSED**  
> Required: $\ge 25$ usable stations. Observed: **28 stations** with $\ge 80\%$ coverage across the 6-month window.

---

## 2. Meteorological & Satellite Fire Data Feasibility

### Open-Meteo ERA5 Reanalysis
- **Endpoint**: `https://archive-api.open-meteo.com/v1/archive`
- **Hours Ingested**: 4,392 continuous hours (100% complete).
- **Extracted Variables**:
  - `wind_speed_10m` (converted to m/s)
  - `wind_direction_10m` (meteorological degrees)
  - Horizontal wind vectors ($u, v$ in m/s)
  - `boundary_layer_height` (meters, critical for mixing volume calculations)
  - `surface_pressure` (hPa)
- **Storage Location**: `data/wind_hourly_6m.json`

### NASA FIRMS Thermal Anomalies
- **Sensor**: VIIRS S-NPP (375m resolution) via NASA FIRMS API.
- **Detections in NCR Bbox**: 49 verified thermal hotspots with coordinates, brightness temperature ($T_{i4}$), Fire Radiative Power (FRP in MW), and confidence ratings.
- **Storage Location**: `data/firms_fires_6m.json`

---

## 3. OpenStreetMap Candidate Emitters Catalog

Extracted via Overpass API within the Delhi-NCR bounding box:
- **Total Candidate Emitter Sites**: **1,212**
- **Catalog Breakdown**:
  - **Industrial facilities & zones**: 670
  - **Active construction sites**: 289
  - **Landfills & waste transfer stations**: 111 (e.g., Ghazipur, Bhalswa, Okhla)
  - **Brick kilns**: 105 (Baghpat, Jhajjar, and Ghaziabad belts)
  - **Quarries / mining areas**: 37
- **Storage Location**: `data/osm_candidates.json` (includes centroid lat/lon, OSM ID, and tags).

---

## 4. Real Spike Case Extraction

- **Station**: Punjabi Bagh, Delhi — DPCC (Station ID: 50)
- **Event Peak**: 2026-04-28 05:00:00 UTC
- **Station PM2.5**: 628.0 µg/m³
- **Regional Background (Median of 35 Stations)**: 63.5 µg/m³
- **Attributable Local Excess**: **+564.5 µg/m³**
- **Co-Pollutant Signature**: PM2.5/PM10 ratio of 1.68 (intense combustion/smoke signature)
- **Verification Plot**: `docs/real_spike_feasibility_plot.png`
