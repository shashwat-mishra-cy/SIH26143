"""Unit test suite for source support temporal diagnostics.

Validates chronological sorting, area change, relative area expansion,
centroid displacement, component counts, and safe skipped timestamp handling.
"""

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.source_support_diagnostics import (
    calculate_temporal_diagnostics,
)


def test_source_support_diagnostics() -> None:
    raw_results = [
        {
            "timestamp": "2025-01-01T12:00:00Z",
            "status": "success",
            "particle_count": 500,
            "hdr_50_area_m2": 6000000.0,
            "hdr_90_area_m2": 14000000.0,
            "kde_max_density": 1.0e-7,
            "hdr_50_centroid_lat": 18.00,
            "hdr_50_centroid_lon": 72.50,
            "hdr_90_centroid_lat": 18.00,
            "hdr_90_centroid_lon": 72.50,
            "hdr_50_component_count": 1,
            "hdr_90_component_count": 2,
        },
        {
            "timestamp": "2025-01-01T10:00:00Z",
            "status": "skipped_insufficient_particles",
            "particle_count": 1,
        },
        {
            "timestamp": "2025-01-01T08:00:00Z",
            "status": "success",
            "particle_count": 500,
            "hdr_50_area_m2": 5000000.0,
            "hdr_90_area_m2": 12000000.0,
            "kde_max_density": 1.2e-7,
            "hdr_50_centroid_lat": 17.98,
            "hdr_50_centroid_lon": 72.48,
            "hdr_90_centroid_lat": 17.98,
            "hdr_90_centroid_lon": 72.48,
            "hdr_50_component_count": 2,
            "hdr_90_component_count": 3,
        },
        {
            "timestamp": "2025-01-01T09:00:00Z",
            "status": "success",
            "particle_count": 500,
            "hdr_50_area_m2": 5500000.0,
            "hdr_90_area_m2": 13000000.0,
            "kde_max_density": 1.1e-7,
            "hdr_50_centroid_lat": 17.99,
            "hdr_50_centroid_lon": 72.49,
            "hdr_90_centroid_lat": 17.99,
            "hdr_90_centroid_lon": 72.49,
            "hdr_50_component_count": 1,
            "hdr_90_component_count": 1,
        },
    ]

    diagnostics = calculate_temporal_diagnostics(raw_results)

    # 1. Verify chronological ordering
    timestamps = [d["timestamp"] for d in diagnostics]
    assert timestamps == sorted(timestamps), "Results not chronologically ordered"

    # 2. Verify skipped timestamp handling
    skipped_item = diagnostics[2]  # 10:00:00Z
    assert skipped_item["status"] == "skipped_insufficient_particles"
    assert skipped_item["hdr_50_area_m2"] is None

    # 3. Verify valid results
    valid_items = [d for d in diagnostics if d["status"] == "success"]
    assert len(valid_items) == 3

    # Step 0 (08:00:00Z)
    item0 = valid_items[0]
    assert item0["hdr_50_area_change_m2"] == 0.0
    assert item0["hdr_50_centroid_displacement_m"] == 0.0
    assert item0["hdr_50_area_relative_change"] == 0.0
    assert item0["hdr_50_component_count"] == 2
    assert item0["hdr_90_component_count"] == 3

    # Step 1 (09:00:00Z) vs Step 0 (08:00:00Z)
    item1 = valid_items[1]
    expected_a50_change = 5500000.0 - 5000000.0
    expected_rel50 = 500000.0 / 5000000.0
    assert abs(item1["hdr_50_area_change_m2"] - expected_a50_change) < 1e-3
    assert abs(item1["hdr_50_area_relative_change"] - expected_rel50) < 1e-5
    assert item1["hdr_50_centroid_displacement_m"] > 0.0

    # Step 2 (12:00:00Z) vs Step 1 (09:00:00Z)
    item2 = valid_items[2]
    expected_a50_change2 = 6000000.0 - 5500000.0
    expected_rel50_2 = 500000.0 / 5500000.0
    assert abs(item2["hdr_50_area_change_m2"] - expected_a50_change2) < 1e-3
    assert abs(item2["hdr_50_area_relative_change"] - expected_rel50_2) < 1e-5
    assert item2["hdr_50_centroid_displacement_m"] > 0.0

    a50_vals = [d["hdr_50_area_m2"] for d in valid_items]
    a90_vals = [d["hdr_90_area_m2"] for d in valid_items]
    disps = [
        max(d["hdr_50_centroid_displacement_m"], d["hdr_90_centroid_displacement_m"])
        for d in valid_items
    ]
    rel_changes = [
        max(
            abs(d["hdr_50_area_relative_change"]),
            abs(d["hdr_90_area_relative_change"]),
        )
        for d in valid_items
    ]

    print("=======================================================================")
    print("SOURCE SUPPORT TEMPORAL DIAGNOSTICS TEST TABLE")
    print("=======================================================================")
    for d in diagnostics:
        if d["status"] == "success":
            print(
                f"[{d['timestamp']}] 50% Area: {d['hdr_50_area_km2']:.3f}km² | "
                f"90% Area: {d['hdr_90_area_km2']:.3f}km² | "
                f"Disp50: {d['hdr_50_centroid_displacement_m']:.1f}m | "
                f"Rel50: {d['hdr_50_area_relative_change']:+.2%}"
            )
        else:
            print(f"[{d['timestamp']}] Status: {d['status']}")

    print("=======================================================================")
    print("DIAGNOSTIC TEST SUMMARY")
    print("=======================================================================")
    print(f"Number of Timestamps:           {len(diagnostics)}")
    print(f"50% HDR Area Min and Max:       {min(a50_vals):.0f} m² to {max(a50_vals):.0f} m²")
    print(f"90% HDR Area Min and Max:       {min(a90_vals):.0f} m² to {max(a90_vals):.0f} m²")
    print(f"Maximum Centroid Displacement:  {max(disps):.2f} m")
    print(f"Maximum Relative Area Change:   {max(rel_changes):.4%}")
    print("=======================================================================\n")

    print("Source Support Temporal Diagnostics Tests: PASSED")


if __name__ == "__main__":
    test_source_support_diagnostics()
