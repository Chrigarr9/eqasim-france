"""Unit tests for drt_map helpers."""
import drt_map  # noqa: F401


def test_module_imports():
    """Smoke test — module imports cleanly."""
    assert hasattr(drt_map, "__doc__")


def test_top_flows_outbound_returns_sorted(tiny_communes, tiny_od):
    rows = drt_map.top_flows(tiny_od, tiny_communes, "A001", n=5, direction="out")
    assert len(rows) == 2
    assert rows[0]["partner_code"] == "B002"
    assert rows[0]["flow"] == 450
    assert rows[0]["partner_name"] == "Bville"
    assert rows[0]["partner_ll"] == [0.5, 1.5]  # [lat, lon] for Leaflet
    assert rows[1]["partner_code"] == "C003"
    assert rows[1]["flow"] == 160


def test_top_flows_inbound(tiny_communes, tiny_od):
    rows = drt_map.top_flows(tiny_od, tiny_communes, "A001", n=5, direction="in")
    codes = [r["partner_code"] for r in rows]
    assert codes == ["B002", "C003"]
    assert rows[0]["flow"] == 400


def test_top_flows_truncates_to_n(tiny_communes, tiny_od):
    rows = drt_map.top_flows(tiny_od, tiny_communes, "A001", n=1, direction="out")
    assert len(rows) == 1
    assert rows[0]["partner_code"] == "B002"


def test_top_flows_missing_commune_returns_empty(tiny_communes, tiny_od):
    rows = drt_map.top_flows(tiny_od, tiny_communes, "Z999", n=5, direction="out")
    assert rows == []


def test_top_flows_invalid_direction_raises(tiny_communes, tiny_od):
    import pytest
    with pytest.raises(ValueError, match="direction"):
        drt_map.top_flows(tiny_od, tiny_communes, "A001", n=5, direction="sideways")


def test_build_hist_svg_returns_svg_string():
    import numpy as np
    dists = np.array([5.0, 12.0, 18.0, 22.0, 45.0])
    weights = np.array([100, 200, 300, 150, 50])
    svg = drt_map.build_hist_svg(dists, weights, width=320, height=120)
    assert svg.startswith("<svg")
    assert 'width="320"' in svg
    assert 'height="120"' in svg
    assert svg.rstrip().endswith("</svg>")


def test_build_hist_svg_contains_bars():
    import numpy as np
    dists = np.array([12.0, 18.0])
    weights = np.array([100, 200])
    svg = drt_map.build_hist_svg(dists, weights, width=320, height=120)
    # At least one <rect> for a bar
    assert svg.count("<rect") >= 2


def test_build_hist_svg_shades_drt_sweetspot():
    import numpy as np
    dists = np.array([12.0])
    weights = np.array([100])
    svg = drt_map.build_hist_svg(
        dists, weights, width=320, height=120, drt_min=10, drt_max=25,
    )
    # The sweet-spot rect should have a marker class we assert on
    assert 'class="drt-band"' in svg


def test_build_hist_svg_handles_empty_input():
    import numpy as np
    svg = drt_map.build_hist_svg(np.array([]), np.array([]), width=320, height=120)
    assert svg.startswith("<svg")
    # No bars, but the DRT band is still drawn
    assert 'class="drt-band"' in svg


def test_build_hist_svg_bar_heights_proportional_to_weights():
    """Bar heights should scale linearly with weights (1:2 weights → 1:2 heights)."""
    import numpy as np
    import re
    dists = np.array([12.0, 32.0])
    weights = np.array([100.0, 200.0])  # 1:2 ratio
    svg = drt_map.build_hist_svg(dists, weights, width=320, height=120)

    # Extract bar heights (bars use fill="#3498db" — DRT band uses a different fill)
    heights = [float(h) for h in re.findall(r'<rect[^>]*height="([\d.]+)"[^>]*fill="#3498db"', svg)]
    assert len(heights) == 2, f"expected 2 bars, got {len(heights)}: {heights}"
    # Taller bar (weight 200) ≈ 2× shorter (weight 100)
    ratio = max(heights) / min(heights)
    assert 1.95 <= ratio <= 2.05, f"bar height ratio {ratio!r} not near 2.0"


def test_build_modes_svg_returns_svg_string():
    shares = {"walk": 0.05, "bike": 0.03, "motorbike": 0.02, "car": 0.80, "pt": 0.10}
    svg = drt_map.build_modes_svg(shares, width=320, height=120)
    assert svg.startswith("<svg")
    assert 'width="320"' in svg
    assert svg.rstrip().endswith("</svg>")


