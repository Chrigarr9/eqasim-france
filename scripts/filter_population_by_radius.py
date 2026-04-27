"""Filter Lyon eqasim population to agents with activities within a radius of a center point.

Produces filtered CSVs and GPKGs for analysis notebooks.
Does NOT produce population XML — the Java runner handles that at runtime.

Usage:
    # By coordinates (EPSG:2154 Lambert-93):
    python scripts/filter_population_by_radius.py \
        --input output_100pct \
        --prefix lyon_100pct_ \
        --radius 30 \
        --center 862000,6525000

    # By commune name (looks up centroid from IGN IRIS shapes):
    python scripts/filter_population_by_radius.py \
        --input output_100pct \
        --prefix lyon_100pct_ \
        --radius 30 \
        --commune "Ambérieu-en-Bugey"
"""
import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


def java_hashcode(s: str) -> int:
    """Replicate Java's String.hashCode() for deterministic nested sampling.

    Matches RunCreatePermanentPopulations.java: abs(id.toString().hashCode()) % 100 < pct.
    Samples are automatically nested: 1% ⊂ 10% ⊂ 25% ⊂ 100%.
    """
    h = np.int32(0)
    for c in s:
        h = np.int32(31) * h + np.int32(ord(c))
    return int(abs(h))


def resolve_commune_center(name: str, iris_path: str) -> tuple[float, float]:
    """Look up a commune by name in the IGN IRIS GeoPackage and return its centroid in EPSG:2154.

    Matches case-insensitively on NOM_COM. Dissolves all IRIS polygons for the
    commune into a single shape before computing centroid.
    """
    iris_path = Path(iris_path)
    if not iris_path.exists():
        raise FileNotFoundError(f"IRIS GeoPackage not found: {iris_path}")

    gdf = gpd.read_file(iris_path)
    matches = gdf[gdf["nom_commune"].str.lower() == name.lower()]

    if matches.empty:
        # Try partial match
        matches = gdf[gdf["nom_commune"].str.lower().str.contains(name.lower())]
        if matches.empty:
            raise ValueError(
                f"Commune '{name}' not found in IRIS data (nom_commune column). "
                f"Check spelling or use --center x,y coordinates directly."
            )
        print(f"Partial match: found {matches['nom_commune'].nunique()} candidate(s)")

    # Dissolve all IRIS polygons for the commune
    commune = matches.dissolve()
    centroid = commune.geometry.iloc[0].centroid
    insee = matches["code_insee"].iloc[0]
    print(f"Resolved '{name}' -> INSEE {insee}, centroid=({centroid.x:.0f}, {centroid.y:.0f})")
    return centroid.x, centroid.y


