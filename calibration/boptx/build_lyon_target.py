"""
Build Lyon-region mode-share calibration target from cached ENTD 2008.

Loads the filtered ENTD pickle from the eqasim-france pipeline cache, filters
to Lyon departments (01, 38, 42, 69), bins trips by euclidean distance, and
writes a boptx shares pickle consumed by ModeShareObjective via `shares_path`.

Also writes reference_trips.csv next to it — required by ModeShareObjective
for its initial bounds computation (the per-bin shares are then overridden
by the pickle).

Fallback: if too few Lyon-region trips remain after filtering, fall back to
national ENTD shares. The user-visible warning will make that obvious.

Usage:
    cd matsim_scenarios/eqasim-france/calibration/boptx
    ../../.venv/Scripts/python build_lyon_target.py
"""
import os
import pickle
import pathlib
import sys

import numpy as np
import pandas as pd


# ENTD filtered cache (produced by synpp `data.hts.entd.filtered` stage).
# Hash is deterministic given the data source + config; for Lyon departments
# (01, 38, 42, 69) this is the cache path.
ENTD_CACHE = "C:/matsim_cache_lyon/data.hts.entd.filtered__e1e2fe5aa0fad92f1984373c7f98a8c1.cache"

# Lyon departments (eqasim-france/config_100pct.yml)
LYON_DEPTS = {"01", "38", "42", "69"}

# Distance bins in METERS — matches Bavaria Kelheim scheme and ENTD distance
# distribution granularity. The <0.5 km and 50-100/>100 km bands can be
# enabled/disabled in one place.
BIN_EDGES_M = [
    (0,       500),
    (500,    1000),
    (1000,   2000),
    (2000,   5000),
    (5000,  10000),
    (10000, 20000),
    (20000, 50000),
]

# Target mode names follow the MATSim / eqasim simulation trip output convention:
# bike gets reported as "bicycle" in the analyzed trips CSV. ENTD filtered
# stores "bike"; we remap on load.
SIM_MODES = ["car", "car_passenger", "pt", "bicycle", "walk"]
ENTD_TO_SIM = {"bike": "bicycle"}


def load_entd_trips(cache_path: str) -> pd.DataFrame:
    """Load the ENTD filtered trips table.

    synpp filtered HTS returns (df_households, df_persons, df_trips); we
    grab the trips DF (index 2). The .p pickle next to the .cache dir
    holds the return value.
    """
    cache_dir = pathlib.Path(cache_path)
    p_file = pathlib.Path(str(cache_dir).replace(".cache", ".p"))
    if not p_file.exists():
        raise FileNotFoundError(f"ENTD pickle not found: {p_file}")

    with open(p_file, "rb") as f:
        obj = pickle.load(f)

    if not (isinstance(obj, tuple) and len(obj) == 3):
        raise TypeError(f"Expected 3-tuple (hh, persons, trips); got {type(obj).__name__}")
    df_trips = obj[2].copy()
    if "mode" not in df_trips.columns:
        raise ValueError(f"Trips DF missing 'mode' column; has: {list(df_trips.columns)}")
    # Remap ENTD mode labels to simulation trip-output labels.
    df_trips["mode"] = df_trips["mode"].astype(str).replace(ENTD_TO_SIM)
    return df_trips


def bin_distances(distances_m: np.ndarray) -> np.ndarray:
    """Assign each distance to a bin index, or -1 if outside the bin range."""
    bin_idx = np.full(len(distances_m), -1, dtype=int)
    for i, (lo, hi) in enumerate(BIN_EDGES_M):
        mask = (distances_m >= lo) & (distances_m < hi)
        bin_idx[mask] = i
    return bin_idx


# ENTD stores routed distance; boptx's ModeShareObjective compares against
# euclidean distance computed from trip endpoint coordinates in the simulation.
# Divide routed by a crow factor to align bin assignments. 1.3 is the typical
# French urban/periurban routed-to-euclidean ratio (Hörl & Balac 2021 report
# ~1.25-1.35 across IdF modes).
CROW_FACTOR = 1.3


