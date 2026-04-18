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