def test_build_modes_svg_contains_five_bars():
    shares = {"walk": 0.2, "bike": 0.2, "motorbike": 0.2, "car": 0.2, "pt": 0.2}
    svg = drt_map.build_modes_svg(shares, width=320, height=120)
    assert svg.count("<rect") == 5


def test_build_modes_svg_labels_percent():
    shares = {"walk": 0.0, "bike": 0.0, "motorbike": 0.0, "car": 1.0, "pt": 0.0}
    svg = drt_map.build_modes_svg(shares, width=320, height=120)
    assert "100%" in svg


def test_build_modes_svg_handles_zero_total():
    shares = {"walk": 0.0, "bike": 0.0, "motorbike": 0.0, "car": 0.0, "pt": 0.0}
    svg = drt_map.build_modes_svg(shares, width=320, height=120)
    # No crash; five zero bars still rendered
    assert svg.count("<rect") == 5


def test_build_modes_svg_bar_heights_proportional_to_shares():
    """A share of 0.5 should produce a bar that is half the height of a share of 1.0."""
    import re
    shares_half = {"walk": 0.0, "bike": 0.0, "motorbike": 0.0, "car": 0.5, "pt": 0.0}
    shares_full = {"walk": 0.0, "bike": 0.0, "motorbike": 0.0, "car": 1.0, "pt": 0.0}
    svg_half = drt_map.build_modes_svg(shares_half, width=320, height=120)
    svg_full = drt_map.build_modes_svg(shares_full, width=320, height=120)

    # Car bar uses fill="#e74c3c"
    heights_half = [float(h) for h in re.findall(r'<rect[^>]*height="([\d.]+)"[^>]*fill="#e74c3c"', svg_half)]
    heights_full = [float(h) for h in re.findall(r'<rect[^>]*height="([\d.]+)"[^>]*fill="#e74c3c"', svg_full)]
    assert len(heights_half) == 1 and len(heights_full) == 1
    ratio = heights_full[0] / heights_half[0]
    assert 1.95 <= ratio <= 2.05, f"1.0/0.5 should give ~2× height, got {ratio!r}"


def test_build_popup_html_endpoint_includes_pt_rows(tiny_communes):
    row = tiny_communes[tiny_communes["code"] == "B002"].iloc[0]
    html = drt_map.build_popup_html(
        row,
        out_flows=[{"partner_code": "A001", "partner_name": "Aville", "flow": 400, "partner_ll": [0.5, 0.5]}],
        in_flows=[],
        hist_svg="<svg></svg>",
        modes_svg="<svg></svg>",
    )
    assert "Bville" in html
    assert "B002" in html
    assert "PT accessibility" in html
    assert "0.250" in html  # pt_accessibility_expanded formatted
    assert "Connectivity" in html
    assert "Aville" in html  # top outbound


def test_build_popup_html_non_endpoint_omits_pt_rows(tiny_communes):
    row = tiny_communes[tiny_communes["code"] == "C003"].iloc[0]
    html = drt_map.build_popup_html(
        row,
        out_flows=[],
        in_flows=[],
        hist_svg="<svg></svg>",
        modes_svg="<svg></svg>",
    )
    assert "PT accessibility" not in html
    assert "Connectivity" not in html
    assert "Cville" in html  # still shows the commune
    assert "Total commute flow" in html  # other rows present


def test_build_popup_html_embeds_svgs(tiny_communes):
    row = tiny_communes[tiny_communes["code"] == "A001"].iloc[0]
    html = drt_map.build_popup_html(
        row, out_flows=[], in_flows=[],
        hist_svg="<svg id='HIST_MARK'></svg>",
        modes_svg="<svg id='MODES_MARK'></svg>",
    )
    assert "HIST_MARK" in html
    assert "MODES_MARK" in html


def test_build_popup_html_empty_flow_lists_omit_sections(tiny_communes):
    row = tiny_communes[tiny_communes["code"] == "A001"].iloc[0]
    html = drt_map.build_popup_html(
        row, out_flows=[], in_flows=[],
        hist_svg="<svg></svg>", modes_svg="<svg></svg>",
    )
    assert "Top outbound" not in html
    assert "Top inbound" not in html


def test_compute_expanded_endpoints_radius(tiny_communes):
    endpoints = drt_map.compute_expanded_endpoints(
        tiny_communes, radius_km=60.0, lyon_arrondissements=set(),
    )
    # A001 (10 km), B002 (30 km), C003 (55 km) — but NOT D004 (70 km)
    assert endpoints == {"A001", "B002", "C003"}


def test_compute_expanded_endpoints_includes_lyon_outside_radius(tiny_communes):
    endpoints = drt_map.compute_expanded_endpoints(
        tiny_communes, radius_km=60.0, lyon_arrondissements={"D004"},
    )
    assert "D004" in endpoints  # D004 is 70 km but it's in the Lyon list


