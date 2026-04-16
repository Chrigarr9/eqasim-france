#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas>=2.0",
#   "geopandas>=0.14",
#   "matplotlib>=3.8",
#   "pyarrow>=14.0",
#   "requests>=2.31",
# ]
# ///
"""
France Scenario Selection: Identify regions suitable for DRT ridepooling.

Uses INSEE MOBPRO 2022 commuter microdata (census transport mode per worker)
as a revealed-preference indicator of PT accessibility. High car share for
inter-commune commuting = poor PT alternatives = DRT opportunity.

Reference: UFC-Que Choisir (2024) mapped PT "zones blanches" — 10M+ French
without PT within 10-min walk. Our MOBPRO-based analysis captures the same
phenomenon from actual commuter behavior.

Produces:
  1. National choropleth: inter-commune car share by commune
  2. National choropleth: PT share by commune
  3. National choropleth: DRT opportunity score
  4. Département ranking table (CSV + console)
  5. Regional zoom maps for top candidate areas

Run:  uv run scenario-selection/analyze_regions.py
"""

from pathlib import Path

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

# ── Data URLs ────────────────────────────────────────────────────────────────

MOBPRO_URL = (
    "https://www.insee.fr/fr/statistiques/fichier/8589904/RP2022_mobpro.parquet"
)
COMMUNES_URL = (
    "https://etalab-datasets.geo.data.gouv.fr/"
    "contours-administratifs/2025/geojson/communes-100m.geojson"
)
DEPTS_URL = (
    "https://etalab-datasets.geo.data.gouv.fr/"
    "contours-administratifs/2025/geojson/departements-100m.geojson"
)

# ── MOBPRO TRANS codes (float64 in parquet) ──────────────────────────────────
#  1 = no commute (WFH)   2 = walk   3 = bicycle
#  4 = motorbike           5 = car    6 = public transit

ACTIVE_MODES = {2.0, 3.0, 4.0, 5.0, 6.0}  # exclude WFH (1.0)


# ── Download helpers ─────────────────────────────────────────────────────────


