# Phase 1.5 Credibility Report: Prior Sensitivity, Score Decomposition & Validation

**Document Version**: 1.5 (Phase 1.5)  
**Scope**: Rigorous audit and credibility fixes for source ranking, low-wind dispersion, operating status, computed bootstrap intervals, fault-detector validation, and unit normalization.

---

## 1. Three-Way Ranking Comparison

Every vetted case evaluated under three regimes:
1. **Heuristic Priors**: Integrates source baseline, assumed kiln seasonality, diurnal modifiers, geometric area dilution, and operating-status penalties.
2. **Flat Priors**: Sets prior weight $W(\text{source}) = 1.0$ uniformly across all candidate sites.
3. **Footprint Only**: Ranks purely by plume dispersion residence density ($L_{\text{fp}}$), setting prior, signature, and satellite multipliers to 1.0.

| Case ID | Event Label | Top Hypothesis (Heuristic) | Score | Top Hypothesis (Flat) | Score | Top Hypothesis (Footprint Only) | Rank Shift? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_crri_20260515` | `possible_fault` | Instrument / Telemetry Fau | 0.93 | Instrument / Telemetry Fau | 0.93 | Okhla Ph III | No |
| `case_anand_vihar_20260405` | `local` | Unnamed Landfill Site | 0.24 | Unnamed Industrial Site | 0.29 | Unnamed Industrial Site | **YES** |
| `case_gurugram_20260630` | `possible_fault` | Instrument / Telemetry Fau | 0.93 | Instrument / Telemetry Fau | 0.93 | Unnamed Industrial Site | No |
| `case_regional_smog_20251020` | `regional` | Airshed Regional Smog (No  | 0.95 | Airshed Regional Smog (No  | 0.95 | Unnamed Industrial Site | No |
| `case_rkpuram_20251112` | `local` | Unnamed Landfill Site | 0.21 | Unnamed Construction Site | 0.24 | Unnamed Construction Site | **YES** |
| `case_anand_vihar_20251102` | `local` | Patparganj Industrial Area | 0.28 | Patparganj Industrial Area | 0.29 | Patparganj Industrial Area | No |
| `case_anand_vihar_20260131` | `local` | Unnamed Industrial Site | 0.25 | Unnamed Industrial Site | 0.35 | Unnamed Industrial Site | No |

---

## 2. January 2026 Anand Vihar Case: Detailed Score Decomposition

### The Question
*Why does the January 31, 2026 Anand Vihar footprint overlap Ghazipur Landfill, yet the top ranked hypothesis is a Sahibabad industrial site?*

### Quantitative Decomposition
At `2026-01-31 05:00 UTC` (10:30 IST), ERA5 10m wind was light ($1.19\text{ m/s}$) from $105.0^\circ$ (East-Southeast):
* **Sahibabad Industrial Plot (`osm_way_1498754706`)**:
  - Distance from station: **0.69 km**
  - Compass bearing from station: **$95.9^\circ$**
  - Angular deviation from wind vector: $|95.9^\circ - 105.0^\circ| = \mathbf{9.1^\circ}$ (dead-center of the upwind plume core)
  - Footprint Likelihood: **1.000** (normalized peak corridor density)
  - Prior Weight: **0.118** (diffuse industrial plot with geometry penalty)
  - Chemical Signature Multiplier: **1.625** (fine ratio $0.70$ + high $NO_2 = 103.2\text{ }\mu\text{g/m}^3$)
  - Raw Compound Score: $0.118 \times 1.000 \times 1.625 \times 1.0 = \mathbf{0.1917}$

* **Ghazipur Landfill (`osm_way_76727509`)**:
  - Distance from station: **2.79 km**
  - Compass bearing from station: **$156.4^\circ$**
  - Angular deviation from wind vector: $|156.4^\circ - 105.0^\circ| = \mathbf{51.4^\circ}$ (wide off-axis)
  - Footprint Likelihood: **0.110** (under widened calm-wind dispersion $\sigma_\theta = 45^\circ$)
  - Prior Weight: **0.850** (major named landfill base weight)
  - Chemical Signature Multiplier: **1.450** (combustion fine ratio)
  - Raw Compound Score: $0.850 \times 0.110 \times 1.450 \times 1.0 = \mathbf{0.1356}$

### Plain-Language Summary
Ghazipur Landfill has a far higher base prior weight ($0.850$ vs $0.118$). However, because Ghazipur is located $51.4^\circ$ South-Southeast of the station, whereas the wind was blowing from $105^\circ$ East-Southeast, Ghazipur sits on the outer flank of the transport plume. The Sahibabad plot is only 690 meters due east ($9.1^\circ$ off-center), placing it squarely in the advective core.
Under low-wind handling ($\sigma_\theta = 45^\circ$), Ghazipur's likelihood increases from near-zero to rank as a strong competitor (#2), but the physical proximity and wind alignment of the Sahibabad plot slightly edge it out.

---

## 3. Low-Wind Handling & Footprint Discriminability

Under stagnant conditions ($s < 1.5\text{ m/s}$), mechanical wind direction meanders erratically over wide angles:
- **Normal Wind Regime ($s \ge 1.5\text{ m/s}$)**: $\sigma_\theta = 15.0^\circ$, $\sigma_s/s = 0.20$, $K_h = 10.0\text{ m}^2/\text{s}$.
- **Low-Wind Calm Regime ($s < 1.5\text{ m/s}$)**:
  - $\sigma_\theta = \mathbf{45.0^\circ}$ (3x widened Gaussian direction turbulence).
  - $\sigma_s/s = \mathbf{0.40}$ (doubled relative speed noise).
  - $K_h = \mathbf{25.0\text{ m}^2/\text{s}}$ (enhanced sub-grid eddy diffusion).

### Footprint Discriminability Metric
For every case, the metric $\Delta_{\text{top5}} = \frac{d_{\text{top1}} - d_{\text{top5}}}{d_{\text{top1}}}$ measures whether the plume creates a distinct directional corridor or a near-uniform stagnant pancake:
- If $\Delta_{\text{top5}} < 0.25$ (top-5 candidate densities within 25% of each other): Output flags `multiple_comparable_candidates`, lowers the confidence tier to `low`, and elevates `outcome_insufficient_evidence`.
- **Cases Affected**: Case 2 (0.97 m/s), Case 4 (0.89 m/s), Case 5 (1.17 m/s), and Case 7 (1.19 m/s) trigger low-wind dispersion broadening. Case 4 (Diwali) and Case 5 exhibit lower discriminability, correctly reflecting diffuse winter stagnation.

---

## 4. Operating Status Check & Rajghat Power Station Audit

### Decommissioned & Disused Sites
OSM tags were audited for lifecycle prefixes (`disused:*`, `abandoned:*`, `demolished:*`, `historic:*`).
- **Rajghat Thermal Power Station (`osm_way_464283160`)**:
  - OSM Tag: `disused:power=plant`, `plant:source=coal`.
  - Historical reality: Rajghat coal power plant was permanently decommissioned in 2015 to combat Delhi particulate pollution.
  - **Action**: Identified by the lifecycle parser, flagged as `unverified_operating_status (decommissioned/disused)`, and assigned a **0.05x penalty** ($95\%$ reduction).
  - **Result**: In Case 6 (Anand Vihar Winter), Rajghat's rank collapses from Rank #1 down to bottom rank, preventing erroneous inspection dispatch to a non-operational coal plant.
- Total disused sites flagged across NCR catalog: **23 candidates** (including Badarpur Thermal Power Station and 20 disused quarries).

---

## 5. Interval Honesty & Empirical Bootstrap

Static hardcoded intervals (such as previous constant `0.91 [0.85, 0.96]`) have been removed.
- **Empirical Monte Carlo Bootstrap ($B = 30$ iterations)**:
  Each interval $[q_{10}, q_{90}]$ is computed by sampling:
  1. Wind direction and speed perturbations ($\sigma_\theta, \sigma_s$).
  2. Regional background uncertainty via bootstrap resampling of reporting CAAQMS stations.
  3. Chemical signature uncertainty ($\pm 15\%$ multiplicative lognormal variation).
- **Confidence Tiers**:
  - `high`: Spread $\le 0.15$ with top score $\ge 0.35$ and directional wind.
  - `medium`: Spread $\le 0.30$.
  - `low`: Spread $> 0.30$ or low-wind discriminability $< 0.25$.

---

## 6. Fault Detector Validation & Hold-Out Testing

### Breakdown of 3,626 `collapse_after_peak` Hours
- **NaN Gaps (Telemetry Dropouts)**: **1,039 instances (97.0%)**.
  Sensors operating at peak levels where logger transmission abruptly dropped to `NaN` for $\ge 2$ consecutive hours.
- **Near-Zero Drops**: **32 instances (3.0%)**.
  Physical crashes where concentration collapsed from $\ge 200\text{ }\mu\text{g/m}^3$ to $\le 5.0\text{ }\mu\text{g/m}^3$ within 1 hour.
- **Expansion Buffer**: Multi-hour suspect expansion ($\pm 1$h around crash) accounts for the 3,626 total suspect hours. Boundary artifacts in small slices have been fixed by requiring at least 2 consecutive NaN hours and slice boundary exclusion.

### Hold-Out Testing on 10 Untouched Stations
Synthetic faults were injected into clean periods of 10 hold-out stations (excluding tuning stations 50, 301, 5627, 235, 17):
- **Synthetic Constant Ratio (0.6000 for 4h)**: **10 / 10 detected (Recall = 100.0%)**
- **Synthetic Peak Collapse (450 to 0 ug/m3)**: **10 / 10 detected (Recall = 100.0%)**
- **Synthetic Frozen Float (185.4 ug/m3 for 4h)**: **10 / 10 detected (Recall = 100.0%)**
- **False Positive Rate on Untouched Healthy Windows**: **7.60%** of total hours flagged as suspect.

### Punjabi Bagh Classification
- Reworded explicitly as: **"unverified hypothesis (possible BAM channel desynchronization during dust surge)"**. Confirmed deterministically only as a direct physical $PM_{2.5} > PM_{10}$ violation ($PM_{2.5} = 628.0, PM_{10} = 374.0$).
