# Lyon eqasim scenario — plan, handover, and data checklist

This is the single-source handover document for the Lyon scenario used in
Christoph Garritsen's dissertation (VW / TU Munich, 2026). Same document
covers: project plan, current state, cross-machine handover steps, data
download checklist, and post-download pipeline execution.

Upstream pipeline: https://github.com/eqasim-org/eqasim-france (v1.4.0+25,
main @ 5a00846). This fork (`Chrigarr9/eqasim-france`, branch `lyon`) adds
**only** a customised `config.yml` and this documentation — the pipeline
source code is pristine and will be kept unchanged.

---

## 1. Project context

**Dissertation topic.** DRT ridepooling as a PT alternative in rural areas,
studied via a rural-metropolitan commuter corridor. Output: Pareto front of
cost (subsidy) vs service quality.

**Why Lyon.** Earlier work targeted Kelheim / Bavaria using the
`eqasim-org/bavaria` fork. That path hit persistent calibration problems
(ENTD→MiD structural mismatch, boptx crash after 188 evaluations,
French-pipeline distance CDFs being force-replaced with MiD 2017 Bayern
data). Since the dissertation is about *methodology*, not about building a
scenario, we switched (2026-04-16) to a proven, well-documented pipeline
for a French metropolitan region. Lyon was chosen over Toulouse for
academic credibility, eqasim maturity, and stronger Paper 2 narrative
(rural → metropolis commuter connection). Départements: 01 Ain, 38 Isère,
42 Loire, 69 Rhône.

**Shortlisted Kelheim-equivalent communes** (from
`scenario-selection/france_analysis.ipynb`, MOBPRO 2022 analysis):
Ambérieu-en-Bugey (01004), Brignais (69027), Veauche (42323),
Saint-Bonnet-de-Mure (69287), Vaugneray (69255), Chasse-sur-Rhône (38087),
Pont-Évêque (38318), Colombier-Saugnieu (69299). Final selection after the
full Lyon population is generated.

**Pipeline reference.** Hörl & Balac (2021), *Synthetic population and
travel demand for Paris and Île-de-France based on open and publicly
available data*, Transportation Research Part C, 130, 103291.

## 2. Strategy — unchanged pipeline

We run eqasim-france **as published** — no modifications to gravity model,
commuter handling, distance sampling, or any synthesis code. The Bavaria
fork had ~35 such modifications; on this branch they are all absent. The
rationale: the value of this pipeline is that it is the scientifically
trusted, peer-reviewed reference implementation for France. Any bug fixes
we find ourselves during Lyon work should be pushed upstream as PRs, not
kept as local patches.

Only non-pipeline additions on the `lyon` branch:
- `config.yml` — Lyon settings (départements, 1 % sampling, ENTD, paths)
- `DOWNLOAD_LYON_DATA.md` — this file
- `download_lyon_data.py` — helper for auto-fetchable data
- `.gitignore` additions for Lyon data subdirectories

## 3. Current state (as of 2026-04-16)

| Item | Status |
|---|---|
| Fork `Chrigarr9/eqasim-france` created | ✓ |
| Submodule at `matsim_scenarios/eqasim-france` | ✓ |
| Branch `lyon` off pristine upstream main (5a00846, v1.4.0+25) | ✓ |
| `config.yml` — Lyon départements, synthesis.output, 1 % sampling | ✓ |
| `download_lyon_data.py` — auto-fetch script | ✓ |
| MOBPRO 2022 copied from `scenario-selection/data/` | ✓ (67 MB) |
| Other data | **pending — see §5** |
| Pipeline never run yet | — |

## 4. Cross-machine handover

The target machine (where the pipeline will actually run) needs to
(a) pull this repo including the submodule, and (b) download the remaining
~12–20 GB of data.

```bash
# 1. Get the Dissertation repo and submodule state
cd /path/to/projects
git clone git@github.com:Chrigarr9/Dissertation.git   # or git pull if already present
cd Dissertation
git submodule update --init --recursive

# 2. Enter the Lyon fork
cd matsim_scenarios/eqasim-france
git checkout lyon                # should already be on lyon; safe to re-run
git pull origin lyon

# 3. Install Python deps (upstream uses uv since PR #498)
uv sync   # or: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 4. Fetch auto-downloadable data (~550 MB)
python download_lyon_data.py
# Optional: also try the community Lyon TCL fallback (see §5.3)
# python download_lyon_data.py --include-tcl

# 5. Manually download the 13 remaining datasets — see §5.2 tables below

# 6. Verify and run
python verify_data.py            # upstream sanity check (if applicable)
python -m synpp config.yml       # runs synthesis.output stage
```

**Disk requirement: ~25 GB free** (data + pipeline cache + 1 % output).
Full 100 % run needs more — plan 60–80 GB.

**Memory requirement: 16 GB minimum** for 1 % sampling; more for larger
sampling rates. `config.yml` is set to `java_memory: 10G` — bump if the
target machine has more and `matsim.output` is enabled later.

## 5. Data download

