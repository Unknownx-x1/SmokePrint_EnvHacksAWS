# Smokeprint Timestamp Alignment & Temporal Conventions

**Document Version**: 1.0 (Phase 0.6)  
**Standard Air Quality Timezone**: IST (`Asia/Kolkata`, UTC+05:30)  
**Storage & Computing Timezone**: UTC (ISO-8601 with trailing `Z`)

---

## 1. OpenAQ v3 Temporal Convention

In the OpenAQ v3 API, hourly measurement periods are explicitly defined as interval bounds:
* `period.datetimeFrom`: The exact beginning timestamp of the 1-hour physical sampling window (e.g., `2026-04-28T04:30:00Z`).
* `period.datetimeTo`: The exact ending timestamp of the 1-hour physical sampling window (e.g., `2026-04-28T05:30:00Z`).
* `period.interval`: `01:00:00` (60 minutes).

### CAAQMS Sampling Practice in Delhi-NCR
Central Pollution Control Board (CPCB) and Delhi Pollution Control Committee (DPCC) Continuous Ambient Air Quality Monitoring Stations (CAAQMS) report hourly averaged beta-attenuation and optical counts aggregated on a half-hour or top-of-hour interval (typically `:30` to `:30` or `:00` to `:00`).

---

## 2. Open-Meteo ERA5 Wind Alignment

In Open-Meteo ERA5 reanalysis and forecast models:
* Hourly timestamps (e.g., `2026-04-28T05:00`) represent instantaneous model states for 10-meter wind vectors ($u, v$), surface pressure, and boundary layer height.
* The meteorological state at `05:00 UTC` coincides precisely with the **temporal midpoint** of the OpenAQ measurement interval `[04:30Z, 05:30Z]`.

### Explicit Alignment Rule
1. **Canonical Measurement Key**: Every air quality observation interval $[t_{\text{from}}, t_{\text{to}}]$ is mapped to its rounded hourly midpoint $T_{\text{mid}} = t_{\text{from}} + 30\text{ minutes}$ (e.g., interval `[04:30Z, 05:30Z]` $\implies$ `05:00:00Z`).
2. **Wind Interpolation**: ERA5 horizontal wind vectors ($u, v$) and boundary layer heights ($z_{\text{pbl}}$) are sampled at $T_{\text{mid}}$ to represent the mean advective transport acting on the plume during that exact 1-hour sampling cycle.
3. **Diurnal Hour-of-Day Logic**: For diurnal human emission curves (morning traffic 08:00–10:00 IST, evening peak 18:00–21:00 IST, nocturnal boundary layer collapse 22:00–06:00 IST), $T_{\text{mid}}$ is localized to `Asia/Kolkata`:
   $$\text{Hour}_{\text{IST}} = (T_{\text{mid, UTC}} + 5\text{h } 30\text{m}).\text{hour}$$
4. **Consistency Enforcement**: All back-trajectory advection integration steps ($dt = 60\text{s}$) evaluate wind velocity vectors linearly interpolated between $T_{\text{mid}}$ and $T_{\text{mid}} - 1\text{h}$.