def test_compute_expanded_endpoints_empty_on_tiny_radius(tiny_communes):
    endpoints = drt_map.compute_expanded_endpoints(
        tiny_communes, radius_km=5.0, lyon_arrondissements=set(),
    )
    assert endpoints == set()


def test_build_flow_data_json_shape(tiny_communes, tiny_od):
    data = drt_map.build_flow_data_json(tiny_communes, tiny_od, top_n=5)
    assert set(data.keys()) == {"A001", "B002", "C003", "D004"}
    assert "center" in data["A001"]
    assert "out" in data["A001"]
    assert "in" in data["A001"]


def test_build_flow_data_json_center_is_lat_lon(tiny_communes, tiny_od):
    data = drt_map.build_flow_data_json(tiny_communes, tiny_od, top_n=5)
    assert data["A001"]["center"] == [0.5, 0.5]  # [lat, lon]


def test_build_flow_data_json_flows_truncated_to_n(tiny_communes, tiny_od):
    data = drt_map.build_flow_data_json(tiny_communes, tiny_od, top_n=1)
    assert len(data["A001"]["out"]) == 1
    assert data["A001"]["out"][0]["partner_code"] == "B002"


def test_build_map_js_contains_map_name():
    js = drt_map.build_map_js(map_name="map_abc123", flow_data={})
    assert "map_abc123" in js
    assert "popupopen" in js
    assert "drawFlows" in js
    assert "flowsLayer" in js


def test_build_map_js_embeds_flow_data_json():
    data = {"X1": {"center": [45.0, 4.8], "out": [], "in": []}}
    js = drt_map.build_map_js(map_name="map_x", flow_data=data)
    assert '"X1"' in js
    assert "45.0" in js


def test_build_map_js_uses_safe_dom_for_button():
    # Avoid innerHTML — use textContent / appendChild.
    js = drt_map.build_map_js(map_name="map_x", flow_data={})
    assert "innerHTML" not in js
    assert "textContent" in js


def test_build_map_returns_folium_map(tiny_communes, tiny_od):
    import folium
    m = drt_map.build_map(
        tiny_communes, tiny_od, rail_gdf=None, shortlist_codes=set(),
    )
    assert isinstance(m, folium.Map)


def test_build_map_rendered_html_contains_js_and_commune(tiny_communes, tiny_od):
    m = drt_map.build_map(
        tiny_communes, tiny_od, rail_gdf=None, shortlist_codes={"B002"},
    )
    html = m.get_root().render()
    # Custom JS present
    assert "drawFlows" in html
    assert "flowsLayer" in html
    # At least one commune name and code appear somewhere (in popup HTML or GeoJSON props)
    assert "Bville" in html
    assert "B002" in html
    # Leaflet-polylinedecorator CDN loaded
    assert "leaflet-polylinedecorator" in html


def test_build_map_writes_html_to_path(tiny_communes, tiny_od, tmp_path):
    out = tmp_path / "map.html"
    drt_map.build_map(
        tiny_communes, tiny_od, rail_gdf=None, shortlist_codes=set(),
        output_path=out,
    )
    assert out.exists()
    content = out.read_text()
    assert "drawFlows" in content


def test_build_map_js_defers_to_window_load():
    """Custom JS must run on window 'load' so the folium map var + leaflet + CDN
    scripts are all ready. Otherwise `map` and `L.polylineDecorator` may be
    undefined at run time."""
    js = drt_map.build_map_js(map_name="map_x", flow_data={})
    assert "window.addEventListener('load'" in js


def test_build_map_loads_polylinedecorator_after_leaflet(tiny_communes, tiny_od):
    """The polylinedecorator CDN must appear AFTER folium's leaflet.js import
    in document order so `L` is defined when the decorator script runs."""
    m = drt_map.build_map(
        tiny_communes, tiny_od, rail_gdf=None, shortlist_codes=set(),
    )
    html = m.get_root().render()
    leaflet_pos = html.find("leaflet@1.9.3/dist/leaflet.js")
    decorator_pos = html.find("leaflet-polylinedecorator")
    assert leaflet_pos != -1, "folium's leaflet.js not found in HTML"
    assert decorator_pos != -1, "polylinedecorator CDN not found in HTML"
    assert leaflet_pos < decorator_pos, (
        f"leaflet.js must load before polylinedecorator "
        f"(leaflet at {leaflet_pos}, decorator at {decorator_pos})"
    )


