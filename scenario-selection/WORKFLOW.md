# Scenario Selection → Cutting Workflow (Lyon)

End-to-end record of how we pick a DRT study area around Lyon and cut the
full eqasim-france Lyon scenario to that area. Doubles as the dissertation
trail for the Paper 1 / Paper 2 scenario selection.

---

## 1. Goal

Pick a rural / peri-urban sub-area of the Lyon region with:

1. **High commuter volume** — enough demand for a meaningful DRT service.
2. **Poor PT accessibility** — justifies DRT as a PT alternative rather than a PT supplement.
3. **Outside the Lyon métropole belt** — the story is rural/peri-urban DRT, not
   urban ridehail.
4. **Spatially contiguous** — multiple candidate communes near each other so
   the scenario has a natural boundary.
5. **Anchored to Lyon** — supports Paper 2's stop-based connector study (DRT
   feeding a rail station with onward service into Lyon).

---

## 2. Pipeline

```
captivity_analysis.ipynb  ──►  §12 Pareto ranking  ──►  commune shortlist
                                                              │
                                                              ▼
                                             build_cutter_polygon.py
                                                              │
                                                              ▼
                                                    cutter.geojson (WGS84 circle)
                                                              │
                                 (on scenario machine)         │
                                                              ▼
                                         `matsim.simulation.cut` synpp stage
                                                              │
                                                              ▼
                                                    cut MATSim scenario
```

---

## 3. Step 1 — Commune ranking (this machine)

Run the captivity analysis notebook end-to-end:

```bash
cd scenario-selection
uv run --with jupyter jupyter notebook captivity_analysis.ipynb
# or open in VSCode / Cursor
```

Prereqs: `uv run download_lyon_data.py --scenario-selection` (OSM + GTFS, ~800 MB,
one-time). INSEE MOBPRO parquet + commune GeoJSON are auto-fetched by the notebook.

### Sections

| § | Content |
|---|---|
| 1-3 | Load INSEE MOBPRO, commune geometries, GTFS rail/frequency |
| 4 | r5py travel-time matrix (~358 endpoints; cached as `ttm.parquet`) |
| 5-5b | Commuter-weighted PT accessibility + connectivity index |
| 6 | Hard-threshold shortlist (captivity axis) |
| 7-8 | HEART slide-21/22 analogues |
| 9 | Ranked captivity shortlist |
| 10 | Expanded TTM for all communes ≤ 60 km (`ttm_expanded.parquet`) |
| 11 | Interactive folium map (`output/drt_suitability_map.html`) |
| **12** | **Pareto ranking — flow × PT accessibility** |

### §12 output

Non-dominated sort on two axes:
- **X: `total_flow`** (inbound + outbound commuters, §2)
- **Y: `pt_accessibility_expanded`** (commuter-weighted `min(1, car/pt)`, §10b)

Scope filter (default): `dist_to_lyon_km ∈ [20, 30]` and `total_flow ≥ 500` —
the half-hour drive band, metro belt excluded. Parameters are at the top of
cell 39 for easy tuning.

Products:
- `output/commune_pareto_ranking.csv` — full ranked table
- `output/pareto_scatter.png` — flow (log) × PT access with fronts colored
- `output/pareto_map.png` — commune polygons by front; dashed 20 / 30 km rings

### Selected cluster (2026-04-19)

Three front-1 communes east of Lyon, at the Ain-Rhône confluence:

| INSEE | Commune | Flow | PT access | Dist | Notes |
|---|---|---|---|---|---|
| 01224 | Loyettes | 1918 | 0.14 | 28 km | Mixed (io_ratio 2.8) |
| 01378 | Saint-Maurice-de-Gourdans | 1358 | 0.09 | 25 km | Strongly outbound |
| 01361 | Saint-Jean-de-Niost | 815 | 0.05 | 29 km | Almost pure bedroom |

Rationale: only contiguous front-1 cluster in the band; lowest PT scores on
the entire front; extends into a ~35k-commuter zone (fronts 2–3 — Balan,
Pont-de-Chéruy, Chavanoz, Charvieu-Chavagneux, Tignieu-Jameyzieu) that
anchors the Paper 1 service area. Connectivity ~0.002 (virtually zero PT
reachability in 60 min) is the captivity headline number.

---

## 4. Step 2 — Build the cutter polygon (either machine)

```bash
uv run scenario-selection/build_cutter_polygon.py \
    --communes 01224 01378 01361 \
    --radius-km 40 \
    --output data/cutter/lyon_drt_area.geojson
```

What it does:
1. Downloads `communes-100m.geojson` if missing (32 MB, gitignored).
2. Projects the three commune polygons to Lambert-93 (EPSG:2154).
3. Takes the centroid of the union.
4. Buffers by `radius_km` kilometres in Lambert-93.
5. Reprojects back to WGS84 and writes a single-feature GeoJSON FeatureCollection.

### Why 40 km

Centroid is at **45.815 °N, 5.196 °E**, ~27 km east of Lyon Part-Dieu. A 40 km
radius:
- Covers Lyon Part-Dieu with ~13 km margin on the west — safely includes all
  Lyon arrondissements and Villeurbanne workplaces.