def download(url: str, dest: Path, label: str = "") -> None:
    if dest.exists():
        print(f"  [cached] {label or dest.name}")
        return
    print(f"  downloading {label or dest.name} ...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=600)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    written = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            f.write(chunk)
            written += len(chunk)
            if total:
                print(
                    f"\r  downloading {label or dest.name} ... "
                    f"{written / 1e6:.0f}/{total / 1e6:.0f} MB",
                    end="",
                    flush=True,
                )
    print()


def download_all() -> None:
    print("=== Downloading data ===")
    download(MOBPRO_URL, DATA_DIR / "RP2022_mobpro.parquet", "MOBPRO 2022")
    download(COMMUNES_URL, DATA_DIR / "communes-100m.geojson", "commune boundaries")
    download(DEPTS_URL, DATA_DIR / "departements-100m.geojson", "département boundaries")
    print()


# ── MOBPRO processing ────────────────────────────────────────────────────────


def process_mobpro() -> pd.DataFrame:
    """Compute per-commune commuter mode shares from MOBPRO microdata.

    Returns DataFrame indexed by commune code with columns:
      total_commuters, car_share, pt_share, bike_share, walk_share,
      inter_commuters, inter_car_share, inter_pt_share, dept
    """
    print("=== Processing MOBPRO 2022 ===")
    cols = ["COMMUNE", "DCLT", "ILT", "TRANS", "IPONDI"]
    df = pd.read_parquet(DATA_DIR / "RP2022_mobpro.parquet", columns=cols)
    print(f"  {len(df):,} records loaded")

    # Active commuters only (exclude WFH=1.0)
    comm = df[df["TRANS"].isin(ACTIVE_MODES)].copy()
    print(f"  {len(comm):,} active commuters")

    # ── All commuters: per-commune mode shares ──
    weights = comm.groupby(["COMMUNE", "TRANS"])["IPONDI"].sum().unstack(fill_value=0)
    totals = weights.sum(axis=1)

    stats = pd.DataFrame(
        {
            "total_commuters": totals,
            "car_share": weights.get(5.0, 0) / totals,
            "pt_share": weights.get(6.0, 0) / totals,
            "bike_share": weights.get(3.0, 0) / totals,
            "walk_share": weights.get(2.0, 0) / totals,
        }
    )

    # ── Inter-commune commuters (ILT != 1.0) — DRT-relevant ──
    inter = comm[comm["ILT"] != 1.0]
    iw = inter.groupby(["COMMUNE", "TRANS"])["IPONDI"].sum().unstack(fill_value=0)
    itot = iw.sum(axis=1)

    stats["inter_commuters"] = itot
    stats["inter_car_share"] = iw.get(5.0, 0) / itot
    stats["inter_pt_share"] = iw.get(6.0, 0) / itot

    # Fill communes with zero inter-commune commuters
    stats[["inter_commuters", "inter_car_share", "inter_pt_share"]] = stats[
        ["inter_commuters", "inter_car_share", "inter_pt_share"]
    ].fillna(0)

    # Département code from first 2 characters (index may be categorical)
    stats["dept"] = stats.index.astype(str).str[:2]

    # Metropolitan France only (01-95, 2A, 2B)
    metro = {f"{i:02d}" for i in range(1, 96)} | {"2A", "2B"}
    stats = stats[stats["dept"].isin(metro)]

    wt = stats["total_commuters"]
    total = wt.sum()
    print(f"  {len(stats):,} metropolitan communes")
    print(f"  total commuters: {total:,.0f}")
    if total > 0:
        print(f"  national car share: {(stats['car_share'] * wt).sum() / total:.1%}")
        print(f"  national PT share:  {(stats['pt_share'] * wt).sum() / total:.1%}")
    print()

    return stats


# ── Département-level aggregation ────────────────────────────────────────────


def aggregate_departments(stats: pd.DataFrame) -> pd.DataFrame:
    """Commuter-weighted département-level summary."""
    print("=== Département ranking ===")

    def wavg(group: pd.DataFrame, col: str, weight: str) -> float:
        w = group[weight]
        return (group[col] * w).sum() / w.sum() if w.sum() > 0 else 0.0

    rows = []
    for dept, g in stats.groupby("dept"):
        row = {
            "dept": dept,
            "n_communes": len(g),
            "total_commuters": g["total_commuters"].sum(),
            "inter_commuters": g["inter_commuters"].sum(),
            "car_share": wavg(g, "car_share", "total_commuters"),
            "pt_share": wavg(g, "pt_share", "total_commuters"),
            "inter_car_share": wavg(g, "inter_car_share", "inter_commuters"),
            "inter_pt_share": wavg(g, "inter_pt_share", "inter_commuters"),
        }
        # DRT opportunity: high inter-commune car share, low PT, sufficient volume
        # Exclude very small départements (< 5000 inter-commune commuters)
        row["drt_score"] = (
            row["inter_car_share"]
            * (1 - row["inter_pt_share"])
            * np.log1p(row["inter_commuters"])
        )
        rows.append(row)

    dept_df = pd.DataFrame(rows).set_index("dept").sort_values(
        "drt_score", ascending=False
    )

    # Print top 20
    print("\n  Top 20 départements by DRT opportunity score:")
    print("  " + "─" * 80)
    print(
        f"  {'Dept':>4}  {'Communes':>8}  {'Commuters':>10}  "
        f"{'Car%':>5}  {'PT%':>5}  {'InterCar%':>9}  {'InterPT%':>8}  {'Score':>6}"
    )
    print("  " + "─" * 80)
    for dept, r in dept_df.head(20).iterrows():
        print(
            f"  {dept:>4}  {r['n_communes']:>8.0f}  {r['total_commuters']:>10,.0f}  "
            f"{r['car_share']:>5.1%}  {r['pt_share']:>5.1%}  "
            f"{r['inter_car_share']:>8.1%}  {r['inter_pt_share']:>7.1%}  "
            f"{r['drt_score']:>6.2f}"
        )
    print()

    return dept_df


# ── Map plotting ─────────────────────────────────────────────────────────────

# France metropolitan bounds (approx, for axis limits)
FR_BOUNDS = (-5.2, 41.3, 9.6, 51.1)  # (minx, miny, maxx, maxy)


def load_geometries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load commune and département boundaries."""
    print("=== Loading geometries ===")
    communes = gpd.read_file(DATA_DIR / "communes-100m.geojson")
    depts = gpd.read_file(DATA_DIR / "departements-100m.geojson")

    # Filter to metropolitan France
    metro_codes = {f"{i:02d}" for i in range(1, 96)} | {"2A", "2B"}
    dept_col = "codeDepartement" if "codeDepartement" in depts.columns else "code"
    depts = depts[depts[dept_col].isin(metro_codes)]

    # Commune département from first 2 chars of code
    code_col = "code" if "code" in communes.columns else communes.columns[0]
    communes["dept"] = communes[code_col].str[:2]
    communes = communes[communes["dept"].isin(metro_codes)]

    print(f"  {len(communes):,} commune polygons")
    print(f"  {len(depts):,} département polygons")
    print()
    return communes, depts


def plot_national_choropleth(
    gdf: gpd.GeoDataFrame,
    dept_gdf: gpd.GeoDataFrame,
    column: str,
    title: str,
    filename: str,
    cmap: str = "RdYlGn_r",
    vmin: float = 0,
    vmax: float = 1,
    label: str = "",
    reverse_cbar: bool = False,
) -> None:
    """Plot a national choropleth map at commune level with département borders."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 14), facecolor="white")

    # Filter out communes missing the column
    plot_gdf = gdf.dropna(subset=[column])

    plot_gdf.plot(
        column=column,
        ax=ax,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        linewidth=0,
        antialiased=False,
    )

    # Département borders
    dept_gdf.boundary.plot(ax=ax, linewidth=0.3, color="#333333", alpha=0.5)

    ax.set_xlim(FR_BOUNDS[0], FR_BOUNDS[2])
    ax.set_ylim(FR_BOUNDS[1], FR_BOUNDS[3])
    ax.set_axis_off()
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)

    # Colorbar
    sm = plt.cm.ScalarMappable(
        cmap=cmap, norm=mcolors.Normalize(vmin=vmin, vmax=vmax)
    )
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, shrink=0.6)
    cbar.set_label(label or column, fontsize=11)
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def plot_drt_score(
    gdf: gpd.GeoDataFrame,
    dept_gdf: gpd.GeoDataFrame,
) -> None:
    """Plot DRT opportunity score: high car + low PT + sufficient volume."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 14), facecolor="white")

    plot_gdf = gdf.dropna(subset=["drt_score"])

    # Use quantile-based normalization for better contrast
    vmax = plot_gdf["drt_score"].quantile(0.95)
    vmin = plot_gdf["drt_score"].quantile(0.05)

    plot_gdf.plot(
        column="drt_score",
        ax=ax,
        cmap="YlOrRd",
        vmin=vmin,
        vmax=vmax,
        linewidth=0,
        antialiased=False,
    )

    dept_gdf.boundary.plot(ax=ax, linewidth=0.3, color="#333333", alpha=0.5)

    ax.set_xlim(FR_BOUNDS[0], FR_BOUNDS[2])
    ax.set_ylim(FR_BOUNDS[1], FR_BOUNDS[3])
    ax.set_axis_off()
    ax.set_title(
        "DRT Opportunity Score\n(high car dependency × low PT × commuter volume)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    sm = plt.cm.ScalarMappable(
        cmap="YlOrRd", norm=mcolors.Normalize(vmin=vmin, vmax=vmax)
    )
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, shrink=0.6)
    cbar.set_label("DRT opportunity score", fontsize=11)

    out = OUTPUT_DIR / "france_drt_opportunity.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def plot_regional_zoom(
    gdf: gpd.GeoDataFrame,
    dept_gdf: gpd.GeoDataFrame,
    region_depts: list[str],
    region_name: str,
    filename: str,
) -> None:
    """3-panel zoom for a region: car share, PT share, DRT score."""
    region_gdf = gdf[gdf["dept"].isin(region_depts)]
    region_dept_gdf = dept_gdf[
        dept_gdf[
            "codeDepartement" if "codeDepartement" in dept_gdf.columns else "code"
        ].isin(region_depts)
    ]

    if region_gdf.empty:
        print(f"  [skip] No data for {region_name}")
        return

    bounds = region_gdf.total_bounds  # (minx, miny, maxx, maxy)
    pad = 0.1
    xlim = (bounds[0] - pad, bounds[2] + pad)
    ylim = (bounds[1] - pad, bounds[3] + pad)

    fig, axes = plt.subplots(1, 3, figsize=(24, 10), facecolor="white")

    panels = [
        ("inter_car_share", "Inter-commune car share", "RdYlGn_r", 0.4, 1.0),
        ("inter_pt_share", "Inter-commune PT share", "RdYlGn", 0.0, 0.3),
        ("drt_score", "DRT opportunity score", "YlOrRd", None, None),
    ]

    for ax, (col, title, cmap, vmin, vmax) in zip(axes, panels):
        plot_data = region_gdf.dropna(subset=[col])
        if vmin is None:
            vmin = plot_data[col].quantile(0.05)
            vmax = plot_data[col].quantile(0.95)

        plot_data.plot(
            column=col, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax,
            linewidth=0.1, edgecolor="#cccccc",
        )
        region_dept_gdf.boundary.plot(ax=ax, linewidth=1.0, color="#333333")

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_axis_off()
        ax.set_title(title, fontsize=13, fontweight="bold")

        sm = plt.cm.ScalarMappable(
            cmap=cmap, norm=mcolors.Normalize(vmin=vmin, vmax=vmax)
        )
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, shrink=0.7)
        if col.endswith("_share"):
            cbar.ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f"{x:.0%}")
            )

    fig.suptitle(
        f"{region_name} — Commuter Analysis",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download
    download_all()

    # 2. Process MOBPRO
    stats = process_mobpro()

    # 3. Département ranking
    dept_df = aggregate_departments(stats)
    dept_df.to_csv(OUTPUT_DIR / "department_ranking.csv")
    print(f"  saved {OUTPUT_DIR / 'department_ranking.csv'}")

    # 4. Load geometries and merge
    communes, depts = load_geometries()
    code_col = "code" if "code" in communes.columns else communes.columns[0]
    # Drop dept from stats to avoid collision with communes' dept column
    merged = communes.merge(
        stats.drop(columns=["dept"]),
        left_on=code_col, right_index=True, how="left",
    )

    # Per-commune DRT score: car_share * (1 - pt_share) * log(1 + inter_commuters)
    merged["drt_score"] = (
        merged["inter_car_share"]
        * (1 - merged["inter_pt_share"])
        * np.log1p(merged["inter_commuters"])
    )

    # 5. National maps
    print("\n=== Generating national maps ===")
    plot_national_choropleth(
        merged, depts,
        column="inter_car_share",
        title="Inter-commune Commuter Car Share (MOBPRO 2022)",
        filename="france_car_share.png",
        cmap="RdYlGn_r",
        vmin=0.4, vmax=1.0,
        label="Car mode share (inter-commune commuters)",
    )
    plot_national_choropleth(
        merged, depts,
        column="inter_pt_share",
        title="Inter-commune Commuter PT Share (MOBPRO 2022)",
        filename="france_pt_share.png",
        cmap="RdYlGn",
        vmin=0.0, vmax=0.3,
        label="PT mode share (inter-commune commuters)",
    )
    plot_drt_score(merged, depts)

    # 6. Regional zoom maps for eqasim-ready regions + other candidates
    print("\n=== Generating regional zoom maps ===")

    regions = {
        # eqasim-france documented configs
        "Lyon / Auvergne": (
            ["01", "07", "26", "38", "42", "43", "63", "69", "73", "74"],
            "zoom_auvergne_rhone_alpes.png",
        ),
        "Toulouse / Occitanie": (
            ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
            "zoom_occitanie.png",
        ),
        "Nantes / Pays de la Loire": (
            ["44", "49", "53", "72", "85"],
            "zoom_pays_de_la_loire.png",
        ),
        # Other potentially interesting regions
        "Brittany": (
            ["22", "29", "35", "56"],
            "zoom_bretagne.png",
        ),
        "Bourgogne-Franche-Comté": (
            ["21", "25", "39", "58", "70", "71", "89", "90"],
            "zoom_bourgogne_fc.png",
        ),
    }

    for name, (dept_list, fname) in regions.items():
        plot_regional_zoom(merged, depts, dept_list, name, fname)

    # 7. Summary: top regions for eqasim compatibility
    print("\n=== Summary: eqasim-compatible regions ===")
    eqasim_regions = {
        "Lyon (Ain/Isère/Loire/Rhône)": ["01", "38", "42", "69"],
        "Lyon extended (+ Ardèche/Drôme/Savoie)": [
            "01", "07", "26", "38", "42", "69", "73", "74",
        ],
        "Toulouse core": ["31", "32", "81", "82"],
        "Nantes / Loire-Atlantique": ["44"],
    }

    print(f"\n  {'Region':<42} {'InterCar%':>9} {'InterPT%':>8} {'Commuters':>10}")
    print("  " + "─" * 72)
    for name, dept_list in eqasim_regions.items():
        sub = stats[stats["dept"].isin(dept_list)]
        ic = sub["inter_commuters"].sum()
        if ic > 0:
            ic_car = (sub["inter_car_share"] * sub["inter_commuters"]).sum() / ic
            ic_pt = (sub["inter_pt_share"] * sub["inter_commuters"]).sum() / ic
        else:
            ic_car = ic_pt = 0
        print(f"  {name:<42} {ic_car:>8.1%} {ic_pt:>7.1%} {ic:>10,.0f}")

    print("\nDone. Check output/ for maps and department_ranking.csv")


if __name__ == "__main__":
    main()
