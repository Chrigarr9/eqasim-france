"""Unit tests for drt_map helpers."""
import drt_map  # noqa: F401


def test_module_imports():
    """Smoke test — module imports cleanly."""
    assert hasattr(drt_map, "__doc__")
