# Lyon eqasim-france ASC Calibration

Adapted from `matsim_scenarios/bavaria/calibration/boptx/` v4.

## Status: NOT USED — IDF defaults retained (2026-04-19)

After an initial DE run (36 evals, L1 = 0.0363 vs baseline IDF-defaults L1 = 0.0450), we decided to **keep the Hörl & Balac 2021 published IDF calibrated ASCs** (hardcoded in `IDFModeParameters.buildDefault()`) rather than re-tune for Lyon.

Rationale:
- **Baseline fit is already good**: aggregate mode-share error with IDF defaults is within ±2 pp of the Lyon ENTD target for every mode. Per-cell L1 of 0.045 is adequate for a dissertation about DRT methodology, not about mode-share accuracy.
- **DE improvement was marginal and overfit**: calibrated ASCs pushed per-cell L1 from 0.045 → 0.036 (19% gain) but aggregate car share got *worse* (+1.9pp vs baseline's -0.3pp) — DE traded aggregate accuracy for per-cell shape.
- **Structural issues block further gains**:
  - Bicycle stuck at 0% due to `bike.betaAgeOver18_u_a = -0.0496` dominating any ASC
  - PT middle-distance under-prediction (sim 3-4% vs target 12-13% at 2-10 km) is the PT-reference pinning + network equilibrium issue — not ASC-tunable with single-iter DE
- **Scientific grounding**: "We use the Hörl & Balac 2021 calibrated IDF mode choice parameters" is a clean one-line citation. DE-retuned ASCs would require defending the calibration against a thin ENTD Lyon subset (2,162 trips).
- **DRT analysis is rural**: The Pareto analysis focuses on rural/periurban communes (dept 01, 42, periurban 38/69) where PT share is near-zero anyway. The urban PT gap doesn't affect rural DRT calibration.

Infrastructure (scripts, target builder, run script) is retained for future re-calibration if needed (e.g., if DRT integration reveals systematic bias requiring ASC adjustment, or if EDGT Lyon 2015 data becomes accessible).

**To run simulations with IDF defaults**: `run_eqasim_lyon_1pct.sh` falls back to defaults when `calibrated_asc.yml` is absent. No CLI overrides needed.

## Files

| File | Purpose |
|---|---|
| `calibrate_lyon_1pct.py` | Main calibration driver. Runs boptx Differential Evolution over ASCs + walk/bike betaTT. |
| `build_lyon_target.py` | Builds `data/lyon_entd_shares.pkl` + `data/reference_trips.csv` from the cached filtered ENTD. |
| `export_calibrated_asc.py` | Extracts best-so-far ASCs from the boptx pickle into `calibrated_asc.yml`. |
| `run_eqasim_lyon_1pct.sh` | Runs a full MATSim loop with the calibrated ASCs applied (post-calibration). |
| `data/README.md` | Target data documentation. |

## Prerequisites

- Lyon 1% MATSim scenario at `../../output_1pct/lyon_1pct_*.xml.gz` (+ `run.jar`). Produced by the eqasim-france synpp pipeline with `sampling_rate: 0.01` and `run_matsim: false`.
- eqasim-france Python venv at `../../.venv/` (for building targets, exporting ASCs).
- JDK 21 at `C:/Users/VWAUCCY/dev/msf/.jdk/jdk-21.0.2+13/`.
- `boptx-upstream/` reused from the Bavaria sibling at `matsim_scenarios/bavaria/calibration/boptx/boptx-upstream/` (auto-added to `sys.path`).

## Workflow

```bash
cd matsim_scenarios/eqasim-france/calibration/boptx

# 1. Build the mode-share target (once, or when ENTD cache changes)
../../.venv/Scripts/python build_lyon_target.py

# 2. Generate the ASC-only config variant (DMC=1.0, KeepLastSelected=0.0)
#    Idempotent; re-run if output_1pct/lyon_1pct_config.xml is regenerated.
../../.venv/Scripts/python make_asc_only_config.py

# 3. Run calibration (blocks; write a log redirect if running overnight)
../../.venv/Scripts/python calibrate_lyon_1pct.py 4 4 2>&1 | tee calibration_lyon_1pct.log
# args: [parallelism] [threads/eval]  — 4x4 ≈ 16 cores of work

# 4. Export best-so-far ASCs to YAML (can be re-run while calibration is alive)
../../.venv/Scripts/python export_calibrated_asc.py

# 5. Run a full simulation with the calibrated ASCs
bash run_eqasim_lyon_1pct.sh 100
```

### Why the ASC-only config variant

The generated Lyon config has DMC strategy weight 0.05 (5%) and KeepLastSelected 0.95 — calibrated for warm-start multi-iteration simulations. With `iterations=1` (our calibration setting), only 5% of agents would pick a fresh mode each evaluation; the other 95% keep their initialization-random modes and contribute pure noise to the objective. `make_asc_only_config.py` flips these to 1.0 / 0.0 so every agent's mode choice contributes to the calibration signal exactly once per evaluation.

## Design notes

### Why ASC-only (not full parameter estimation)?

Bavaria's session logs showed that full parameter estimation on a 1% sample is dominated by Monte Carlo noise: `betaTravelTime` and `betaCost` values are econometrically identified from the HTS and should not be re-tuned in-simulation. Only the ASCs — which absorb modal constants not captured by the utility specification — need simulation-based tuning.

The walk/bike `betaTravelTime_u_min` parameters are kept as secondary free params because they shape the distance-vs-share curve. Freezing them at the IDF defaults over-predicts walk at 0.5-2 km and bike at 5-50 km (observed in Bavaria v3).

### What's tuned (v1 — minimal)

- `car.alpha_u`      — free (init +1.35, bounds [-0.50, +4.00])
- `bike.alpha_u`     — free (init -2.00, bounds [-4.00,  0.00])
- `walk.alpha_u`     — free (init +1.43, bounds [-1.00, +4.00])

Initial values are the IDF defaults directly — PT is the reference at 0, so no shift is applied.

Total: **3 free parameters**. DE with 8 candidates.

### Why PT as the reference mode

When DRT is later added to the scenario, its parameters will be **seeded from PT** (conservative: PT's waiting-time and access/egress penalties realistically apply to DRT; seeding from car would grant DRT car's strong +1.35 ASC for free, biasing the dissertation's Pareto front). Pinning PT at 0 puts DRT's initial utility at 0 too — DRT sits naturally in PT's utility neighborhood and any calibrated DRT ASC later reads as a clean delta from PT.

### What's frozen

- `pt.alpha_u` — pinned at 0 via CLI (reference alternative).
- `motorcycle.alpha_u` — pinned at +1.35 via CLI (IDF default). Base Lyon motorcycle share is <1 %; not worth tuning.
- `walk.betaTravelTime_u_min` (-0.15) and `bike.betaTravelTime_u_min` (-0.05) — held at IDF defaults. Free them only if the ASC-only fit leaves systematic per-distance-band residuals (observed walk-over at 0.5-2 km or bike-over at 5-50 km in Bavaria v3).
- `idfCar.betaInsideUrbanArea` (-0.5), `idfCar.betaCrossingUrbanArea` (-1.0), `idfBike.betaInsideUrbanArea` (+1.5) — IDF-specific urban-area betas kept at IDF paper values. Would need a per-zone decomposition to identify.

### Structurally non-tunable

- `car_passenger` uses `ZeroUtilityEstimator` in the generated config (`lyon_1pct_config.xml` line 252-254) — its utility is literally 0, with no `carPassenger.alpha_u` field in `IDFModeParameters`. The CLI flag would be silently ignored. Its share emerges from per-person `isPassenger` availability + zero utility vs the calibrated modes. **Tuning ride ASC requires a Java patch** replacing the estimator with one that reads an `alpha_u` field.

### Values used in `run_eqasim_lyon_1pct.sh`

The simulation reads parameters from `IDFModeParameters.buildDefault()` (config has `modeParametersPath = null`). Any CLI `--mode-choice-parameter:...` flag overrides the default in memory. After calibration, `export_calibrated_asc.py` writes the best ASCs to `calibrated_asc.yml`, and the shell script applies them as overrides on top of the IDF defaults.

### Why 1% for calibration

At 18k persons the 1% sample is small enough for ~5 min/eval single-threaded on this machine. A full calibration run of ~400 evaluations takes ~33 h wall-clock single-threaded, or ~8 h with 4x parallelism.

After convergence, the same ASCs are applied to larger samples (10%, 25%, 100%) via `run_eqasim_lyon_1pct.sh` (change `--sample` path in the shell script).
