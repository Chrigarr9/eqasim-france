# Lyon Calibration Targets

This directory holds the calibration target pickles and CSVs consumed by
`calibrate_lyon_1pct.py`. Artifacts are produced by `build_lyon_target.py`.

## Files

| File | Producer | Consumer | Purpose |
|---|---|---|---|
| `lyon_entd_shares.pkl` | `build_lyon_target.py` | `ModeShareObjective(shares_path=...)` | Target per-mode per-bin shares (Lyon ENTD-filtered). Drives the objective. |
| `lyon_entd_shares.csv` | `build_lyon_target.py` | (inspection) | Human-readable copy of the pickle. |
| `reference_trips.csv` | `build_lyon_target.py` | `ModeShareObjective` | Trip-level seed — used only for initial bounds (per-bin shares are overridden by the pickle). |

## Target data source

ENTD 2008 (Enquête Nationale Transport et Déplacements), filtered by the
eqasim-france synpp pipeline to trips relevant for the Lyon départements
(01 Ain, 38 Isère, 42 Loire, 69 Rhône).

The pipeline cache at
`C:/matsim_cache_lyon/data.hts.entd.filtered__*.p` is loaded directly;
no network access needed after the pipeline has been run once.

## Distance bands

Seven bands, aligned with the Bavaria/Kelheim scheme and ENTD granularity:

| idx | range |
|---|---|
| 0 | 0 – 0.5 km |
| 1 | 0.5 – 1 km |
| 2 | 1 – 2 km |
| 3 | 2 – 5 km |
| 4 | 5 – 10 km |
| 5 | 10 – 20 km |
| 6 | 20 – 50 km |

>50 km bands are excluded: sparse in ENTD Lyon subset and out of scope for
the typical daily mobility the scenario must reproduce.

## Alternatives

`config_100pct.yml` currently uses `hts: entd`. For region-specific
calibration, EDGT Lyon 2015 (if downloaded via CEREMA/ADISP) gives a richer
regional survey. Swap `ENTD_CACHE` in `build_lyon_target.py` to the EDGT
filtered cache and rebuild.
