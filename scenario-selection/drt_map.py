"""Helpers for the DRT-suitability interactive map.

Cell-by-cell usage lives in ``captivity_analysis.ipynb`` §10–§11.
These functions are pure (no I/O, no r5py) so they can be unit-tested.
"""

from __future__ import annotations

import geopandas as gpd
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
