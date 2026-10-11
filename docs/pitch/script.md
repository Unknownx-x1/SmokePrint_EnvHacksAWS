# Smokeprint: 3-Minute Product Pitch & Walkthrough

**Target Duration**: 2:40 – 2:55 (Target speaking rate: ~145–150 wpm)  
**Total Spoken Words**: 406 words (Target constraint: 380–430 words)  
**Live Site URL**: `http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com`

---

## Word-for-Word Narration Script

**[0:00 - 0:20] The Problem**  
Air quality monitors show when pollution spikes, but never whether to send an inspector into the field, or where to go first. When a monitor turns red, field teams often scramble blindly without knowing if the reading is a genuine local plume, regional smog, or a broken sensor. Smokeprint solves this critical operational decision problem.

**[0:20 - 0:55] Gurugram Sensor Fault Refusal**  
Look at the Gurugram case from June 2026. The monitor shows heavy pollution, but Smokeprint immediately displays "NO DISPATCH RECOMMENDED". Why? Because the PM2.5 to PM10 ratio is locked at exactly 0.600 across the whole morning window, followed by an abrupt reading dropout. That is a logger fault, so the tool says no dispatch. Smokeprint stands down the field team, preventing officers from wasting time chasing a hardware glitch.

**[0:55 - 1:15] Regional Smog Refusal**  
Now look at the Delhi smog episode from October 2025. Here again, Smokeprint issues "NO DISPATCH RECOMMENDED". Many stations rose together across the airshed, so it is not one local source. Sending municipal officers to inspect a local factory gate cannot resolve an airshed-wide event.

**[1:15 - 1:50] Anand Vihar Spike & Candidate Triage**  
In contrast, examine a genuine local spike at Anand Vihar in November 2025. PM2.5 climbs overnight from about 180 to 400 ug/m3. The peak hour has PM10 about 536 and a PM2.5 to PM10 ratio near 0.75. Here, Smokeprint recommends dispatch. Crucially, the shortlist is a set of comparable candidates—a triage list, not an attribution. Upwind sites like Patparganj Industrial Area and Rajghat Bus Depot are prioritized for physical field inspection.

**[1:50 - 2:15] Disused Facility Filter**  
Look at candidate three: Rajghat Thermal Power Station. The Rajghat Thermal Power Station is aligned with the wind but tagged disused in OpenStreetMap, so the tool says inspection is unlikely to be useful. That prevents field officers from wasting precious inspection hours at decommissioned power facilities.

**[2:15 - 2:35] Evidence & Backtest Validation**  
On our Evidence page, backtest evaluations across 500 simulated plume injections show that the shortlist achieves 54.4% precision at rank one, beating the nearest-upwind baseline of 34.4%. Because this evaluation uses simulated plume injections, this shows consistency, not real-world accuracy.

**[2:35 - 2:55] Cloud Architecture & Replay**  
Smokeprint is built on AWS using S3, DynamoDB, Lambda, HTTP API, Step Functions, and CloudWatch, and is completely free-tier friendly. Clicking "Replay on AWS" runs a Step Functions replay of a stored, validated result, clearly marked as replayed. Contextual review uses the Strands Agents SDK with a small local model, and outputs are validated before they are served.

---

## Live UI Screen Walkthrough Guide

| Timing | Page URL | On-Screen Action & Visual Elements |
|---|---|---|
| **0:00 - 0:20** | `/` (Landing) | Show landing page headline: *"A spike at a monitor is not a single source attribution. Smokeprint tells you whether to send an inspector, and where first."* Highlight the problem statement. |
| **0:20 - 0:55** | `/officer/` → `/field/case_gurugram_20260630/` | Select Gurugram (Jun 30) card marked `REFUSED: instrument fault`. Open field view showing red banner: `NO DISPATCH RECOMMENDED`. Highlight ratio lock at `0.600` and dropout description. |
| **0:55 - 1:15** | `/officer/` → `/field/case_regional_smog_20251020/` | Select Delhi Smog (Oct 20) card marked `REFUSED: regional`. Show refusal note: stations simultaneously elevated across airshed; no dispatch for regional events. |
| **1:15 - 1:50** | `/officer/` → `/field/case_anand_vihar_20251102/` | Select Anand Vihar (Nov 02). Point to `STATION PM2.5: 400 µg/m³`, `PM2.5/PM10: 0.746`. Display candidate shortlist banner: *"Candidates are comparable; this is a triage list, not an attribution."* Show #1 Patparganj Industrial Area and #2 Rajghat Bus Depot. |
| **1:50 - 2:15** | `/field/case_anand_vihar_20251102/` | Scroll to candidate #3: Rajghat Thermal Power Station (`LOW` tier). Point to the exact status sentence: *"Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful."* |
| **2:15 - 2:35** | `/evidence/` | Navigate to Evidence tab. Show 500-Trial Dispersion Mismatch table: Shortlist P@1 `54.4%` vs Nearest-Upwind `34.4%`. Read caveat: *"simulated plume injections; consistency not real-world accuracy"*. |
| **2:35 - 2:55** | `/architecture/` & `/officer/` | Show serverless AWS diagram (S3, DynamoDB, Lambda, Step Functions, CloudWatch). Click `Replay on AWS` button; demonstrate `replayed` provenance and agent validation banner. |