def main():
    parser = argparse.ArgumentParser(description="Filter Lyon population by radius around center point")
    parser.add_argument("--input", required=True, help="Input directory with eqasim output")
    parser.add_argument("--prefix", required=True, help="File prefix (e.g. lyon_100pct_)")
    parser.add_argument("--radius", type=float, default=30.0, help="Radius in km (default: 30)")
    parser.add_argument("--center", default=None,
                        help="Center point x,y in EPSG:2154 Lambert-93 (e.g. 862000,6525000)")
    parser.add_argument("--commune", default=None,
                        help="Commune name to use as center (looks up centroid from IGN IRIS shapes)")
    parser.add_argument("--iris", default="C:/matsim_cache_lyon/data.spatial.iris__313f85918c6e46308216ee3a4e29de83.cache/CONTOURS-IRIS_3-0__GPKG_LAMB93_FXX_2024-01-01/CONTOURS-IRIS/1_DONNEES_LIVRAISON_2024-12-00163/CONTOURS-IRIS_3-0_GPKG_LAMB93_FXX-ED2024-01-01/contours-iris.gpkg",
                        help="Path to IGN IRIS GeoPackage")
    parser.add_argument("--sample", type=float, default=1.0,
                        help="Fraction of persons to keep after radius filter, e.g. 0.1 for 10%% (default: 1.0). "
                             "Uses hash-based deterministic sampling (nested: 1%%⊂10%%⊂25%%⊂100%%).")
    parser.add_argument("--output", default=None, help="Output directory (default: <input>/filtered_<radius>km_<commune>)")
    args = parser.parse_args()

    if args.commune is None and args.center is None:
        parser.error("Provide either --commune or --center")

    input_dir = Path(args.input)
    prefix = args.prefix
    radius_m = args.radius * 1000.0

    if args.commune:
        cx, cy = resolve_commune_center(args.commune, args.iris)
        label = args.commune.replace(" ", "_").replace("é", "e").replace("è", "e").replace("â", "a")
    else:
        cx, cy = [float(v) for v in args.center.split(",")]
        label = f"{int(cx)}_{int(cy)}"

    sample_label = f"_{int(args.sample * 100)}pct" if args.sample < 1.0 else ""
    output_dir = Path(args.output) if args.output else input_dir / f"filtered_{int(args.radius)}km_{label}{sample_label}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input:  {input_dir}")
    print(f"Center: ({cx:.0f}, {cy:.0f}), Radius: {args.radius} km")
    print(f"Output: {output_dir}")

    # --- Step 1: Load activities with geometry and find persons within radius ---
    activities_gpkg = input_dir / f"{prefix}activities.gpkg"
    print(f"\nLoading {activities_gpkg.name} ...")
    gdf_activities = gpd.read_file(activities_gpkg)

    gdf_activities["dist_to_center"] = np.sqrt(
        (gdf_activities.geometry.x - cx) ** 2 +
        (gdf_activities.geometry.y - cy) ** 2
    )

    within = gdf_activities[gdf_activities["dist_to_center"] <= radius_m]
    keep_persons = set(within["person_id"].unique())
    total_persons = gdf_activities["person_id"].nunique()

    print(f"Persons within {args.radius} km: {len(keep_persons):,} / {total_persons:,} "
          f"({len(keep_persons)/total_persons:.1%})")

    # Downsample using hash-based deterministic sampling (matches RunCreatePermanentPopulations.java)
    if args.sample < 1.0:
        pct = int(args.sample * 100)
        keep_persons = {pid for pid in keep_persons if java_hashcode(str(pid)) % 100 < pct}
        print(f"Hash-downsampled to {args.sample:.0%}: {len(keep_persons):,} persons")

    # --- Step 2: Filter and write activities GPKG ---
    gdf_filtered = gdf_activities[gdf_activities["person_id"].isin(keep_persons)].copy()
    gdf_filtered = gdf_filtered.drop(columns=["dist_to_center"])
    out_path = output_dir / f"{prefix}activities.gpkg"
    gdf_filtered.to_file(out_path, driver="GPKG")
    print(f"  Wrote {out_path.name}: {len(gdf_filtered):,} activities")

    # --- Step 3: Filter CSVs ---
    keep_hh = None
    for name in ["persons", "activities", "trips", "households"]:
        csv_path = input_dir / f"{prefix}{name}.csv"
        if not csv_path.exists():
            print(f"  Skipping {csv_path.name} (not found)")
            continue

        df = pd.read_csv(csv_path, sep=";")

        if name == "households":
            persons_csv = input_dir / f"{prefix}persons.csv"
            df_persons = pd.read_csv(persons_csv, sep=";")
            keep_hh = set(df_persons[df_persons["person_id"].isin(keep_persons)]["household_id"])
            df_out = df[df["household_id"].isin(keep_hh)]
        else:
            df_out = df[df["person_id"].isin(keep_persons)]

        out_path = output_dir / f"{prefix}{name}.csv"
        df_out.to_csv(out_path, sep=";", index=False)
        print(f"  Wrote {out_path.name}: {len(df_out):,} rows")

    # --- Step 4: Filter spatial files ---
    for name in ["homes", "trips", "commutes"]:
        gpkg_path = input_dir / f"{prefix}{name}.gpkg"
        if not gpkg_path.exists():
            print(f"  Skipping {gpkg_path.name} (not found)")
            continue

        gdf = gpd.read_file(gpkg_path)
        if "person_id" in gdf.columns:
            gdf_out = gdf[gdf["person_id"].isin(keep_persons)]
        elif "household_id" in gdf.columns and keep_hh is not None:
            gdf_out = gdf[gdf["household_id"].isin(keep_hh)]
        else:
            print(f"  Skipping {gpkg_path.name} (no person_id or household_id column)")
            continue

        out_path = output_dir / f"{prefix}{name}.gpkg"
        gdf_out.to_file(out_path, driver="GPKG")
        print(f"  Wrote {out_path.name}: {len(gdf_out):,} rows")

    # --- Summary ---
    removed = total_persons - len(keep_persons)
    print(f"\nDone. Kept {len(keep_persons):,} persons ({len(keep_persons)/total_persons:.1%}), "
          f"removed {removed:,} outside {args.radius} km radius.")


if __name__ == "__main__":
    main()
