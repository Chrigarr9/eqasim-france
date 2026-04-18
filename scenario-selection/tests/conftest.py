import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon


@pytest.fixture
def tiny_communes():
    """Four synthetic communes laid out on a small grid."""
    rows = [
        {"code": "A001", "nom": "Aville", "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
         "lon": 0.5, "lat": 0.5, "dist_to_lyon_km": 10.0, "dist_to_rail_km": 2.0,
         "daytime_trips_per_hour": 5.0, "total_flow": 1200.0, "car_share": 0.8,
         "lyon_share": 0.4, "pt_accessibility_expanded": 0.9, "connectivity_expanded": 0.5},
        {"code": "B002", "nom": "Bville", "geometry": Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
         "lon": 1.5, "lat": 0.5, "dist_to_lyon_km": 30.0, "dist_to_rail_km": 8.0,
         "daytime_trips_per_hour": 0.5, "total_flow": 3000.0, "car_share": 0.95,
         "lyon_share": 0.15, "pt_accessibility_expanded": 0.25, "connectivity_expanded": 0.05},
        {"code": "C003", "nom": "Cville", "geometry": Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
         "lon": 0.5, "lat": 1.5, "dist_to_lyon_km": 55.0, "dist_to_rail_km": 15.0,
         "daytime_trips_per_hour": 0.0, "total_flow": 500.0, "car_share": 0.9,
         "lyon_share": 0.05, "pt_accessibility_expanded": None, "connectivity_expanded": None},
        {"code": "D004", "nom": "Dville", "geometry": Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
         "lon": 1.5, "lat": 1.5, "dist_to_lyon_km": 70.0, "dist_to_rail_km": 20.0,
         "daytime_trips_per_hour": 0.0, "total_flow": 100.0, "car_share": 0.85,
         "lyon_share": 0.02, "pt_accessibility_expanded": None, "connectivity_expanded": None},
    ]
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


@pytest.fixture
def tiny_od():
    """Synthetic OD matrix matching tiny_communes."""
    return pd.DataFrame([
        {"origin": "A001", "dest": "B002", "m2": 0,  "m3": 10, "m4": 0,  "m5": 400, "m6": 40, "total": 450, "car": 400, "car_share": 0.89},
        {"origin": "A001", "dest": "C003", "m2": 0,  "m3": 0,  "m4": 0,  "m5": 150, "m6": 10, "total": 160, "car": 150, "car_share": 0.94},
        {"origin": "B002", "dest": "A001", "m2": 0,  "m3": 5,  "m4": 0,  "m5": 380, "m6": 15, "total": 400, "car": 380, "car_share": 0.95},
        {"origin": "B002", "dest": "C003", "m2": 0,  "m3": 0,  "m4": 10, "m5": 290, "m6": 0,  "total": 300, "car": 300, "car_share": 1.00},
        {"origin": "C003", "dest": "A001", "m2": 20, "m3": 0,  "m4": 0,  "m5": 180, "m6": 0,  "total": 200, "car": 180, "car_share": 0.90},
    ])