def compute_shares(df: pd.DataFrame, weight_col: str = "trip_weight") -> tuple:
    """Compute weighted mode shares per distance bin.

    Returns (shares_dict[mode] -> list, totals per bin).
    """
    if "routed_distance" not in df.columns:
        raise ValueError(f"No routed_distance column. Have: {list(df.columns)}")
    # Convert routed -> euclidean proxy so the target bins align with the
    # simulation's euclidean-based distance reporting.
    dist = df["routed_distance"].to_numpy() / CROW_FACTOR

    weights = df[weight_col].to_numpy()
    modes = df["mode"].astype(str).to_numpy()
    bins = bin_distances(dist)

    # Accumulate weighted counts per (mode, bin)
    n_bins = len(BIN_EDGES_M)
    counts = {m: np.zeros(n_bins) for m in SIM_MODES}
    totals = np.zeros(n_bins)

    for m in SIM_MODES:
        mode_mask = (modes == m)
        for b in range(n_bins):
            bin_mask = (bins == b) & mode_mask
            counts[m][b] = weights[bin_mask].sum()
    for b in range(n_bins):
        totals[b] = sum(counts[m][b] for m in SIM_MODES)

    shares = {m: (counts[m] / np.where(totals > 0, totals, 1.0)).tolist() for m in SIM_MODES}
    return shares, totals


def main():
    print("Loading ENTD trips from cache...")
    df_trips = load_entd_trips(ENTD_CACHE)
    print(f"  Total trips: {len(df_trips):,}")
    print(f"  Columns:     {list(df_trips.columns)[:10]}...")

    # The synpp filtered stage has already restricted to Lyon-region trips
    # (departments 01/38/42/69). Verify it's consistent.
    if "origin_departement_id" in df_trips.columns:
        origin_depts = set(df_trips["origin_departement_id"].astype(str).unique())
        print(f"  Origin departments in set: {sorted(origin_depts)}")
        extraneous = origin_depts - LYON_DEPTS
        if extraneous:
            print(f"  Extraneous departments present (will re-filter): {sorted(extraneous)}")
            df_lyon = df_trips[df_trips["origin_departement_id"].astype(str).isin(LYON_DEPTS)]
        else:
            df_lyon = df_trips
    else:
        df_lyon = df_trips
    print(f"  Lyon-region trips: {len(df_lyon):,}")

    shares, totals = compute_shares(df_lyon)

    # Print summary
    print(f"\nLyon ENTD per-bin mode shares ({len(df_lyon):,} trips):")
    band_labels = [f"{lo/1000:.1f}-{hi/1000:.0f}km" for lo, hi in BIN_EDGES_M]
    header = f"  {'band':12s}  {'n_trips':>10s}  " + "  ".join(f"{m[:5]:>5s}" for m in SIM_MODES)
    print(header)
    for i, (band, total) in enumerate(zip(band_labels, totals)):
        row = f"  {band:12s}  {total:10.0f}  " + "  ".join(
            f"{shares[m][i]*100:5.1f}" for m in SIM_MODES
        )
        print(row)

    # Build boptx pickle payload: (bounds, distance_col_name, shares)
    bounds = {m: [(i, lo, hi) for i, (lo, hi) in enumerate(BIN_EDGES_M)] for m in SIM_MODES}
    payload = (bounds, "euclidean_distance", shares)

    script_dir = pathlib.Path(__file__).resolve().parent
    out_path = script_dir / "data" / "lyon_entd_shares.pkl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump(payload, f)
    print(f"\nWrote {out_path}")

    # Also write CSV for inspection
    csv_path = script_dir / "data" / "lyon_entd_shares.csv"
    with open(csv_path, "w", newline="") as f:
        f.write("mode;bin_idx;lower_m;upper_m;share;n_trips_total\n")
        for m in SIM_MODES:
            for i, (lo, hi) in enumerate(BIN_EDGES_M):
                f.write(f"{m};{i};{lo};{hi};{shares[m][i]:.6f};{totals[i]:.0f}\n")
    print(f"Wrote {csv_path}")

    # reference_trips.csv needed by ModeShareObjective for initial bounds
    # (per-bin shares are overridden by the pickle at runtime).
    if "euclidean_distance" not in df_lyon.columns and "routed_distance" in df_lyon.columns:
        df_lyon = df_lyon.copy()
        df_lyon["euclidean_distance"] = df_lyon["routed_distance"]
    cols = ["mode", "euclidean_distance", "routed_distance"]
    weight_col = next((c for c in ["trip_weight", "weight"] if c in df_lyon.columns), None)
    if weight_col:
        cols.append(weight_col)
    for c in ("preceding_purpose", "following_purpose"):
        if c in df_lyon.columns:
            cols.append(c)
    ref_path = script_dir / "data" / "reference_trips.csv"
    df_lyon[cols].to_csv(ref_path, sep=";", index=False)
    print(f"Wrote {ref_path} ({len(df_lyon):,} rows)")


if __name__ == "__main__":
    main()