All data goes under `data/<subdir>/` relative to this repo. All these
subdirectories are **gitignored** — nothing you download gets committed.
**Estimated total: ~12–20 GB on disk.**

### 5.1 Auto-downloadable (run the script)

```bash
python download_lyon_data.py               # 10 files, ~550 MB, idempotent
python download_lyon_data.py --include-tcl # + community TCL fallback
```

| # | Source | URL | Target | Files | ~Size |
|---|---|---|---|---|---|
| 1 | BAN adresses (data.gouv.fr) | `https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{dept}.csv.gz` | `data/ban_lyon/` | `adresses-{01,38,42,69}.csv.gz` | ~50 MB |
| 2 | OSM Rhône-Alpes (Geofabrik) | `https://download.geofabrik.de/europe/france/rhone-alpes-220101.osm.pbf` | `data/osm_lyon/` | `rhone-alpes-220101.osm.pbf` | ~300 MB |
| 3 | SNCF TER/TGV/Intercités GTFS | `https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip` | `data/gtfs_lyon/` | `sncf-tgv-intercite-ter.gtfs.zip` | ~100 MB |
| 4 | Oùra (Ruban / Porte d'Isère) GTFS | `https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=OURA&dataFormat=GTFS&dataProfil=OPENDATA` | `data/gtfs_lyon/` | `oura.gtfs.zip` | ~50 MB |
| 5 | STAS (Loire 42) GTFS | `https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=CARS_REGION_LOIRE&dataFormat=GTFS&dataProfil=OPENDATA` | `data/gtfs_lyon/` | `stas.gtfs.zip` | ~30 MB |
| 6 | Rhône Express GTFS | `https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=CARS_REGION_EXPRESS&dataFormat=GTFS&dataProfil=OPENDATA` | `data/gtfs_lyon/` | `express.gtfs.zip` | ~30 MB |
| 7 | L'va (Vienne) GTFS | `https://s3.eu-west-1.amazonaws.com/files.orchestra.ratpdev.com/networks/vienne-mobi/exports/medias.zip` | `data/gtfs_lyon/` | `medias.zip` | ~10 MB |
| 8 | TAG (Grenoble) GTFS | `https://data.mobilites-m.fr/api/gtfs/BUL` | `data/gtfs_lyon/` | `BUL-GTFS.zip` | ~30 MB |

### 5.2 Manual — click-through web forms

#### National data (required for any French scenario)

| # | Source | Landing page | Target | Files | ~Size |
|---|---|---|---|---|---|
| 9 | INSEE — Census RP 2022 (individuals) | https://www.insee.fr/fr/statistiques/8647104 | `data/rp_2022/` | `RP2022_indcvi.parquet` (parquet, *Individus localisés au canton-ou-ville*) | ~3–5 GB |
| 10 | INSEE — Population totals 2022 | https://www.insee.fr/fr/statistiques/8647014 | `data/rp_2022/` | `base-ic-evol-struct-pop-2022_csv.zip` (*France hors Mayotte*, csv) | ~50 MB |
| 11 | INSEE — MOBPRO 2022 (work OD) | https://www.insee.fr/fr/statistiques/8589904 | `data/rp_2022/` | `RP2022_mobpro.parquet` — **already present (copied from scenario-selection/data/)** | 67 MB |
| 12 | INSEE — MOBSCO 2022 (education OD) | https://www.insee.fr/fr/statistiques/8589945 | `data/rp_2022/` | `RP2022_mobsco.parquet` | ~20 MB |
| 13 | INSEE — Filosofi 2021 (income) | https://www.insee.fr/fr/statistiques/7756855 | `data/filosofi_2021/` | `indic-struct-distrib-revenu-2021-COMMUNES_XLSX.zip` + `indic-struct-distrib-revenu-2021-SUPRA_XLSX.zip` | ~30 MB |
| 14 | INSEE — BPE 2024 (services/facilities) | https://www.insee.fr/fr/statistiques/8217525 | `data/bpe_2024/` | `BPE24.parquet` | ~100 MB |
| 15 | Ministry of Ecology — ENTD 2008 HTS | https://www.statistiques.developpement-durable.gouv.fr/enquete-nationale-transports-et-deplacements-entd-2008 | `data/entd_2008/` | `Q_tcm_menage_0.csv`, `Q_tcm_individu.csv`, `Q_menage.csv`, `Q_individu.csv`, `Q_ind_lieu_teg.csv`, `K_deploc.csv` | ~100 MB |
| 16 | IGN — IRIS 2024 | https://geoservices.ign.fr/contoursiris | `data/iris_2024/` | `CONTOURS-IRIS_3-0__GPKG_LAMB93_FXX_2024-01-01.7z` | ~500 MB |
| 17 | INSEE — Zoning codes 2024 | https://www.insee.fr/fr/information/7708995 | `data/codes_2024/` | `reference_IRIS_geo2024.zip` | ~5 MB |
| 18 | data.gouv.fr — SIRENE stock | https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/ | `data/sirene/` | `StockEtablissement_utf8.parquet` + `StockUniteLegale_utf8.parquet` | ~4 GB |
| 19 | data.gouv.fr — SIRENE geoloc | https://www.data.gouv.fr/fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/ | `data/sirene/` | `GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet` | ~500 MB |

#### Lyon-specific — BD TOPO

| # | Source | Landing page | Target | Files | ~Size |
|---|---|---|---|---|---|
| 20 | IGN — BD TOPO 2022 (4 départements) | https://geoservices.ign.fr/bdtopo → *Téléchargement anciennes éditions* → *BD TOPO® 2022 GeoPackage Départements* | `data/bdtopo_lyon/` | `BDTOPO_3-0_TOUSTHEMES_GPKG_LAMB93_D{001,038,042,069}_2022-03-15.7z` (4 files) | ~2 GB |

### 5.3 Lyon TCL (urban transit) — auth-gated

| # | Source | Landing page | Target | File | ~Size |
|---|---|---|---|---|---|
| 21 | TCL GTFS (official) | https://data.grandlyon.com/portail/fr/connexion → register → `tcl_sytral.tcltheorique` | `data/gtfs_lyon/` | `lyon_tcl.zip` | ~50 MB |

TCL is the main Lyon urban transit network (bus + tram). The simulation's
PT modal split depends on this feed. The official source requires a free
data.grandlyon.com account — **this is the recommended route for academic
work.**

A community Google-mediated fallback URL with an exposed API key exists
(`gtech-transit-prod.apigee.net/v1/google/gtfs/odbl/lyon_tcl.zip?apikey=…`)
and the script can attempt it via `--include-tcl`, but the ToS status of
that mirror is unclear — prefer the official source when citing in the
dissertation.

### 5.4 Optional data

- **EMP 2019** (National Person Mobility Survey) — newer alternative to
  ENTD 2008, 2019 rather than 2008. Landing:
  https://www.statistiques.developpement-durable.gouv.fr/resultats-detailles-de-lenquete-mobilite-des-personnes-de-2019
  → `data/emp_2019/`
- **EDGT Lyon 2015** (Regional household travel survey) — requires
  ADISP/CEREMA researcher access, gives region-specific calibration over
  the national ENTD.
  Landing: http://www.progedo-adisp.fr/serie_emd.php → `data/edgt_lyon_2015/`.
  Activate via `hts: edgt_lyon` + `edgt_lyon_source: adisp|cerema` in
  `config.yml`.

## 6. Running the pipeline

After all data in §5 is in place:

```bash
# Sanity-check data layout against upstream expectations
python verify_data.py
ls -lhR data/

# Synthesis: builds the 1 % synthetic population into output/
python -m synpp config.yml
```

Output files end up in `output/` with prefix `lyon_` (matching
`config.yml`). For the full simulation (not just population synthesis),
uncomment `- matsim.output` in `config.yml` — this requires all the GTFS
and OSM data from §5.1 plus Java 17+.

Scaling up: edit `config.yml` → `sampling_rate: 0.1` (10 %) once the 1 %
run completes cleanly. A 100 % Lyon run (~2 M agents) is the final target.

## 7. Dissertation connection

**Paper 1 — ridepooling in a rural commune cluster.** After synthesis
completes, extract commuter demand for the selected Kelheim-equivalent
commune(s) from the full Lyon population via
`matsim-libs/contribs/drt-demand-extraction/`. Feed into the
ExMAS/MIP optimiser at `ExmasCommuters/`. Produce Pareto front of
subsidy vs service quality.

**Paper 2 — rural → Lyon intermodal.** DRT as feeder to train/tram for
long-distance commuters in the same shortlisted commune(s). Builds on the
synthetic population's home-work flows.

**Calibration strategy.** Option A (calibrate full Lyon region, then cut
30 km radius around the target commune for DRT analysis) is recommended
over Option B (cut first, then calibrate). The Bavaria experience showed
that cutting first creates boundary effects — 26 % of workers had
destinations outside the study area and were dropped. Calibrating the
full region first avoids this. See
`scenario-selection/.planning/handoff-lyon-scenario.md` §5 for the full
discussion.

## 8. References

- **Main pipeline paper.** Hörl, S. and Balac, M. (2021). Synthetic
  population and travel demand for Paris and Île-de-France based on open
  and publicly available data. *Transportation Research Part C*, 130,
  103291. https://doi.org/10.1016/j.trc.2021.103291
- **Upstream repo.** https://github.com/eqasim-org/eqasim-france
- **This fork.** https://github.com/Chrigarr9/eqasim-france/tree/lyon
- **Upstream case documentation.**
  - `docs/cases/lyon.md` — Lyon-specific data instructions
  - `docs/population/population_data.md` — national French data sources
  - `docs/population/population_execution.md` — running the pipeline
  - `docs/simulation/simulation_execution.md` — running the MATSim simulation
- **Scenario-selection analysis.** Located in the Dissertation repo at
  `scenario-selection/france_analysis.ipynb` (MOBPRO 2022 commuter flow
  analysis, commune shortlist, interactive folium maps).
- **Prior handoff.** `scenario-selection/.planning/handoff-lyon-scenario.md`
  (2026-04-16) — records the Bavaria → Lyon decision in full.
