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
