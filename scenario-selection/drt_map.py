"""Helpers for the DRT-suitability interactive map.

Cell-by-cell usage lives in ``captivity_analysis.ipynb`` §10–§11.
These functions are pure (no I/O, no r5py) so they can be unit-tested.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd


def top_flows(
    od: pd.DataFrame,
    communes: gpd.GeoDataFrame,
    code: str,
    *,
    n: int,
    direction: str,
) -> list[dict]:
    """Return the top-N partner flows for a commune.

    direction="out" → rows where commune is origin; partner_code = dest
    direction="in"  → rows where commune is dest;   partner_code = origin

    Each returned dict has: partner_code, partner_name, flow (int), partner_ll ([lat, lon]).
    Sorted by flow descending. Empty list if commune not in od.
    """
    if direction not in ("out", "in"):
        raise ValueError(f"direction must be 'out' or 'in', got {direction!r}")

    key, partner = ("origin", "dest") if direction == "out" else ("dest", "origin")
    sub = od[od[key] == code].nlargest(n, "total")
    if sub.empty:
        return []

    lookup = communes.set_index("code")[["nom", "lon", "lat"]]
    out: list[dict] = []
    for _, r in sub.iterrows():
        p = r[partner]
        if p not in lookup.index:
            continue
        nom = lookup.at[p, "nom"]
        lon = float(lookup.at[p, "lon"])
        lat = float(lookup.at[p, "lat"])
        out.append({
            "partner_code": p,
            "partner_name": nom,
            "flow": int(r["total"]),
            "partner_ll": [lat, lon],
        })
    return out


def build_hist_svg(
    distances: np.ndarray,
    weights: np.ndarray,
    *,
    width: int = 320,
    height: int = 120,
    bin_width: float = 5.0,
    max_km: float = 80.0,
    drt_min: float = 10.0,
    drt_max: float = 25.0,
    bar_color: str = "#3498db",
    band_color: str = "#f39c12",
) -> str:
    """Return an inline SVG of a weighted commute-distance histogram.

    Pads/clips to the [0, max_km] range. Shades the [drt_min, drt_max] DRT
    sweet-spot as a translucent overlay (class="drt-band"). Dimensions in
    pixels. No JavaScript — pure static SVG for popup embedding.
    """
    pad_l, pad_r, pad_t, pad_b = 4, 4, 4, 14   # room for axis labels
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    bins = np.arange(0, max_km + bin_width, bin_width)
    n_bins = len(bins) - 1
    counts, _ = (np.histogram(distances, bins=bins, weights=weights)
                 if len(distances) else (np.zeros(n_bins), bins))
    max_c = counts.max() if counts.max() > 0 else 1.0

    parts: list[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']

    # DRT sweet-spot band
    band_x = pad_l + (drt_min / max_km) * plot_w
    band_w = ((drt_max - drt_min) / max_km) * plot_w
    parts.append(
        f'<rect class="drt-band" x="{band_x:.1f}" y="{pad_t}" width="{band_w:.1f}" '
        f'height="{plot_h}" fill="{band_color}" fill-opacity="0.15"/>'
    )

    # Bars
    bar_w = plot_w / n_bins
    for i, c in enumerate(counts):
        if c <= 0:
            continue
        bar_h = (c / max_c) * plot_h
        bx = pad_l + i * bar_w
        by = pad_t + plot_h - bar_h
        parts.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w - 0.5:.1f}" '
            f'height="{bar_h:.1f}" fill="{bar_color}"/>'
        )

    # X-axis ticks at 0, 20, 40, 60, 80 km
    for tick_km in (0, 20, 40, 60, 80):
        tx = pad_l + (tick_km / max_km) * plot_w
        parts.append(
            f'<text x="{tx:.1f}" y="{height - 2}" font-size="9" '
            f'text-anchor="middle" fill="#555">{tick_km}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)