def test_build_filter_panel_html_contains_three_ranges():
    """Panel must render min + max slider per filter key (dist, flow, area)."""
    stats = {"dist": (0.0, 60.0), "flow": (0.0, 5000.0), "area": (0.0, 120.0)}
    html = drt_map.build_filter_panel_html(stats)
    for key in ("dist", "flow", "area"):
        assert f'id="drt-filter-{key}-min"' in html
        assert f'id="drt-filter-{key}-max"' in html
        assert f'id="drt-filter-{key}-val"' in html
    # Bounds are applied to the range inputs
    assert 'min="0.0"' in html
    assert 'max="60.0"' in html


def test_build_filter_js_references_layer_and_fields():
    js = drt_map.build_filter_js(layer_name="geo_json_xyz")
    assert "geo_json_xyz" in js
    # The three fields the panel binds against
    assert "dist_to_lyon_km" in js
    assert "total_flow" in js
    assert "area_km2" in js
    # Runs after load (same invariant as build_map_js)
    assert "window.addEventListener('load'" in js


def test_build_map_features_expose_filter_properties(tiny_communes, tiny_od):
    """Each GeoJson feature must expose dist/flow/area so the JS filter can
    see them. If a property is missing, the filter excludes the commune
    (null < anything is false)."""
    m = drt_map.build_map(
        tiny_communes, tiny_od, rail_gdf=None, shortlist_codes=set(),
    )
    html = m.get_root().render()
    # Properties appear in the GeoJson payload
    assert '"dist_to_lyon_km":' in html
    assert '"total_flow":' in html
    assert '"area_km2":' in html
    # Filter panel and filter JS both rendered
    assert 'id="drt-filter-panel"' in html
    assert 'drt-filter-dist-min' in html


def test_style_function_opacity_scales_with_flow():
    """Bivariate choropleth: a high-flow feature should be more opaque than a
    low-flow feature with identical pt_accessibility."""
    import drt_map as dm
    import math
    # Colormap doesn't matter here; style function only uses its fillColor.
    dummy_cmap = lambda v: "#ff0000"
    style = dm._style_function_factory(dummy_cmap, max_log_flow=math.log1p(10000))
    low = style({"properties": {"pt_accessibility_expanded": 0.2, "total_flow": 50}})
    high = style({"properties": {"pt_accessibility_expanded": 0.2, "total_flow": 8000}})
    assert high["fillOpacity"] > low["fillOpacity"], (
        f"high-flow opacity {high['fillOpacity']} must exceed "
        f"low-flow opacity {low['fillOpacity']}"
    )
    # Opacity stays in [0.15, 0.9] floor/ceiling bounds
    for s in (low, high):
        assert 0.15 <= s["fillOpacity"] <= 0.9


def test_style_function_handles_missing_flow_or_pt():
    import drt_map as dm
    dummy_cmap = lambda v: "#ff0000"
    style = dm._style_function_factory(dummy_cmap, max_log_flow=10.0)
    # No PT score (non-endpoint) + no flow → grey, min opacity
    s_grey = style({"properties": {"pt_accessibility_expanded": None, "total_flow": None}})
    assert s_grey["fillColor"] == "#d9d9d9"
    assert s_grey["fillOpacity"] > 0
    # PT score present, flow missing → floor opacity, colormap colour
    s_nofow = style({"properties": {"pt_accessibility_expanded": 0.3, "total_flow": None}})
    assert s_nofow["fillColor"] == "#ff0000"
    assert s_nofow["fillOpacity"] == 0.15


def test_build_filter_panel_includes_drt_opportunity_slider_when_provided():
    """When drt_opportunity_km stats are supplied, the panel renders a 4th slider."""
    stats = {
        "dist": (0.0, 60.0),
        "flow": (0.0, 5000.0),
        "area": (0.0, 120.0),
        "drt": (0.0, 100000.0),
    }
    html = drt_map.build_filter_panel_html(stats)
    assert 'id="drt-filter-drt-min"' in html
    assert 'id="drt-filter-drt-max"' in html


def test_build_filter_panel_skips_keys_not_in_stats():
    """Legacy frames (no drt_opportunity_km column) should still render 3 sliders."""
    stats = {"dist": (0, 60), "flow": (0, 5000), "area": (0, 120)}
    html = drt_map.build_filter_panel_html(stats)
    assert 'id="drt-filter-drt-min"' not in html  # no 4th slider
    assert 'id="drt-filter-dist-min"' in html  # others still present


def test_build_filter_panel_positioned_bottom_left():
    """Filter panel must sit in the bottom-left so it doesn't cover the top-left
    LayerControl or the top-right Clear-flows button / colorbar."""
    html = drt_map.build_filter_panel_html({"dist": (0, 60), "flow": (0, 5000), "area": (0, 120)})
    assert "bottom:" in html
    assert "left:" in html
    assert "top:10px" not in html  # was the old position
