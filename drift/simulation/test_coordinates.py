"""Test suite for local metric coordinate projection module (coordinates.py).

Validates forward and inverse projections between WGS84 decimal degrees and metric X/Y coordinates.
"""

from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.coordinates import (
    project_latlon_to_xy,
    project_xy_to_latlon,
    PYPROJ_AVAILABLE,
)


def test_coordinates() -> None:
    assert PYPROJ_AVAILABLE, "pyproj package is not installed."

    ref_lon = 72.5
    ref_lat = 18.0

    # ---------------------------------------------------------
    # CASE A: Reference Point maps to (x=0, y=0)
    # ---------------------------------------------------------
    x0, y0 = project_latlon_to_xy(ref_lon, ref_lat, ref_lon, ref_lat)
    assert abs(x0) < 1e-3, f"Reference longitude should map to x ≈ 0, got {x0}"
    assert abs(y0) < 1e-3, f"Reference latitude should map to y ≈ 0, got {y0}"

    # ---------------------------------------------------------
    # CASE B: Project nearby coordinates and verify metric values
    # ---------------------------------------------------------
    test_lons = [72.48, 72.50, 72.52]
    test_lats = [17.99, 18.00, 18.01]

    xs, ys = project_latlon_to_xy(test_lons, test_lats, ref_lon, ref_lat)

    # (72.48, 17.99) is SW of reference -> negative X and negative Y
    assert xs[0] < 0, f"Expected negative X for lon 72.48, got {xs[0]}"
    assert ys[0] < 0, f"Expected negative Y for lat 17.99, got {ys[0]}"

    # (72.50, 18.00) is reference point -> X ≈ 0, Y ≈ 0
    assert abs(xs[1]) < 1e-3, f"Expected X ≈ 0 for lon 72.50, got {xs[1]}"
    assert abs(ys[1]) < 1e-3, f"Expected Y ≈ 0 for lat 18.00, got {ys[1]}"

    # (72.52, 18.01) is NE of reference -> positive X and positive Y
    assert xs[2] > 0, f"Expected positive X for lon 72.52, got {xs[2]}"
    assert ys[2] > 0, f"Expected positive Y for lat 18.01, got {ys[2]}"

    # Check order-of-magnitude scale in meters (~2118m for 0.02 deg longitude at 18 deg N)
    assert 2000 < abs(xs[0]) < 2300, f"Unreasonable X scale in meters: {xs[0]}"
    assert 1000 < abs(ys[0]) < 1200, f"Unreasonable Y scale in meters: {ys[0]}"

    # ---------------------------------------------------------
    # CASE C: Round-trip test (Lat/Lon -> X/Y -> Lat/Lon)
    # ---------------------------------------------------------
    orig_lons = np.array([72.48, 72.49, 72.50, 72.51, 72.52])
    orig_lats = np.array([17.99, 17.995, 18.00, 18.005, 18.01])

    proj_x, proj_y = project_latlon_to_xy(orig_lons, orig_lats, ref_lon, ref_lat)
    rec_lons, rec_lats = project_xy_to_latlon(proj_x, proj_y, ref_lon, ref_lat)

    lon_error = np.max(np.abs(orig_lons - rec_lons))
    lat_error = np.max(np.abs(orig_lats - rec_lats))
    max_roundtrip_error = float(max(lon_error, lat_error))

    assert max_roundtrip_error < 1e-6, f"Round-trip error too large: {max_roundtrip_error}"

    # ---------------------------------------------------------
    # CASE D: Multiple coordinates & preservation of count/order
    # ---------------------------------------------------------
    multi_lons = np.random.uniform(72.40, 72.60, size=50)
    multi_lats = np.random.uniform(17.90, 18.10, size=50)

    m_x, m_y = project_latlon_to_xy(multi_lons, multi_lats, ref_lon, ref_lat)

    assert len(m_x) == 50, f"Expected 50 output X values, got {len(m_x)}"
    assert len(m_y) == 50, f"Expected 50 output Y values, got {len(m_y)}"

    r_lons, r_lats = project_xy_to_latlon(m_x, m_y, ref_lon, ref_lat)

    assert np.allclose(multi_lons, r_lons, atol=1e-6), "Array order/values changed in round-trip!"
    assert np.allclose(multi_lats, r_lats, atol=1e-6), "Array order/values changed in round-trip!"

    # ---------------------------------------------------------
    # SUMMARY OUTPUT
    # ---------------------------------------------------------
    print("Coordinate projection tests: PASSED")
    print(f"- Projection method used: Azimuthal Equidistant (AEQD) via pyproj")
    print(f"- Reference point: (lon={ref_lon}°E, lat={ref_lat}°N)")
    print(f"- Example X/Y result: (lon=72.48, lat=17.99) -> X={xs[0]:.2f}m, Y={ys[0]:.2f}m")
    print(f"- Maximum round-trip error: {max_roundtrip_error:.2e} degrees")


if __name__ == "__main__":
    test_coordinates()
