# SmokePrint: Atmospheric Dispersion Decision Support and Field Triage Engine

SmokePrint is an operational decision support system designed for municipal environmental protection agencies and air quality inspection teams operating in the National Capital Region (Delhi-NCR). It bridges the gap between ambient continuous air quality monitoring (CAAQMS) telemetry and field enforcement by combining Lagrangian atmospheric dispersion modeling, multi-pollutant chemical signature gating, automated telemetry fault detection, and geospatial infrastructure validation.

The system evaluates ambient particulate surges in real time to determine whether an inspection dispatch is physically warranted, while automatically standing down field teams during instrument logger failures, regional weather inversions, and non-combustion dust events.

---

## 1. System Architecture and Cloud Infrastructure

SmokePrint is deployed as a serverless, decoupled architecture on Amazon Web Services (AWS) operating within Free Tier resource boundaries.

```
+-----------------------------------------------------------------------------------+
| CLIENT AND EDGE LAYER                                                             |
|                                                                                   |
|  [ CloudFront CDN (Global Edge Caching, TLS Termination, Brotli Compression) ]    |
|                                   |                                               |
|                    +--------------+--------------+                                |
|                    |                             |                                |
|                    v                             v                                |
|         [ S3 Static Website ]          [ OpenFreeMap Vector Tiles ]               |
|       Next.js 15 App Export             Self-hosted / Keyless Tile Grid           |
+-----------------------------------------------------------------------------------+
                                    |
                                    v HTTPS
+-----------------------------------------------------------------------------------+
| AWS SERVERLESS INGESTION AND ORCHESTRATION LAYER                                  |
|                                                                                   |
|  [ AWS API Gateway (HTTP API v2) ] ──> [ ApiFunction Lambda (Python 3.12) ]       |
|                                                     |                             |
|                                                     v                             |
|                           [ AWS Step Functions Workflow Engine ]                  |
|                                                     │                             |
|           +───────────────────┬─────────────────────┼───────────────────+         |
|           v                   v                     v                   v         |
|   (Task 1: LoadBundle) (Task 2: RunCore)   (Task 3: AgentReview) (Task 4: Store)  |
+-----------------------------------------------------------------------------------+
                                    │
                                    v
+-----------------------------------------------------------------------------------+
| DATA PERSISTENCE AND LOCAL AGENT LAYER                                            |
|                                                                                   |
|  [ Amazon DynamoDB ]                   [ Strands Agents SDK Execution Loop ]      |
|    - Table: smokeprint-cases             - Adversarial Critic Agent               |
|    - Table: smokeprint-runs              - Local Llama-3.2 Context Verification   |
|                                          - Deterministic Validation Barrier       |
|  [ Amazon S3 Data Bucket ]                                                        |
|    - s3://smokeprint-data-* (Canonical cases, ERA5 wind grids, 12m baselines)     |
+-----------------------------------------------------------------------------------+
```

### 1.1 Infrastructure Components

| Infrastructure Component | AWS Service | Configuration Specification |
|---|---|---|
| Edge Distribution | Amazon CloudFront | TLS 1.3 termination, HTTP/2, automated edge gzip/brotli compression, global S3 origin caching. |
| Web Application Hosting | Amazon S3 Static Hosting | Next.js 15 static export (`web/out/`), zero-compute client pre-rendering. |
| API Gateway | AWS HTTP API (v2) | CORS-enabled, low-latency payload passthrough to Python execution environments. |
| Compute Runtime | AWS Lambda | Python 3.12 runtime, 512 MB memory allocation, sub-100ms cold start optimization. |
| State Orchestration | AWS Step Functions | Standard State Machine: `LoadBundle` -> `RunCore` -> `AgentReview` -> `StoreRun`. |
| Primary Storage | Amazon DynamoDB | On-Demand capacity mode, tables `smokeprint-cases` (partition: `case_id`) and `smokeprint-runs` (partition: `run_id`). |
| Object Storage | Amazon S3 | Data storage bucket for canonical case JSONs, ERA5 reanalysis fields, and backtest archives. |
| Vector Base Maps | OpenFreeMap / MapLibre GL | Keyless, privacy-preserving vector and raster tiles without proprietary API dependencies. |

### 1.2 Execution Provenance and Governance Standards

