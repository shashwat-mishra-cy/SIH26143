"""Test suite for geometry sampling (Polygon & MultiPolygon) in backward drift simulation.

Validates particle seeding inside simple polygons, irregular polygons, and disconnected MultiPolygons.
"""

from pathlib import Path
import sys

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shapely.geometry import Point, Polygon, MultiPolygon
from drift.simulation.backward import sample_points_in_geometry


def test_geometry_sampling() -> None:
    # ---------------------------------------------------------
    # CASE A: Simple rectangular Polygon
    # ---------------------------------------------------------
    rect_coords = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.52, 18.01],
        [72.48, 18.01],
    ]
    poly_a = Polygon(rect_coords)

    lons_a, lats_a = sample_points_in_geometry(poly_a, number_of_points=500, seed=42)

    assert len(lons_a) == 500, f"Expected 500 points, got {len(lons_a)}"
    assert len(lats_a) == 500, f"Expected 500 points, got {len(lats_a)}"

    all_inside_a = all(
        poly_a.contains(Point(lon, lat)) for lon, lat in zip(lons_a, lats_a)
    )
    assert all_inside_a, "Not all points were inside the simple rectangular polygon!"

    print("Polygon:")
    print(f"  points generated: {len(lons_a)}")
    print(f"  all inside: {all_inside_a}\n")

    # ---------------------------------------------------------
    # CASE B: Irregular Polygon (6 vertices, concave L-shape)
    # ---------------------------------------------------------
    irregular_coords = [
        [72.45, 17.95],
        [72.55, 17.95],
        [72.55, 18.00],
        [72.50, 18.00],
        [72.50, 18.05],
        [72.45, 18.05],
    ]
    poly_b = Polygon(irregular_coords)
    assert len(irregular_coords) >= 6, "Irregular polygon must have at least 6 vertices"
    assert poly_b.is_valid, "Irregular polygon geometry is invalid"

    lons_b, lats_b = sample_points_in_geometry(poly_b, number_of_points=500, seed=42)

    assert len(lons_b) == 500, f"Expected 500 points, got {len(lons_b)}"
    assert len(lats_b) == 500, f"Expected 500 points, got {len(lats_b)}"

    all_inside_b = all(
        poly_b.contains(Point(lon, lat)) for lon, lat in zip(lons_b, lats_b)
    )
    assert all_inside_b, "Not all points were inside the irregular polygon!"

    print("Irregular Polygon:")
    print(f"  points generated: {len(lons_b)}")
    print(f"  all inside: {all_inside_b}\n")

    # ---------------------------------------------------------
    # CASE C: MultiPolygon (Two disconnected synthetic polygons)
    # ---------------------------------------------------------
    comp_1 = Polygon([
        [72.40, 17.90],
        [72.44, 17.90],
        [72.44, 17.94],
        [72.40, 17.94],
    ])
    comp_2 = Polygon([
        [72.56, 18.06],
        [72.60, 18.06],
        [72.60, 18.10],
        [72.56, 18.10],
    ])

    multi_poly = MultiPolygon([comp_1, comp_2])
    assert multi_poly.is_valid, "MultiPolygon geometry is invalid"

    lons_c, lats_c = sample_points_in_geometry(multi_poly, number_of_points=500, seed=42)

    assert len(lons_c) == 500, f"Expected 500 points, got {len(lons_c)}"
    assert len(lats_c) == 500, f"Expected 500 points, got {len(lats_c)}"

    all_inside_c = all(
        multi_poly.contains(Point(lon, lat)) for lon, lat in zip(lons_c, lats_c)
    )
    assert all_inside_c, "Not all points were inside the MultiPolygon!"

    comp_a_points = sum(
        1 for lon, lat in zip(lons_c, lats_c) if comp_1.contains(Point(lon, lat))
    )
    comp_b_points = sum(
        1 for lon, lat in zip(lons_c, lats_c) if comp_2.contains(Point(lon, lat))
    )

    assert comp_a_points > 0, "Component A received 0 sampled points!"
    assert comp_b_points > 0, "Component B received 0 sampled points!"
    assert comp_a_points + comp_b_points == 500, (
        f"Sum of component points ({comp_a_points} + {comp_b_points}) != 500"
    )

    print("MultiPolygon:")
    print(f"  points generated: {len(lons_c)}")
    print(f"  all inside: {all_inside_c}")
    print(f"  component A points: {comp_a_points}")
    print(f"  component B points: {comp_b_points}")


if __name__ == "__main__":
    test_geometry_sampling()
