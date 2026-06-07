# Self-contained: reads only output/commune_pareto_ranking.csv, data/communes-100m.geojson,
# data/RP2022_mobpro.parquet, cache/ttm_expanded.parquet — NO r5py re-run. Safe on a cold kernel.
# Replicates §2 (OD build), §7 (centroids), §14 (SV cluster) then exports the two slide figures.
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

HERE = Path.cwd()
DATA, CACHE, OUT = HERE / "data", HERE / "cache", HERE / "output"
LYON_CENTRE_LON, LYON_CENTRE_LAT = 4.8590, 45.7607   # Part-Dieu
LYON_DEPTS = {"01", "38", "42", "69"}
LYON_ZONE_KM = 10.0
SV_CODE = "01390"


def hkm(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


mobpro = pd.read_parquet(DATA / "RP2022_mobpro.parquet")
communes = gpd.read_file(DATA / "communes-100m.geojson")
rank = pd.read_csv(OUT / "commune_pareto_ranking.csv")
rank["code"] = rank["code"].astype(str).str.zfill(5)
ttm = pd.read_parquet(CACHE / "ttm_expanded.parquet")

communes["dept"] = communes["code"].str[:2]
lc = communes[communes["dept"].isin(LYON_DEPTS)].copy()

# §2 OD flows by mode
m = mobpro.copy()
m["o_dept"] = m["COMMUNE"].astype(str).str[:2]
m["d_dept"] = m["DCLT"].astype(str).str[:2]
m = m[m["o_dept"].isin(LYON_DEPTS) & m["d_dept"].isin(LYON_DEPTS)]
ma = m[m["TRANS"].isin({2.0, 3.0, 4.0, 5.0, 6.0})].copy()
ma["COMMUNE"] = ma["COMMUNE"].astype(str)
ma["DCLT"] = ma["DCLT"].astype(str)
od = (ma.groupby(["COMMUNE", "DCLT", "TRANS"], as_index=False)["IPONDI"].sum()
      .rename(columns={"COMMUNE": "origin", "DCLT": "dest", "TRANS": "mode", "IPONDI": "weight"}))
od = od[od["origin"] != od["dest"]].copy()
od_mode = od.pivot_table(index=["origin", "dest"], columns="mode", values="weight", fill_value=0.0)
od_mode.columns = [f"m{int(c)}" for c in od_mode.columns]
od_mode["total"] = od_mode.sum(axis=1)
od_mode["car"] = od_mode.get("m5", 0.0) + od_mode.get("m4", 0.0)
od_mode = od_mode.reset_index()

# §7 centroids + lyon distance
ctr = lc.to_crs("EPSG:4326").geometry.centroid
lc["lon"], lc["lat"] = ctr.x, ctr.y
lc["dist_to_lyon_km"] = lc.apply(lambda r: hkm(LYON_CENTRE_LON, LYON_CENTRE_LAT, r["lon"], r["lat"]), axis=1)
lyon_zone_codes = set(lc.loc[lc["dist_to_lyon_km"] <= LYON_ZONE_KM, "code"])
name_of = dict(zip(lc["code"], lc["nom"]))

# §14 SV cluster centroid + max-free-radius
sv = lc[lc["code"] == SV_CODE]
sv_wgs = gpd.GeoSeries([sv.to_crs("EPSG:2154").geometry.union_all().centroid], crs="EPSG:2154").to_crs("EPSG:4326").iloc[0]
clon, clat = sv_wgs.x, sv_wgs.y
lc["_d_sv"] = lc.apply(lambda r: hkm(clon, clat, r["lon"], r["lat"]) if pd.notna(r["lon"]) else np.nan, axis=1)
mfr = None
for r_km in range(5, 36):
    if set(lc.loc[lc["_d_sv"] <= r_km, "code"]) & lyon_zone_codes:
        break
    mfr = r_km
local_zone = set(lc.loc[(lc["_d_sv"] <= mfr) & (~lc["code"].isin(lyon_zone_codes)), "code"])

# cluster scenario stats + SV-anchored commute relations (slide-05 numbers)
od_p1 = od_mode[od_mode["origin"].isin(local_zone) & od_mode["dest"].isin(local_zone)].copy()
cxy = dict(zip(lc["code"], zip(lc["lon"], lc["lat"])))
od_p1["dist_km"] = od_p1.apply(
    lambda r: hkm(*cxy[r["origin"]], *cxy[r["dest"]]) if r["origin"] in cxy and r["dest"] in cxy else np.nan, axis=1)
od_p1 = od_p1.merge(ttm[["origin", "dest", "car_min", "pt_min_nowait"]], on=["origin", "dest"], how="left")
rank_sv = rank[rank["code"] == SV_CODE].iloc[0]
print(f"SV cluster: {len(local_zone)} communes within {mfr} km | intra commuters/day "
      f"{od_p1['total'].sum():,.0f} (car {od_p1['car'].sum()/od_p1['total'].sum()*100:.1f}%)")
print(f"SV: flow {rank_sv['total_flow']:,.0f} | PT-acc {rank_sv['pt_accessibility_expanded']:.3f} "
      f"(~{1/rank_sv['pt_accessibility_expanded']:.1f}x slower) | car {rank_sv['car_share']*100:.1f}%")
print("\nTop SV-anchored relations (origin/dest = Saint-Vulbas):")
sv_rel = od_p1[(od_p1["origin"] == SV_CODE) | (od_p1["dest"] == SV_CODE)].sort_values("total", ascending=False).head(8)
for _, r in sv_rel.iterrows():
    o, d = name_of.get(r["origin"], r["origin"]), name_of.get(r["dest"], r["dest"])
    pt = f"{r['pt_min_nowait']:.0f}" if pd.notna(r["pt_min_nowait"]) else "no PT"
    print(f"  {o:>22} -> {d:<22} {r['total']:6.0f} | {r['dist_km']:4.1f} km | car {r['car_min']:.0f} | PT {pt}")

# ── FIGURE 1 — Pareto scatter (linear axes, Saint-Vulbas highlighted) ─────────
scope = rank[rank["pareto_front"].notna()].copy()
acc_col = "pt_accessibility_expanded"
fig, ax = plt.subplots(figsize=(7.2, 6.4))
front_palette = {1: "#d62728", 2: "#f08c2e", 3: "#f6c177"}
dom = scope[~scope["pareto_front"].isin([1, 2, 3])]
ax.scatter(dom["total_flow"], dom[acc_col], s=22, c="#cfd6da", edgecolor="white", linewidth=0.4, alpha=0.8, zorder=2, label="Dominated")
for f in [3, 2, 1]:
    sub = scope[scope["pareto_front"] == f]
    ax.scatter(sub["total_flow"], sub[acc_col], s=46, c=front_palette[f], edgecolor="white",
               linewidth=0.6, alpha=0.95, zorder=5 + (3 - f), label=f"Front {f} (n={len(sub)})")
sv_row = scope[scope["code"] == SV_CODE].iloc[0]
ax.scatter([sv_row["total_flow"]], [sv_row[acc_col]], s=230, facecolor="none", edgecolor="#111111", linewidth=2.0, zorder=20)
ax.annotate("Saint-Vulbas", (sv_row["total_flow"], sv_row[acc_col]), xytext=(10, 8),
            textcoords="offset points", fontsize=12, fontweight="bold", zorder=21)
ax.set_xlabel("Commuter flow  (inbound + outbound, per day)", fontsize=12)
ax.set_ylabel("PT accessibility   (lower = worse PT)", fontsize=12)
ax.tick_params(labelsize=10)
ax.grid(True, alpha=0.25)
ax.legend(loc="upper right", frameon=True, fontsize=10)
ax.set_ylim(0, ax.get_ylim()[1])
ax.set_xlim(0, ax.get_xlim()[1])
fig.tight_layout()
fig.savefig(OUT / "slide_pareto_scatter.png", dpi=200, bbox_inches="tight")
plt.close("all")

# ── FIGURES 2 & 3 — commute-flow maps (orient on notebook §17) ────────────────────
# One shared frame + base (basemap, all commune outlines, ranks, Lyon) used twice:
#   FIG 2 (slide 6) = intra-zone commutes; FIG 3 (outlook) = zone -> Lyon commutes.
import contextily as cx
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from shapely.geometry import box as _box

MIN_FLOW = 20                       # floor for intra OD pairs (as in §17); Lyon map has NO floor
TOP_SV = 32                         # cap on SV-touching intra arrows (the inbound fan)
TOP_OTHER = 38                      # cap on non-SV intra arrows (slide-scale legibility)
LW_MIN, LW_MAX = 0.4, 5.5           # arrow width range, linear in commuter count
INTRA_BLUE = "#1f4e79"
LYON_TEAL = "#0c7c8c"

lc_w = lc.to_crs("EPSG:3857").copy()
lc_w = lc_w.merge(rank[["code", "pareto_front"]], on="code", how="left")
cent_w = dict(zip(lc_w["code"], zip(lc_w.geometry.centroid.x, lc_w.geometry.centroid.y)))
svx, svy = cent_w[SV_CODE]
lyon_w = gpd.GeoSeries([gpd.points_from_xy([LYON_CENTRE_LON], [LYON_CENTRE_LAT], crs="EPSG:4326")[0]],
                       crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
LYON_XY = (lyon_w.x, lyon_w.y)
front_palette = {1.0: "#d62728", 2.0: "#f08c2e", 3.0: "#f6c177"}
HALO = [pe.withStroke(linewidth=2.6, foreground="white")]

# intra: all SV-touching pairs (the focus) + the largest other intra pairs (legibility).
# zone->Lyon: aggregate to ONE arrow per origin commune (sum over all Lyon-zone dests),
#   no commuter threshold -> the full fan into Lyon (Paper 2 outlook).
_intra_all = od_mode[od_mode["origin"].isin(local_zone) & od_mode["dest"].isin(local_zone)
                     & (od_mode["total"] >= MIN_FLOW)]
_sv_touch = _intra_all[(_intra_all["origin"] == SV_CODE) | (_intra_all["dest"] == SV_CODE)].nlargest(TOP_SV, "total")
_other = _intra_all[(_intra_all["origin"] != SV_CODE) & (_intra_all["dest"] != SV_CODE)].nlargest(TOP_OTHER, "total")
intra = pd.concat([_sv_touch, _other]).copy()
to_lyon = (od_mode[od_mode["origin"].isin(local_zone) & od_mode["dest"].isin(lyon_zone_codes)]
           .groupby("origin", as_index=False)["total"].sum())
print(f"drawn flows: intra {len(intra)} ({len(_sv_touch)} SV-touching + {len(_other)} other) "
      f"| zone->Lyon {len(to_lyon)} origin communes (all, no threshold)")
FIG_H = 6.5


def _frame(codes, padx=0.05, pady=0.06):
    xs = [cent_w[c][0] for c in codes if c in cent_w] + [LYON_XY[0]]
    ys = [cent_w[c][1] for c in codes if c in cent_w] + [LYON_XY[1]]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    xmin -= (xmax - xmin) * padx; xmax += (xmax - xmin) * padx
    ymin -= (ymax - ymin) * pady; ymax += (ymax - ymin) * pady
    return xmin, ymin, xmax, ymax


# tight frame for slide 6 (intra endpoints + Lyon + SV); outlook gets its own (its origins span wider)
F_INTRA = _frame(set(intra["origin"]) | set(intra["dest"]) | {SV_CODE})
F_LYON = _frame(set(to_lyon["origin"]) | {SV_CODE})
print(f"intra frame aspect {(F_INTRA[2]-F_INTRA[0])/(F_INTRA[3]-F_INTRA[1]):.2f} | "
      f"lyon frame aspect {(F_LYON[2]-F_LYON[0])/(F_LYON[3]-F_LYON[1]):.2f}")
# Ambérieu sanity: confirm the #1 flow's NE endpoint stays inside the slide-6 frame
_amb = intra.loc[intra["total"].idxmax()]
_ac = cent_w.get(_amb["origin"] if _amb["origin"] != SV_CODE else _amb["dest"])
print(f"top flow {_amb['origin']}->{_amb['dest']} ({_amb['total']:.0f}); endpoint in intra frame: "
      f"{F_INTRA[0] <= _ac[0] <= F_INTRA[2] and F_INTRA[1] <= _ac[1] <= F_INTRA[3]}")


def _new_fig(frame):
    xmin, ymin, xmax, ymax = frame
    fig, ax = plt.subplots(figsize=((xmax - xmin) / (ymax - ymin) * FIG_H, FIG_H))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
    return fig, ax


def _draw_base(ax, frame, show_ranks=True):
    xmin, ymin, xmax, ymax = frame
    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, crs="EPSG:3857", attribution_size=4)
    vis = lc_w[lc_w.geometry.intersects(_box(xmin, ymin, xmax, ymax))]
    vis.plot(ax=ax, facecolor="none", edgecolor="#b9b9b9", linewidth=0.35, zorder=2)  # all commune outlines
    if show_ranks:
        for f, c in front_palette.items():
            sub = vis[vis["pareto_front"] == f]
            if len(sub):
                sub.plot(ax=ax, facecolor=c, alpha=0.40, edgecolor=c, linewidth=0.9, zorder=3)
    lc_w[lc_w["code"] == SV_CODE].plot(ax=ax, facecolor="#8e44ad", alpha=0.62, edgecolor="#5b2c82", linewidth=1.8, zorder=5)
    ax.scatter(*LYON_XY, marker="*", s=520, c="#1a3a6b", edgecolor="white", linewidth=0.9, zorder=11)
    ax.annotate("Lyon", LYON_XY, xytext=(7, 4), textcoords="offset points",
                fontsize=12.5, fontweight="bold", color="#1a3a6b", zorder=12).set_path_effects(HALO)
    ax.annotate("Saint-Vulbas", (svx, svy), xytext=(13, 15), textcoords="offset points",
                fontsize=12, fontweight="bold", color="#4a2370", zorder=12).set_path_effects(HALO)
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_axis_off()


def _lw(flow, ref):
    return LW_MIN + (LW_MAX - LW_MIN) * (flow / ref)


# ===== FIGURE 2 — intra-zone commute network (slide 6): one blue colour, width ~ flow =====
fig, ax = _new_fig(F_INTRA)
_draw_base(ax, F_INTRA, show_ranks=True)
ref = intra["total"].max()
for _, r in intra.sort_values("total").iterrows():          # small flows first, big on top
    o, d = cent_w.get(r["origin"]), cent_w.get(r["dest"])
    if o and d:
        ax.annotate("", xy=d, xytext=o,
                    arrowprops=dict(arrowstyle="-|>", color=INTRA_BLUE, alpha=0.75, lw=_lw(r["total"], ref),
                                    connectionstyle="arc3,rad=0.08", shrinkA=2, shrinkB=4), zorder=7)
ax.legend(handles=[
    mpatches.Patch(facecolor="#8e44ad", alpha=0.62, edgecolor="#5b2c82", label="Saint-Vulbas (anchor)"),
    mpatches.Patch(facecolor=front_palette[1.0], alpha=0.40, edgecolor=front_palette[1.0], label="Rank 1 commune"),
    mpatches.Patch(facecolor=front_palette[2.0], alpha=0.40, edgecolor=front_palette[2.0], label="Rank 2 commune"),
    Line2D([0], [0], color=INTRA_BLUE, lw=2.4, marker=">", markersize=6, label="Intra-zone commute"),
], loc="upper left", fontsize=7.5, framealpha=0.93)
fig.savefig(OUT / "slide_cluster_map.png", dpi=200)
plt.close("all")

# ===== FIGURE 3 — zone -> Lyon commutes (outlook): no rank colour, one arrow per origin =====
fig, ax = _new_fig(F_LYON)
_draw_base(ax, F_LYON, show_ranks=False)
ref2 = to_lyon["total"].max() if len(to_lyon) else 1.0
for _, r in to_lyon.sort_values("total").iterrows():
    o = cent_w.get(r["origin"])
    if o:
        ax.annotate("", xy=LYON_XY, xytext=o,
                    arrowprops=dict(arrowstyle="-|>", color=LYON_TEAL, alpha=0.6, lw=_lw(r["total"], ref2),
                                    connectionstyle="arc3,rad=0.08", shrinkA=2, shrinkB=9), zorder=7)
ax.legend(handles=[
    mpatches.Patch(facecolor="#8e44ad", alpha=0.62, edgecolor="#5b2c82", label="Saint-Vulbas (anchor)"),
    Line2D([0], [0], color=LYON_TEAL, lw=2.4, marker=">", markersize=6, label="Commute to Lyon"),
], loc="upper left", fontsize=7.5, framealpha=0.93)
fig.savefig(OUT / "slide_outlook_lyon_map.png", dpi=200)
plt.close("all")

# ── FIGURE 0 — the real PT-accessibility formulation (mathtext, for slide-04) ─────
ff, fax = plt.subplots(figsize=(5.0, 3.0))
fax.axis("off")
fax.set_xlim(0, 1)
fax.set_ylim(0, 1)
FCOL = "#006b63"
fax.text(0.02, 0.88,
         r"$s_{o\rightarrow d}=\min\left(1,\ \dfrac{t_{\mathrm{car}}}{t_{\mathrm{PT}}}\right)$",
         fontsize=19, va="center", ha="left", color=FCOL)
fax.text(0.02, 0.30,
         r"$R_{c}=\dfrac{\sum_{\mathrm{in}}\mathrm{flow}\cdot s\ +\ \sum_{\mathrm{out}}\mathrm{flow}\cdot s}"
         r"{\sum_{\mathrm{in}}\mathrm{flow}\ +\ \sum_{\mathrm{out}}\mathrm{flow}}$",
         fontsize=19, va="center", ha="left", color=FCOL)
ff.savefig(OUT / "slide_formula.png", dpi=240, bbox_inches="tight", transparent=True)
plt.close("all")

print("\nslide figures written to output/ (slide_pareto_scatter.png, slide_cluster_map.png, slide_formula.png)")