1. Replay Standard: All Step Functions executions and API recompute endpoints serve deterministic, precomputed, and validated artifacts declaring `source: "replayed"` and `mode: "replayed_from_canonical_output"`.
2. Credential Sanitization: Outgoing responses pass through sanitization middleware that strips raw AWS account identifiers, IAM role names, and Resource Names (ARNs).
3. Cost and Compute Bounds: Real-time agent reviews utilize a lightweight local execution loop via the Strands Agents SDK with deterministic validator barriers, preventing unconstrained cloud inference expenditure.

---

## 2. Mathematical Methodology and Dispersion Physics

### 2.1 Backward-in-Time Lagrangian Plume Dispersion

SmokePrint evaluates atmospheric advection using a Lagrangian particle dispersion model coupled to hourly ECMWF ERA5 reanalysis fields (zonal wind component $u$, meridional wind component $v$, and planetary boundary layer height $z_{pbl}$).

For each episode, an ensemble of $N = 500$ numerical particles is released at the receptor monitoring station $(x_0, y_0, z_0)$ at time $t_0$ and integrated backward in time over integration steps $\Delta t = 60\text{ s}$ up to a maximum domain radius $R_{max} = 15\text{ km}$:

$$x(t - \Delta t) = x(t) - \left[ \bar{u}(z, t) + u'(t) \right] \Delta t$$

$$y(t - \Delta t) = y(t) - \left[ \bar{v}(z, t) + v'(t) \right] \Delta t$$

Turbulent velocity perturbations $(u', v')$ are parameterized using stochastic Gaussian Markov processes constrained by atmospheric stability regimes:

* Normal Advection Regime ($\bar{s} \ge 1.5\text{ m/s}$):
  * Directional perturbation standard deviation: $\sigma_\theta = 15.0^\circ$ ($0.2618\text{ rad}$)
  * Relative wind speed perturbation standard deviation: $\sigma_s / \bar{s} = 0.20$
  * Horizontal sub-grid eddy diffusivity: $K_h = 10.0\text{ m}^2/\text{s}$
* Low Wind / Nocturnal Meandering Regime ($\bar{s} < 1.5\text{ m/s}$):
  * Directional perturbation standard deviation: $\sigma_\theta = 45.0^\circ$ ($0.7854\text{ rad}$)
  * Relative wind speed perturbation standard deviation: $\sigma_s / \bar{s} = 0.40$
  * Horizontal sub-grid eddy diffusivity: $K_h = 25.0\text{ m}^2/\text{s}$

Horizontal Brownian random walk displacement per integration step is computed as:

$$\Delta r_{turb} = \sqrt{2 K_h \Delta t} \cdot \mathcal{N}(0, 1)$$

Vertical advection is bounded by the nocturnal planetary boundary layer ceiling:

$$0 \le z(t) \le z_{pbl}(t)$$

Spatial footprint densities are accumulated on a discrete Cartesian grid with cell resolution $\Delta x = \Delta y = 250\text{ m}$. The footprint density $D(x, y)$ represents the residence-time integral of backward particles traversing grid cell $(x, y)$.

### 2.2 Bayesian Hypothesis Ranking and Score Decomposition

Candidate industrial, landfill, and commercial emission sources cataloged in OpenStreetMap are scored against the spatial footprint using posterior probability decomposition:

$$P(H_i \mid \text{data}) \propto P(H_i) \cdot P(\text{footprint} \mid H_i) \cdot P(\text{signature} \mid H_i) \cdot F_{\text{status}}(H_i)$$

Where:
* $P(H_i)$ is the baseline source prior based on facility type, licensed stack count, and baseline capacity.
* $P(\text{footprint} \mid H_i)$ is the spatial likelihood derived from the normalized particle residence-time density $D(x_i, y_i)$ at the candidate centroid.
* $P(\text{signature} \mid H_i)$ is the chemical profile likelihood evaluated against observed $PM_{2.5} / PM_{10}$ ratios and thermal $NO_x$ co-emissions.
* $F_{\text{status}}(H_i)$ is the operating status verification factor derived from OpenStreetMap lifecycle tagging:
  * Active facilities: $F_{\text{status}} = 1.0$
  * Decommissioned, disused, or historic facilities (e.g. `disused:power=plant`): $F_{\text{status}} = 0.05$

Candidates within the top footprint density percentile are partitioned into confidence tiers:
* High Confidence (Tier 1): Upwind offset $\Delta \theta \le 25^\circ$, active operational status, elevated chemical signature alignment.
* Medium Confidence (Tier 2): Offset $25^\circ < \Delta \theta \le 45^\circ$, or unclassified industrial zoning.
* Low Confidence (Tier 3): Offset $\Delta \theta > 45^\circ$, or facilities verified as decommissioned/disused.

---

## 3. Automated Quality Control and Refusal Detectors

SmokePrint enforces deterministic refusal gates to prevent improper enforcement dispatches. An episode triggering any refusal condition is assigned `dispatch_refused: true`, halting field routing.

```
+---------------------------------------------------------------------------------------+
| SENSOR TELEMETRY TIME-SERIES                                                          |
+---------------------------------------------------------------------------------------+
        │
        ├─── Ratio Lock Check: |r(t) - r(t-1)| <= 0.005 for >= 3h? ──> [INSTRUMENT FAULT REFUSAL]
        │
        ├─── Negative Delta / Unphysical: PM2.5 > 1.05 * PM10 + 5?  ──> [INSTRUMENT FAULT REFUSAL]
        │
        ├─── Post-Surge Collapse: Peak >= 200 dropped to <= 5 or NaN?─> [INSTRUMENT FAULT REFUSAL]
        │
        ├─── Regional Synchrony: >= 90% NCR monitors elevated?       ──> [REGIONAL SMOG REFUSAL]
        │
        └─── Size Fraction Gate: PM2.5 / PM10 < 0.25?               ──> [COARSE DUST REFUSAL]
        │
        └─── [ALL GATES PASSED] ──> Proceed to Plume Dispersion and Candidate Triage
```

### 3.1 Instrument Hardware Fault Detectors

1. Unphysical Ratio Violation: Flags instances where fine particulate concentration exceeds total particulate concentration beyond sensor measurement tolerance:

   $$PM_{2.5}(t) > 1.05 \cdot PM_{10}(t) + 5.0\ \mu\text{g/m}^3$$

2. Constant Ratio Lock (Firmware Synthesis): Detects optical or electrical logger locks where the reported $PM_{2.5} / PM_{10}$ ratio remains static across consecutive hours:

   $$\max_{k \in [0, K-1]} |r(t - k) - \bar{r}| \le 0.005, \quad K \ge 3\text{ hours}, \quad PM_{10} \ge 25\ \mu\text{g/m}^3$$

3. Post-Surge Telemetry Collapse: Catches sensor burnout or channel dropouts where extreme particulate surges are immediately followed by null, negative, or near-zero readings:

   $$PM_{10}(t_{peak}) \ge 200\ \mu\text{g/m}^3 \implies PM_{10}(t_{peak} + 1\text{h}) \le 5\ \mu\text{g/m}^3 \text{ or } \text{NaN}$$

4. Stuck High Float (Inlet Jam): Identifies frozen telemetry channels reporting identical floating-point values over extended intervals during high concentration regimes ($K \ge 3\text{ hours}$).

### 3.2 Airshed Regional Inversion Gate

To distinguish localized emission plumes from basin-wide meteorological inversions, SmokePrint evaluates background telemetry across the entire Delhi-NCR CAAQMS network ($n = 34$ stations).

Let $S_{active}$ denote the set of reporting stations at observation time $t_0$, and $M_{reg}$ denote the regional median $PM_{2.5}$ concentration across all $s \in S_{active}$. If:

$$\frac{\sum_{s \in S_{active}} \mathbb{I}\left(PM_{2.5, s} \ge \tau_{regional}\right)}{|S_{active}|} \ge 0.90$$

the episode is classified as an Airshed-Wide Regional Smog Event. Municipal dispatch to individual facility gates is refused, and the incident is flagged for airshed-level advisory.

### 3.3 Particle Size Distribution Gate

* Fine Combustion Regime ($PM_{2.5} / PM_{10} \ge 0.50$): Indicates secondary aerosol formation or direct combustion emissions (industrial boilers, waste fires, biomass burning).
* Intermediate Mixed Regime ($0.25 \le PM_{2.5} / PM_{10} < 0.50$): Mixed fugitive dust and urban vehicular background.
* Coarse Mechanical Regime ($PM_{2.5} / PM_{10} < 0.25$): Dominance of mechanical dust resuspension, construction aggregate drift, or transboundary sandstorms. Triggers Coarse Dust Refusal, preventing combustion stack inspections.

---

## 4. Canonical Delhi-NCR Episodes

All baseline concentrations, meteorological parameters, and sensor readings originate directly from raw gzip records in the public AWS Open Data OpenAQ archive (`s3://openaq-data-archive/`):

| Case Identifier | Station Name | Time Window (IST) | Peak PM2.5 | PM10 | PM2.5/PM10 | Decision State | Diagnostic Rationale |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| `case_anand_vihar_20251102` | Anand Vihar (DPCC) | 2025-11-03 03:30 | 400.0 | 536.0 | 0.746 | DISPATCH SHORTLIST | Westerly advection (268 deg, 2.44 m/s). Shortlisted Patparganj and Rajghat Bus Depot. Decommissioned power plant filtered. |
| `case_anand_vihar_20260131` | Anand Vihar (DPCC) | 2026-01-31 11:30 | 359.0 | 511.0 | 0.703 | DISPATCH SHORTLIST | Winter nocturnal combustion plume. Downwind transport corroborated at Vivek Vihar (338.0 ug/m3). |
| `case_rkpuram_20251112` | RK Puram (DPCC) | 2025-11-12 21:30 | 501.0 | 639.0 | 0.784 | DISPATCH SHORTLIST | Elevated combustion index (0.784). Downwind transport corroborated at JLN Stadium (482.0 ug/m3). |
| `case_crri_20260515` | CRRI Mathura Rd (IMD) | 2026-05-16 05:30 | 180.7 | 1437.9 | 0.126 | REFUSED (COARSE DUST) | Mechanical resuspension surge. PM2.5/PM10 ratio (0.126) is below combustion threshold (0.25). |
| `case_gurugram_20260630` | Vikas Sadan (HSPCB) | 2026-06-30 12:30 | 332.0 | 553.4 | 0.600 | REFUSED (LOGGER FAULT) | Sensor firmware locked at constant 0.6000 ratio for 10 hours, followed by complete channel collapse. |
| `case_regional_smog_20251020` | Sector 125, Noida (UPPCB) | 2025-10-20 23:30 | 881.0 | 1043.0 | 0.845 | REFUSED (REGIONAL SMOG)| Network-wide regional smog event. 31 of 34 reporting stations concurrently elevated across airshed. |

---

## 5. Empirical Validation and Backtest Ablation

To evaluate triage stability against dispersion uncertainties, SmokePrint was evaluated across an ablation suite consisting of 500 semi-synthetic plume injection trials in authentic Delhi-NCR atmospheric background conditions with perturbed wind fields, boundary layer heights, and Pasquill stability classes:

### 500-Trial Dispersion Mismatch Ablation (95% Bootstrap Confidence Intervals)

| Candidate Scoring Variant | Precision @ 1 (95% CI) | Precision @ 3 (95% CI) | Cluster P @ 3 (95% CI) | Methodological Description |
|---|:---:|:---:|:---:|---|
| Nearest-Upwind Baseline | 34.4% [30.4%, 38.8%] | 60.0% [55.6%, 64.4%] | 71.0% [66.6%, 74.8%] | Standard distance-weighted upwind heuristic |
| Forward-Plume Likelihood Only | 54.4% [49.8%, 58.8%] | 72.8% [68.8%, 76.4%] | 79.4% [75.8%, 82.8%] | Gaussian forward plume advection kernel |
| SmokePrint Production Pipeline | 54.4% [50.0%, 58.6%] | 72.2% [68.2%, 76.0%] | 78.4% [74.6%, 81.8%] | Full pipeline: Plume Footprint x Signature Gating x OSM Status Filter |

### Fault Detector Validation Metrics

* Injected Fault Recall: 100.0% (30 of 30 synthetic injection scenarios correctly detected and isolated).
* Untouched Clean Window False Positive Rate: 0.0% (0 of 10 pre-screened clean reference monitoring days incorrectly flagged).
* Target Failure Modes: Constant ratio lock, telemetry step collapse, frozen float, unphysical inversion.

Note on Evaluation Scope: Synthetic evaluations demonstrate algorithmic stability, footprint convergence, and mathematical resilience against turbulent perturbation; they do not replace direct physical stack monitoring or continuous reference sensor recalibration.

---

## 6. Directory Layout and Repository Structure

```
SmokePrint/
├── core/                       # Frozen deterministic physics and dispersion algorithms
│   ├── plume.py                # Lagrangian backward particle dispersion engine
│   ├── ranking.py              # Bayesian hypothesis ranking and score decomposition
│   ├── qc_faults.py            # Automated instrument fault detectors
│   ├── priors.py               # Source emission priors and OSM operating-status filter
│   ├── units.py                # Telemetry unit conversion and registry
│   └── background.py           # Regional baseline and network median calculation
├── agents/                     # Local agent review framework (Strands Agents SDK)
│   ├── critic.py               # Adversarial Critic identifying contradictory evidence
│   ├── investigator.py         # Infrastructure context and operating status investigator
│   └── validator.py            # Strict zero-hallucination factual validation barrier
├── infra/                      # AWS Infrastructure as Code (SAM)
│   ├── template.yaml           # SAM template defining API, Lambdas, Step Functions, DynamoDB
│   ├── lambdas/                # Serverless execution handlers
│   │   ├── api_handler.py      # HTTP API request router and response sanitizer
│   │   ├── run_core.py         # Step Functions core execution task
│   │   └── shortlist_builder.py# Dynamic candidate triage builder
│   └── step_functions/         # State machine workflow definition
├── web/                        # Next.js 15 Web Application
│   ├── src/app/
│   │   ├── page.tsx            # Incident overview and landing interface
│   │   ├── officer/page.tsx    # Inspection officer decision desk
│   │   ├── field/[caseId]/     # 390px mobile-optimized field inspector routing interface
│   │   ├── evidence/page.tsx   # Statistical backtest and reproducibility audit view
│   │   └── architecture/page.tsx# Serverless cloud infrastructure documentation
│   ├── src/components/         # MapLibre GL map, Chart.js series, triage cards
│   └── src/lib/offlineData.ts  # Pre-bundled offline fallback datasets
├── data/                       # Canonical case datasets and station baselines
│   ├── cases_out/              # Canonical case JSON specifications
│   ├── stations_12m/           # 12-month station background baselines
│   └── raw_cache/              # Cached raw OpenAQ gzip archive records for testing
├── scripts/                    # Audit, verification, and deployment tooling
│   ├── raw_check.py            # Direct S3 OpenAQ gzip archive row extraction utility
│   ├── verify_fault_detectors.py# Test runner for synthetic logger fault injection
│   └── prepare_s3_and_seed.py  # DynamoDB and S3 data seeding automation
├── tests/                      # Automated test suite (73 passing tests)
│   ├── e2e/                    # Playwright end-to-end and mobile layout tests
│   ├── test_audit_phase59.py   # Exact raw OpenAQ archive row parity tests
│   ├── test_pipeline_unit.py   # Unit tests for core dispersion and refusal logic
│   └── test_recompute_parity.py# Live HTTP API vs canonical JSON parity tests
└── docs/                       # Technical documentation and audit reports
    ├── FREEZE.md               # System freeze specification and raw archive index
    └── pitch/script.md         # Narrative presentation script and timing reference
```

---

## 7. Execution and Verification Guide

### 7.1 Prerequisites
* Python 3.12 or 3.13
* Node.js 18.x or 20.x
* AWS SAM CLI (for cloud deployments)

### 7.2 Installation and Setup

```bash
# Clone repository
git clone https://github.com/Unknownx-x1/SmokePrint_EnvHacksAWS.git
cd SmokePrint_EnvHacksAWS

# Configure Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install core dependencies
pip install pytest pytest-playwright requests boto3 numpy pandas
playwright install chromium
```

### 7.3 Executing the Test Suite

```bash
# Execute complete unit, integration, and Playwright E2E test suite (73 tests)
pytest
```

### 7.4 Running the Web Application Locally

```bash
cd web
npm install
npm run dev
# Access local instance at http://localhost:3000
```

### 7.5 Verifying Raw OpenAQ Archive Records

```bash
# Run raw OpenAQ S3 gzip row audit for any vetted case
python scripts/raw_check.py --case case_anand_vihar_20251102
```

---

## 8. Data Sources and Attribution

1. Ambient Air Quality Telemetry: OpenAQ AWS Open Data Program (`s3://openaq-data-archive/`), sourcing continuous CAAQMS monitors from the Central Pollution Control Board (CPCB), Delhi Pollution Control Committee (DPCC), Haryana State Pollution Control Board (HSPCB), and Uttar Pradesh Pollution Control Board (UPPCB).
2. Atmospheric Reanalysis Fields: European Centre for Medium-Range Weather Forecasts (ECMWF) ERA5 Atmospheric Reanalysis via Copernicus Climate Change Service (C3S).
3. Geospatial Data and Infrastructure: OpenStreetMap Contributors, OpenFreeMap vector tile infrastructure.

---

## 9. License

This project is licensed under the terms of the MIT License. See [LICENSE](LICENSE) for details.
