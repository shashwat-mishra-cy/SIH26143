"""Test suite for HDR Mask to Geometry conversion module (hdr_geometry.py).

Validates vector polygon generation, MultiPolygon handling for disconnected regions,
empty mask behavior, and geographic coordinate transformation.
"""

from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shapely.geometry import MultiPolygon, Polygon
from drift.simulation.hdr_geometry import (
    hdr_mask_to_geometry,
    project_hdr_geometry_to_latlon,
)


def test_hdr_geometry() -> None:
    # Set up test metric grid (-1000m to 1000m, 21x21 grid)
    x_lin = np.linspace(-1000.0, 1000.0, 21)
    y_lin = np.linspace(-1000.0, 1000.0, 21)
    grid_x, grid_y = np.meshgrid(x_lin, y_lin)

    # ---------------------------------------------------------
    # 1. Simple connected rectangular mask
    # ---------------------------------------------------------
    mask_rect = (grid_x >= -300.0) & (grid_x <= 300.0) & (grid_y >= -300.0) & (grid_y <= 300.0)
    geom_rect = hdr_mask_to_geometry(grid_x, grid_y, mask_rect)

    assert isinstance(geom_rect, Polygon), f"Expected Polygon, got {type(geom_rect)}"
    assert geom_rect.is_valid, "Rectangular polygon geometry is invalid"
    assert not geom_rect.is_empty, "Rectangular polygon is unexpectedly empty"

    # ---------------------------------------------------------
    # 2. Two disconnected selected regions
    # ---------------------------------------------------------
    mask_disc_1 = (grid_x >= -800.0) & (grid_x <= -400.0) & (grid_y >= -800.0) & (grid_y <= -400.0)
    mask_disc_2 = (grid_x >= 400.0) & (grid_x <= 800.0) & (grid_y >= 400.0) & (grid_y <= 800.0)
    mask_disconnected = mask_disc_1 | mask_disc_2

    geom_disc = hdr_mask_to_geometry(grid_x, grid_y, mask_disconnected)

    assert isinstance(geom_disc, MultiPolygon), f"Expected MultiPolygon, got {type(geom_disc)}"
    assert geom_disc.is_valid, "Disconnected MultiPolygon geometry is invalid"
    num_components = len(geom_disc.geoms)
    assert num_components == 2, f"Expected 2 disconnected components, got {num_components}"

    # ---------------------------------------------------------
    # 3. Irregular mask (L-shape)
    # ---------------------------------------------------------
    mask_l_1 = (grid_x >= -500.0) & (grid_x <= 500.0) & (grid_y >= -500.0) & (grid_y <= -100.0)
    mask_l_2 = (grid_x >= -500.0) & (grid_x <= -100.0) & (grid_y >= -100.0) & (grid_y <= 500.0)
    mask_irregular = mask_l_1 | mask_l_2

    geom_irregular = hdr_mask_to_geometry(grid_x, grid_y, mask_irregular)

    assert geom_irregular.is_valid, "Irregular polygon geometry is invalid"
    assert not geom_irregular.is_empty, "Irregular polygon is unexpectedly empty"

    # ---------------------------------------------------------
    # 4. Empty mask behavior
    # ---------------------------------------------------------
    mask_empty = np.zeros_like(grid_x, dtype=bool)
    geom_empty = hdr_mask_to_geometry(grid_x, grid_y, mask_empty)

    assert geom_empty.is_empty, "Empty mask should return an empty Shapely geometry"
    assert isinstance(geom_empty, Polygon), f"Empty mask expected Polygon, got {type(geom_empty)}"

    # ---------------------------------------------------------
    # 5. Geographic projection transformation helper test
    # ---------------------------------------------------------
    ref_lon, ref_lat = 72.5, 18.0
    geo_geom = project_hdr_geometry_to_latlon(geom_rect, ref_lon, ref_lat)

    assert geo_geom.is_valid, "Geographic projected polygon geometry is invalid"
    assert not geo_geom.is_empty, "Geographic projected polygon is unexpectedly empty"
    min_lon, min_lat, max_lon, max_lat = geo_geom.bounds

    # Check bounds map correctly around lon 72.5, lat 18.0
    assert 72.45 < min_lon < 72.5, f"Unreasonable min_lon: {min_lon}"
    assert 72.5 < max_lon < 72.55, f"Unreasonable max_lon: {max_lon}"
    assert 17.95 < min_lat < 18.0, f"Unreasonable min_lat: {min_lat}"
    assert 18.0 < max_lat < 18.05, f"Unreasonable max_lat: {max_lat}"

    # ---------------------------------------------------------
    # 6. Error handling tests
    # ---------------------------------------------------------
    # Non-boolean mask
    bad_dtype_mask = np.ones_like(grid_x, dtype=float)
    non_bool_error = False
    try:
        hdr_mask_to_geometry(grid_x, grid_y, bad_dtype_mask)
    except ValueError:
        non_bool_error = True
    assert non_bool_error, "Failed to raise ValueError for non-boolean mask"

    # Mismatched shape
    mismatched_mask = mask_rect[:-1, :]
    mismatch_error = False
    try:
        hdr_mask_to_geometry(grid_x, grid_y, mismatched_mask)
    except ValueError:
        mismatch_error = True
    assert mismatch_error, "Failed to raise ValueError for mismatched mask shape"

    # ---------------------------------------------------------
    # Summary Output
    # ---------------------------------------------------------
    print("HDR geometry conversion tests: PASSED")
    print(f"- Single connected region -> Produced geometry: {type(geom_rect).__name__} (Valid: {geom_rect.is_valid})")
    print(f"- Disconnected regions -> Produced geometry: {type(geom_disc).__name__} (Components: {num_components}, Valid: {geom_disc.is_valid})")
    print(f"- Irregular L-shape -> Produced geometry: {type(geom_irregular).__name__} (Valid: {geom_irregular.is_valid})")
    print(f"- Empty mask -> Produced geometry: {type(geom_empty).__name__} (Empty: {geom_empty.is_empty})")
    print(f"- Geographic projected geometry bounds: lon [{min_lon:.6f}, {max_lon:.6f}], lat [{min_lat:.6f}, {max_lat:.6f}]")


if __name__ == "__main__":
    test_hdr_geometry()
