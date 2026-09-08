"""Test suite for Source Support Timeline Analysis module (source_support.py).

Validates multi-timestamp timeline processing, chronological ordering, HDR area calculations,
and particle validation error handling.
"""

from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.source_support import analyze_source_support


def test_source_support() -> None:
    np.random.seed(42)

    # 1. Create synthetic backward trajectory dataset (3 valid timestamps + 1 empty/skipped timestamp)
    timestamps = [
        "2025-01-01T12:00:00Z",  # observation time
        "2025-01-01T09:00:00Z",  # mid time
        "2025-01-01T06:00:00Z",  # 6h backtrack
    ]

    # Centers drifting slightly
    centers = {
        "2025-01-01T12:00:00Z": (72.50, 18.00),
        "2025-01-01T09:00:00Z": (72.49, 18.005),
        "2025-01-01T06:00:00Z": (72.48, 18.010),
    }

    trajectories_by_timestamp = {}

    for ts in timestamps:
        c_lon, c_lat = centers[ts]
        lons = np.random.normal(c_lon, 0.005, 500)
        lats = np.random.normal(c_lat, 0.005, 500)
        trajectories_by_timestamp[ts] = [
            {"longitude": float(lo), "latitude": float(la)} for lo, la in zip(lons, lats)
        ]

    # Add an empty/invalid timestamp to verify handling
    trajectories_by_timestamp["2025-01-01T03:00:00Z"] = [
        {"longitude": np.nan, "latitude": np.nan}
    ]

    # 2. Run analyze_source_support()
    results = analyze_source_support(trajectories_by_timestamp)

    # 3. Assertions & Verification
    assert len(results) == 4, f"Expected 4 processed timestamps, got {len(results)}"

    # Verify chronological ordering
    res_timestamps = [r["timestamp"] for r in results]
    expected_order = [
        "2025-01-01T03:00:00Z",
        "2025-01-01T06:00:00Z",
        "2025-01-01T09:00:00Z",
        "2025-01-01T12:00:00Z",
    ]
    assert res_timestamps == expected_order, f"Timestamps not in chronological order! Got {res_timestamps}"

    # Verify skipped timestamp
    skipped_res = results[0]
    assert skipped_res["particle_count"] == 0, f"Expected 0 valid particles, got {skipped_res['particle_count']}"
    assert skipped_res["status"] == "skipped_insufficient_particles"

    # Verify valid timestamps
    valid_results = results[1:]
    all_geoms_valid = True
    hdr_50_areas = []
    hdr_90_areas = []

    for r in valid_results:
        ts = r["timestamp"]
        assert r["particle_count"] == 500, f"Expected 500 particles at {ts}, got {r['particle_count']}"
        assert r["status"] == "success"

        kde_max = r["kde_max_density"]
        assert np.isfinite(kde_max) and kde_max > 0, f"Invalid max density at {ts}: {kde_max}"

        geom_50 = r["hdr_50_geometry"]
        geom_90 = r["hdr_90_geometry"]

        if not (geom_50.is_valid and geom_90.is_valid):
            all_geoms_valid = False

        assert geom_50.is_valid, f"Invalid 50% HDR geometry at {ts}"
        assert geom_90.is_valid, f"Invalid 90% HDR geometry at {ts}"

        area_50 = r["hdr_50_area_m2"]
        area_90 = r["hdr_90_area_m2"]

        assert area_50 > 0, f"Expected positive 50% HDR area at {ts}, got {area_50}"
        assert area_90 > 0, f"Expected positive 90% HDR area at {ts}, got {area_90}"
        assert area_90 >= area_50, f"90% HDR area ({area_90}) should be >= 50% HDR area ({area_50}) at {ts}"

        hdr_50_areas.append(area_50)
        hdr_90_areas.append(area_90)

        assert r["hdr_50_component_count"] >= 1, f"Invalid component count at {ts}"
        assert r["hdr_90_component_count"] >= 1, f"Invalid component count at {ts}"

    assert all_geoms_valid, "Not all generated HDR geometries were valid!"

    # 4. Summary Output
    print("Source support timeline analysis tests: PASSED")
    print(f"- Number of timestamps processed: {len(results)}")
    print(f"- Valid timestamps particle count: {[r['particle_count'] for r in valid_results]}")
    print(f"- 50% HDR area range: {min(hdr_50_areas):.2f} m² to {max(hdr_50_areas):.2f} m²")
    print(f"- 90% HDR area range: {min(hdr_90_areas):.2f} m² to {max(hdr_90_areas):.2f} m²")
    print(f"- All geometries valid: {all_geoms_valid}")


if __name__ == "__main__":
    test_source_support()
