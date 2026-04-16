# Lyon scenario data — download checklist

This fork runs the eqasim-france pipeline **unchanged** for Lyon
(départements 01 Ain, 38 Isère, 42 Loire, 69 Rhône). Data goes into
`data/<subdir>/` relative to this repo root. All data directories are
gitignored — nothing you download here gets committed.

**Estimated total: ~12–20 GB on disk.**

---

## Auto-downloadable — run the script

```bash
cd matsim_scenarios/eqasim-france
python download_lyon_data.py               # BAN, OSM, 6/7 GTFS feeds
python download_lyon_data.py --include-tcl # also attempt community TCL fallback
```

The script is idempotent (skips already-present files).

| # | Source | URL pattern | Target dir | Files | ~Size |
|---|---|---|---|---|---|
| 1 | BAN adresses (data.gouv.fr) | `https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{dept}.csv.gz` | `data/ban_lyon/` | `adresses-{01,38,42,69}.csv.gz` | ~50 MB |
| 2 | OSM Rhône-Alpes (Geofabrik) | `https://download.geofabrik.de/europe/france/rhone-alpes-220101.osm.pbf` | `data/osm_lyon/` | `rhone-alpes-220101.osm.pbf` | ~300 MB |
| 3 | SNCF TER/TGV GTFS | `https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip` | `data/gtfs_lyon/` | `sncf-tgv-intercite-ter.gtfs.zip` | ~100 MB |
| 4 | Oùra (Ruban / Porte d'Isère) GTFS | `https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=OURA&dataFormat=GTFS&dataProfil=OPENDATA` | `data/gtfs_lyon/` | `oura.gtfs.zip` | ~50 MB |
| 5 | STAS (Loire 42) GTFS | `https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=CARS_REGION_LOIRE&dataFormat=GTFS&dataProfil=OPENDATA` | `data/gtfs_lyon/` | `stas.gtfs.zip` | ~30 MB |
| 6 | Rhône Express GTFS | `https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=CARS_REGION_EXPRESS&dataFormat=GTFS&dataProfil=OPENDATA` | `data/gtfs_lyon/` | `express.gtfs.zip` | ~30 MB |
| 7 | L'va (Vienne) GTFS | `https://s3.eu-west-1.amazonaws.com/files.orchestra.ratpdev.com/networks/vienne-mobi/exports/medias.zip` | `data/gtfs_lyon/` | `medias.zip` | ~10 MB |
| 8 | TAG (Grenoble) GTFS | `https://data.mobilites-m.fr/api/gtfs/BUL` | `data/gtfs_lyon/` | `BUL-GTFS.zip` | ~30 MB |

---

## Manual — click-through web forms

### National data (required for any French scenario)

| # | Source | Landing page | Target dir | Files | ~Size |
|---|---|---|---|---|---|
| 9 | INSEE — Census RP 2022 (individuals) | https://www.insee.fr/fr/statistiques/8647104 | `data/rp_2022/` | `RP2022_indcvi.parquet` (parquet, *Individus localisés au canton-ou-ville*) | ~3–5 GB |
| 10 | INSEE — Population totals 2022 | https://www.insee.fr/fr/statistiques/8647014 | `data/rp_2022/` | `base-ic-evol-struct-pop-2022_csv.zip` (*France hors Mayotte*, csv) | ~50 MB |
| 11 | INSEE — MOBPRO 2022 (work OD) | https://www.insee.fr/fr/statistiques/8589904 | `data/rp_2022/` | `RP2022_mobpro.parquet` — **already copied from scenario-selection/data/** | 67 MB |
| 12 | INSEE — MOBSCO 2022 (education OD) | https://www.insee.fr/fr/statistiques/8589945 | `data/rp_2022/` | `RP2022_mobsco.parquet` | ~20 MB |
| 13 | INSEE — Filosofi 2021 (income) | https://www.insee.fr/fr/statistiques/7756855 | `data/filosofi_2021/` | `indic-struct-distrib-revenu-2021-COMMUNES_XLSX.zip` + `indic-struct-distrib-revenu-2021-SUPRA_XLSX.zip` | ~30 MB |
| 14 | INSEE — BPE 2024 (services) | https://www.insee.fr/fr/statistiques/8217525 | `data/bpe_2024/` | `BPE24.parquet` | ~100 MB |
| 15 | Ministry of Ecology — ENTD 2008 HTS | https://www.statistiques.developpement-durable.gouv.fr/enquete-nationale-transports-et-deplacements-entd-2008 | `data/entd_2008/` | `Q_tcm_menage_0.csv`, `Q_tcm_individu.csv`, `Q_menage.csv`, `Q_individu.csv`, `Q_ind_lieu_teg.csv`, `K_deploc.csv` | ~100 MB |
| 16 | IGN — IRIS 2024 | https://geoservices.ign.fr/contoursiris | `data/iris_2024/` | `CONTOURS-IRIS_3-0__GPKG_LAMB93_FXX_2024-01-01.7z` | ~500 MB |
| 17 | INSEE — Zoning codes 2024 | https://www.insee.fr/fr/information/7708995 | `data/codes_2024/` | `reference_IRIS_geo2024.zip` | ~5 MB |
| 18 | data.gouv.fr — SIRENE stock | https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/ | `data/sirene/` | `StockEtablissement_utf8.parquet` + `StockUniteLegale_utf8.parquet` | ~4 GB |
| 19 | data.gouv.fr — SIRENE geoloc | https://www.data.gouv.fr/fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/ | `data/sirene/` | `GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet` | ~500 MB |

### Lyon-specific — BD TOPO

| # | Source | Landing page | Target dir | Files | ~Size |
|---|---|---|---|---|---|
| 20 | IGN — BD TOPO 2022 (4 départements) | https://geoservices.ign.fr/bdtopo → *Téléchargement anciennes éditions* → *BD TOPO® 2022 GeoPackage Départements* | `data/bdtopo_lyon/` | `BDTOPO_3-0_TOUSTHEMES_GPKG_LAMB93_D{001,038,042,069}_2022-03-15.7z` (4 files) | ~2 GB |

### Lyon-specific — GTFS (auth-gated)

| # | Source | Landing page | Target dir | File | ~Size |
|---|---|---|---|---|---|
| 21 | TCL (Lyon urban) GTFS | https://data.grandlyon.com/portail/fr/connexion → register → `tcl_sytral.tcltheorique` | `data/gtfs_lyon/` | `lyon_tcl.zip` | ~50 MB |

Optional community fallback (Google-mediated, use with caution):
```
https://gtech-transit-prod.apigee.net/v1/google/gtfs/odbl/lyon_tcl.zip?apikey=...&secret=...
```
See `download_lyon_data.py --include-tcl` to attempt it.

---

## Optional data

- **EMP 2019** (National Person Mobility Survey) — newer alternative to ENTD 2008.
  Landing: https://www.statistiques.developpement-durable.gouv.fr/resultats-detailles-de-lenquete-mobilite-des-personnes-de-2019 → `data/emp_2019/`
- **EDGT Lyon 2015** (Regional household travel survey) — requires ADISP/CEREMA
  researcher access. Landing: http://www.progedo-adisp.fr/serie_emd.php → `data/edgt_lyon_2015/`.
  Activates via `hts: edgt_lyon` + `edgt_lyon_source: adisp` (or `cerema`) in `config.yml`.

---

## After downloading, verify

From this repo root:

```bash
python verify_data.py     # upstream sanity check
ls -lhR data/             # eyeball file layout against the tables above
```

Then run the pipeline:

```bash
python -m synpp config.yml
```