- Reaches ~13 km east of the cluster — covers the Plaine de l'Ain industrial
  zone and Ambérieu-en-Bugey.
- Reaches south to ~ Vienne and north to the Dombes lakes.

35 km would have been tight: Lyon 9e (Vaise, west bank) sits ~33 km from
the centroid, leaving only ~2 km margin and risking boundary loss on the
west-bank workplaces.

---

## 5. Step 3 — Cut the scenario (the scenario machine)

### 5.1 Order: calibrate first, then cut

The `.planning/handoff-lyon-scenario.md` notes the Bavaria run saw 26.1 %
boundary loss when the scenario was cut *before* calibration (workers whose
workplace sat just outside the polygon got dropped). We avoid that by:

1. Running full-region calibration on a sub-sample (1 % — ~70k agents, fast).
2. Running the cutter **post-simulation** on the output plans.

This keeps the boundary commutes in the demand graph during calibration and
only drops them at the end when we extract the study area.

### 5.2 1 % full-region calibration

```yaml
# config_lyon.yml (or config_local_lyon.yml)
config:
  sampling_rate: 0.01            # 1 %
  # … usual Lyon config …
run:
  - matsim.simulation.full_run   # full-region calibration first
```

Run synpp. Produces `output/simulation_output/output_plans.xml.gz` — the
calibrated population used as the cutter's input.

### 5.3 Enable the cut stage

Append (or uncomment) the cutter stage in the same config:

```yaml
run:
  - matsim.simulation.full_run
  - matsim.simulation.cut        # cuts post-calibration output
config:
  cutter:
    path: cutter
    file: lyon_drt_area.geojson   # produced in step 4
    name: lyon_drt_area
    after_full_simulation: True   # IMPORTANT: cut the output plans, not the input
```

Place the GeoJSON at `<data_path>/cutter/lyon_drt_area.geojson`.

Output: `<output_path>/lyon_drt_area/`:
- `lyon_drt_area_config.xml` — adapted MATSim config
- `lyon_drt_area_plans.xml.gz` — subset population (home in polygon)
- `lyon_drt_area_network.xml.gz` — subset network
- `lyon_drt_area_facilities.xml.gz` — subset facilities

Under the hood: the synpp stage hands the GeoJSON to
`org.eqasim.core.scenario.cutter.RunScenarioCutter` (Java) via `eqasim.run()`.
Python wrapper: `matsim/simulation/cutter/cut.py`. Loader:
`data/cutter/geometry.py`.

---

## 6. Step 4 — Downstream (DRT demand extraction)

Feed the cut scenario into `matsim-libs/contribs/drt-demand-extraction/` to
generate the DRT demand database (`drt_requests.csv` + `exmas_rides.csv`)
which Paper 1's MIP consumes.

See `papers/paper1/planning/drt-demand-extraction-skeleton.md` for the
demand-extraction methodology.

---

## 7. File map

```
scenario-selection/
├── captivity_analysis.ipynb          # PT accessibility + Pareto ranking (§12)
├── france_analysis.ipynb             # national-scale DRT opportunity scan
├── analyze_regions.py                # script form of national analysis
├── build_cutter_polygon.py           # commune codes + radius → GeoJSON circle
├── drt_map.py                        # folium interactive-map builder
├── WORKFLOW.md                       # ← you are here
├── data/                             # gitignored; auto-downloaded
│   ├── communes-100m.geojson
│   ├── RP2022_mobpro.parquet
│   └── gtfs_clean/
├── cache/                            # gitignored; r5py TTMs
│   ├── ttm.parquet
│   └── ttm_expanded.parquet
├── output/                           # gitignored
│   ├── commune_pareto_ranking.csv
│   ├── pareto_scatter.png
│   ├── pareto_map.png
│   ├── drt_suitability_map.html
│   └── cutter.geojson                # local test output
├── tests/
└── .planning/
    └── handoff-lyon-scenario.md      # cross-machine context
```

---

## 8. Cross-machine transfer

Everything needed to reproduce on the scenario machine lives in git:

- `scenario-selection/build_cutter_polygon.py` (tracked)
- `scenario-selection/WORKFLOW.md` (tracked)
- `scenario-selection/captivity_analysis.ipynb` (tracked, but the scenario
  machine doesn't need to run it — the cluster codes `01224 01378 01361`
  are the only output that crosses machines)

Large inputs (commune GeoJSON, MOBPRO parquet, TTMs) are gitignored; the
script auto-fetches commune GeoJSON when invoked.

### Minimal scenario-machine command

```bash
# 1. generate polygon
uv run scenario-selection/build_cutter_polygon.py \
    --communes 01224 01378 01361 --radius-km 40 \
    --output data/cutter/lyon_drt_area.geojson

# 2. edit config_lyon.yml: add `matsim.simulation.cut` to run: list and
#    cutter block with file: lyon_drt_area.geojson, after_full_simulation: True

# 3. run
uv run python -m synpp
```
