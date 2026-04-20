#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas>=0.14",
#   "shapely>=2.0",
#   "pandas>=2.0",
#   "requests>=2.31",
# ]
# ///
"""
Build a GeoJSON cutter polygon for eqasim-france's RunScenarioCutter.

Given a set of INSEE commune codes and a radius, produces a circle:
union of selected communes → centroid (Lambert-93) → buffer(radius_km)
→ reproject to WGS84 → GeoJSON FeatureCollection.

Feeds `matsim.simulation.cut` stage in eqasim-france's synpp pipeline.

Config snippet to enable the cutter in eqasim-france:

  run:
    - matsim.simulation.cut
  config:
    cutter:
      path: cutter
      file: cutter.geojson
      name: lyon_drt_area
      after_full_simulation: True   # avoid boundary effects

Usage:
  uv run scenario-selection/build_cutter_polygon.py \\
      --communes 01224 01378 01361 \\
      --radius-km 40 \\
      --output data/cutter/lyon_drt_area.geojson
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import requests
from shapely.ops import unary_union

ROOT = Path(__file__).parent
DEFAULT_COMMUNES_FILE = ROOT / "data" / "communes-100m.geojson"
DEFAULT_OUTPUT = ROOT / "output" / "cutter.geojson"
COMMUNES_URL = (
    "https://etalab-datasets.geo.data.gouv.fr/"
    "contours-administratifs/2025/geojson/communes-100m.geojson"
)

LAMBERT93 = "EPSG:2154"  # metric CRS for metropolitan France — centroid + buffer
WGS84 = "EPSG:4326"      # standard GeoJSON CRS


def download_communes(dest: Path) -> None:
    if dest.exists():
        return
    print(f"downloading {dest.name}…")
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(COMMUNES_URL, stream=True, timeout=600)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    print(f"  saved {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


def build_polygon(
    communes_file: Path,
    commune_codes: Iterable[str],
    radius_km: float,
    output: Path,
) -> None:
    codes = sorted({c.strip().upper() for c in commune_codes})
    print(f"reading {communes_file}…")
    communes = gpd.read_file(communes_file)
    code_col = "code" if "code" in communes.columns else communes.columns[0]

    sel = communes[communes[code_col].isin(codes)].copy()
    missing = set(codes) - set(sel[code_col])
    if missing:
        raise ValueError(f"commune codes not found: {sorted(missing)}")
    name_col = "nom" if "nom" in sel.columns else None
    print(f"selected {len(sel)} communes:")
    for _, r in sel.iterrows():
        label = r[name_col] if name_col else ""
        print(f"  {r[code_col]}  {label}")

    sel_l93 = sel.to_crs(LAMBERT93)
    union = unary_union(sel_l93.geometry.values)
    centroid_l93 = union.centroid
    centroid_wgs = (
        gpd.GeoSeries([centroid_l93], crs=LAMBERT93).to_crs(WGS84).iloc[0]
    )
    print(
        f"union centroid: lat={centroid_wgs.y:.6f}  lon={centroid_wgs.x:.6f}"
        f"  (Lambert-93: x={centroid_l93.x:.1f}  y={centroid_l93.y:.1f})"
    )

    buffer_l93 = centroid_l93.buffer(radius_km * 1000.0)
    buffer_wgs = (
        gpd.GeoSeries([buffer_l93], crs=LAMBERT93).to_crs(WGS84).iloc[0]
    )
    minx, miny, maxx, maxy = buffer_wgs.bounds
    print(
        f"buffer radius: {radius_km:.1f} km"
        f"  |  bbox  lon[{minx:.4f}, {maxx:.4f}]  lat[{miny:.4f}, {maxy:.4f}]"
    )

    all_l93 = communes.to_crs(LAMBERT93)
    inside_mask = all_l93.geometry.intersects(buffer_l93)
    n_inside = int(inside_mask.sum())
    n_fully = int(all_l93[inside_mask].geometry.within(buffer_l93).sum())
    print(f"communes inside buffer: {n_inside} ({n_fully} fully contained)")
    if name_col:
        sample = (
            communes[inside_mask]
            .assign(_d=lambda d: d.to_crs(LAMBERT93).geometry.distance(centroid_l93))
            .sort_values("_d")
            [[code_col, name_col]]
            .head(20)
        )
        print("  nearest 20:")
        for _, r in sample.iterrows():
            print(f"    {r[code_col]}  {r[name_col]}")

    output.parent.mkdir(parents=True, exist_ok=True)
    gdf_out = gpd.GeoDataFrame(
        {
            "name": ["cutter"],
            "source_communes": [",".join(codes)],
            "radius_km": [radius_km],
            "centroid_lat": [centroid_wgs.y],
            "centroid_lon": [centroid_wgs.x],
        },
        geometry=[buffer_wgs],
        crs=WGS84,
    )
    if output.exists():
        output.unlink()
    gdf_out.to_file(output, driver="GeoJSON")
    print(f"wrote {output}")

    # Also write a Lambert-93 shapefile companion — eqasim's RunScenarioCutter
    # compares the extent against the MATSim network in its native CRS, which
    # for the France pipeline is EPSG:2154. A WGS84 extent intersects nothing
    # because the coordinate magnitudes don't overlap. The .shp is what the
    # Java cutter actually reads (synpp converts the .geojson → .shp, but
    # without CRS awareness).
    shp_output = output.with_suffix(".shp")
    gdf_l93 = gdf_out.to_crs(LAMBERT93)
    # Shapefile can't hold all attribute types; truncate cleanly.
    gdf_l93 = gdf_l93[["name", "geometry"]]
    # geopandas writes .shp + .shx + .dbf + .prj; remove any stale siblings.
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        stale = shp_output.with_suffix(ext)
        if stale.exists():
            stale.unlink()
    gdf_l93.to_file(shp_output)
    print(f"wrote {shp_output} (Lambert-93 for RunScenarioCutter)")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--communes", nargs="+", required=True, metavar="CODE",
        help="INSEE commune codes (e.g., 01224 01378 01361)",
    )
    p.add_argument(
        "--radius-km", type=float, default=40.0,
        help="buffer radius in km around union centroid (default: 40)",
    )
    p.add_argument(
        "--communes-file", type=Path, default=DEFAULT_COMMUNES_FILE,
        help=f"communes-100m.geojson path (default: {DEFAULT_COMMUNES_FILE.relative_to(ROOT.parent)})",
    )
    p.add_argument(
        "--output", "-o", type=Path, default=DEFAULT_OUTPUT,
        help=f"output GeoJSON path (default: {DEFAULT_OUTPUT.relative_to(ROOT.parent)})",
    )
    args = p.parse_args()

    download_communes(args.communes_file)
    build_polygon(args.communes_file, args.communes, args.radius_km, args.output)


if __name__ == "__main__":
    main()
