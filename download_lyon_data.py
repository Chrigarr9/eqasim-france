#!/usr/bin/env python3
"""Download auto-fetchable data for the Lyon eqasim scenario.

Handles BAN adresses (4 départements), OSM Rhône-Alpes Geofabrik extract,
and 6/7 GTFS feeds. The Lyon TCL GTFS is auth-gated on data.grandlyon.com,
so this script falls back to a community Google-Apigee-mediated mirror.

INSEE parquet/xlsx, IGN BD TOPO 2022, and ENTD 2008 CSVs are click-through
web forms — documented in DOWNLOAD_LYON_DATA.md.

Run from the repo root: `python download_lyon_data.py`

Scopes:
  (default)             — full eqasim pipeline inputs (BAN + OSM + GTFS).
  --scenario-selection  — only what the scenario-selection notebook needs
                          (OSM + GTFS, TCL auto-included). Skips BAN.
  --include-tcl         — force TCL fetch even in full-pipeline mode.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

BAN_DEPTS = ["01", "38", "42", "69"]

# (url, subdir, filename, scope)
#   scope "full"     = eqasim pipeline only (skipped by --scenario-selection)
#   scope "both"     = needed for both pipeline and scenario-selection
DOWNLOADS: list[tuple[str, str, str, str]] = [
    *[
        (
            f"https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{d}.csv.gz",
            "ban_lyon",
            f"adresses-{d}.csv.gz",
            "full",
        )
        for d in BAN_DEPTS
    ],
    (
        "https://download.geofabrik.de/europe/france/rhone-alpes-220101.osm.pbf",
        "osm_lyon",
        "rhone-alpes-220101.osm.pbf",
        "both",
    ),
    (
        "https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip",
        "gtfs_lyon",
        "sncf-tgv-intercite-ter.gtfs.zip",
        "both",
    ),
    (
        "https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=OURA&dataFormat=GTFS&dataProfil=OPENDATA",
        "gtfs_lyon",
        "oura.gtfs.zip",
        "both",
    ),
    (
        "https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=CARS_REGION_LOIRE&dataFormat=GTFS&dataProfil=OPENDATA",
        "gtfs_lyon",
        "stas.gtfs.zip",
        "both",
    ),
    (
        "https://api.oura3.cityway.fr/dataflow/offre-tc/download?provider=CARS_REGION_EXPRESS&dataFormat=GTFS&dataProfil=OPENDATA",
        "gtfs_lyon",
        "express.gtfs.zip",
        "both",
    ),
    (
        "https://s3.eu-west-1.amazonaws.com/files.orchestra.ratpdev.com/networks/vienne-mobi/exports/medias.zip",
        "gtfs_lyon",
        "medias.zip",
        "both",
    ),
    (
        "https://data.mobilites-m.fr/api/gtfs/BUL",
        "gtfs_lyon",
        "BUL-GTFS.zip",
        "both",
    ),
]

TCL_FALLBACK: tuple[str, str, str, str] = (
    "https://gtech-transit-prod.apigee.net/v1/google/gtfs/odbl/lyon_tcl.zip"
    "?apikey=BasyG6OFZXgXnzWdQLTwJFGcGmeOs204&secret=gNo6F5PhQpsGRBCK",
    "gtfs_lyon",
    "lyon_tcl.zip",
    "both",
)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip] {dest.name} ({human(dest.stat().st_size)})")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  [get]  {url}")
    print(f"         -> {dest.relative_to(HERE)}")
    req = urllib.request.Request(url, headers={"User-Agent": "eqasim-lyon-dl/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, tmp.open("wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            got = 0
            while True:
                chunk = resp.read(1 << 18)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                pct = f" ({100 * got / total:.0f}%)" if total else ""
                print(f"\r         {human(got)}{pct}   ", end="", flush=True)
            print()
        tmp.rename(dest)
        return True
    except Exception as e:
        print(f"  [fail] {e}")
        if tmp.exists():
            tmp.unlink()
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--scenario-selection",
        action="store_true",
        help="Minimal download for the scenario-selection notebook: OSM + GTFS only "
        "(no BAN); TCL community fallback auto-enabled.",
    )
    parser.add_argument(
        "--include-tcl",
        action="store_true",
        help="Force community Google-Apigee TCL GTFS fallback. Auto-enabled with --scenario-selection.",
    )
    args = parser.parse_args()

    want_tcl = args.include_tcl or args.scenario_selection
    if args.scenario_selection:
        items = [d for d in DOWNLOADS if d[3] in ("both",)]
    else:
        items = [d for d in DOWNLOADS if d[3] in ("full", "both")]
    if want_tcl:
        items = items + [TCL_FALLBACK]

    fails = 0
    for url, subdir, filename, _scope in items:
        print(f"\n== {subdir}/{filename} ==")
        if not download(url, DATA / subdir / filename):
            fails += 1

    ok = len(items) - fails
    print(f"\nDone: {ok}/{len(items)} successful.")
    if not want_tcl:
        print(
            "\nLyon TCL GTFS not attempted. Either register at "
            "https://data.grandlyon.com/portail/fr/connexion and place "
            "lyon_tcl.zip in data/gtfs_lyon/, or re-run with --include-tcl."
        )
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
