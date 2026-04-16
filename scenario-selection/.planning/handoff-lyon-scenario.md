# Handoff: Lyon eqasim Scenario Generation

**Date:** 2026-04-16
**Previous session:** Scenario selection analysis (france_analysis.ipynb)
**Next steps:** Clone eqasim-france, download data, generate Lyon scenario

---

## Context & Decision

We are switching from the Bavaria/Kelheim MATSim scenario to a **French scenario using the eqasim-france pipeline**. The Bavaria scenario had extensive calibration problems (ENTD→MiD data mismatch, boptx crash, walk mode over-representation — see `bavaria/.planning/` for full history). Since the dissertation is about **methodology** (DRT ridepooling Pareto front of cost vs quality), not about building a scenario, we want a proven, well-documented pipeline.

**Decision: Lyon region** was chosen over Toulouse based on:
- Stronger academic credibility (France's 2nd metro area)
- Best-documented eqasim-france configuration
- Better Paper 2 narrative (rural → metropolis commuter connection)
- Toulouse had worse PT (6.9% vs 14.8%) which is good for DRT argument, but Lyon's outer ring still has 85-95% car dependency
- eqasim-france uses native French data (ENTD survey) — no cross-country translation issues like Bavaria had

## Analysis Done (scenario-selection/)

The notebook `france_analysis.ipynb` contains the full analysis:
- **INSEE MOBPRO 2022** commuter microdata (7.4M records, transport mode per worker)
- National maps of car dependency and PT accessibility
- Département ranking by DRT opportunity
- Per-commune total commute flow analysis (in + out, all directions)
- Interactive folium maps with flow arrows
- **"Kelheim filter"** identifying rural communes with high car-dependent commuting

### Shortlisted communes (from interactive exploration):
| Commune | Code | Total flow | Car % | Avg dist | Notes |
|---|---|---|---|---|---|
| Ambérieu-en-Bugey | 01004 | 9,366 | 94% | 20km | Ain, rail to Lyon, strong Kelheim analogy |
| Brignais | 69027 | ~12,000 | ~87% | ~14km | SW Lyon suburb, high inbound (employer) |
| Veauche | 42323 | 6,032 | 95% | 16km | Loire/St-Étienne area, very car-dependent |
| Saint-Bonnet-de-Mure | 69287 | ~5,500 | ~92% | ~14km | East Lyon near airport |
| Vaugneray | 69255 | ~5,000 | ~90% | ~15km | West Lyon hills |
| Chasse-sur-Rhône | 38087 | ~5,000 | ~89% | ~15km | South, Vienne corridor |
| Pont-Évêque | 38318 | ~3,500 | ~92% | ~18km | South, near Vienne |
| Colombier-Saugnieu | 69299 | ~2,500 | ~95% | ~15km | East, near airport, very car-dependent |

These are candidates for the ~30km radius study area. Final selection should be based on:
1. Which has the clearest "rural area needing DRT" narrative
2. Which is within the eqasim-france Lyon configuration départements (01, 38, 42, 69)
3. Which has enough commuter volume for interesting DRT demand

## Next Steps: eqasim-france Pipeline

### 1. Clone the repository
```bash
cd /mnt/Shared/Code/projects/Dissertation
git clone https://github.com/eqasim-org/eqasim-france.git
# Or: git clone https://github.com/eqasim-org/ile-de-france.git (older name, same thing)
```
The latest release is **v1.4.0 (February 2026)**.

### 2. Lyon configuration
Documentation: `docs/cases/lyon.md` in the repo.

Default Lyon départements: **01 (Ain), 38 (Isère), 42 (Loire), 69 (Rhône)**
Extended: add 07 (Ardèche), 26 (Drôme), 73 (Savoie), 74 (Haute-Savoie)

Config changes needed in `config.yml`:
```yaml
config:
  regions: []
  departments: ["01", "38", "42", "69"]  # Lyon core, extend as needed
  sampling_rate: 1.0  # 100% sample
  # ... other Lyon-specific settings per docs/cases/lyon.md
```

### 3. Data to download

All data is open. Some can be automated, some needs manual download:

**Automated (scripts in pipeline):**
- OpenStreetMap: Geofabrik Rhône-Alpes extract
- BAN addresses: adresse.data.gouv.fr (per department CSV.gz)
- INSEE census data

**May need manual download:**
- **BD TOPO 2022** buildings: IGN GeoServices, per department (7z files for 01, 38, 42, 69)
- **ENTD 2008** or **EMP 2019** household travel survey: via ADISP/Progedo (requires researcher access) — check if the pipeline has a workaround
- **EDGT Lyon 2015**: local household travel survey (via CEREMA) — optional but improves calibration
- **GTFS feeds**: 
  - TCL (Lyon urban): transport.data.gouv.fr
  - Cars Région (interurban buses)
  - SNCF TER/TGV
  - TAG (Grenoble), STAS (Saint-Étienne) if using extended departments

### 4. Check Bavaria work for cross-platform lessons
The Bavaria eqasim work (`bavaria/` directory) has fixes for:
- Running on Linux and Windows
- KBA driving license data bugs
- Gravity model parameters
- boptx calibration setup
- Distance correction factors

Check `bavaria/.planning/` for session logs with all the fixes. Many issues were Bavaria-specific (ENTD→MiD translation) but some pipeline fixes may apply.

### 5. Calibration strategy — open question

**Option A: Calibrate full region, then cut 30km radius**
- Pro: calibration sees the full travel demand, more realistic
- Con: expensive (100% Lyon = ~2M agents), cut area may have edge effects

**Option B: Cut 30km radius first, then calibrate**
- Pro: faster iteration, focused calibration
- Con: boundary effects, missing through-traffic

**Recommendation to discuss:** Option A is methodologically cleaner. The Bavaria experience showed that study area boundaries create artifacts (26.1% of workers dropped because destinations fell outside). Calibrating the full region first, then extracting the study area for DRT analysis, avoids this. The DRT demand extraction tool (`matsim-libs/contribs/drt-demand-extraction/`) can then extract the relevant demand from the calibrated full scenario.

### 6. Connection to dissertation papers

**Paper 1:** Ridepooling optimization within a rural commune cluster (the "Kelheim equivalent")
- Uses ExMAS/MIP optimizer from ExmasCommuters/
- Input: extracted commuter demand from MATSim scenario
- Focus: Pareto front of subsidy vs service quality

**Paper 2:** Rural → Lyon intermodal commuter service
- DRT as feeder to train/tram for long-distance commuters
- Multi-stop or intermodal service design
- Uses the connection between the selected rural area and Lyon

## Files & Locations

| Path | Contents |
|---|---|
| `scenario-selection/france_analysis.ipynb` | Full analysis notebook (executed, all outputs) |
| `scenario-selection/explore_regions.ipynb` | Earlier version (has VS Code caching issues) |
| `scenario-selection/analyze_regions.py` | CLI script version of the analysis |
| `scenario-selection/data/` | Downloaded MOBPRO parquet + GeoJSON (gitignored, ~101MB) |
| `scenario-selection/output/` | Static PNG maps (gitignored) |
| `bavaria/.planning/` | Bavaria calibration session logs (useful reference) |
| `ExmasCommuters/` | Python ridepooling optimizer |
| `matsim-libs/contribs/drt-demand-extraction/` | Java MATSim DRT demand extraction |
