"""End-to-End Integration Test for SIH26143 Drift Pipeline.

Integrates real ERA5 wind and Copernicus ocean current forcing datasets with polygon-based
backward particle tracking, metric coordinate projection, 2D KDE density estimation,
Highest Density Region (HDR) thresholding, and vector geometry transformation.
"""

from datetime import datetime
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shapely.geometry import Polygon
from drift.simulation.backward import (
    run_polygon_backward_simulation,
    group_trajectories_by_timestamp,
)
from drift.simulation.source_support import analyze_source_support


def test_end_to_end() -> None:
    # 1. Define synthetic irregular spill polygon in real data domain (around 72.5°E, 18.0°N)
    spill_coords = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.53, 18.00],
        [72.51, 18.01],
        [72.47, 18.01],
        [72.46, 18.00],
    ]
    spill_poly = Polygon(spill_coords)
    assert spill_poly.is_valid, "Irregular spill polygon is invalid!"
    min_lon, min_lat, max_lon, max_lat = spill_poly.bounds

    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    duration_hours = 6.0
    number_of_particles = 500
    time_step_minutes = 10.0

    print("=======================================================================")
    print("STARTING END-TO-END SIH26143 DRIFT PIPELINE INTEGRATION TEST")
    print("=======================================================================")
    print(f"Spill Polygon Bounds: Lon [{min_lon:.4f}, {max_lon:.4f}], Lat [{min_lat:.4f}, {max_lat:.4f}]")
    print(f"Detection Timestamp:  {detection_time.isoformat()}Z")
    print(f"Particles Seeded:     {number_of_particles}")
    print("Using Forcing:        Real ERA5 Winds + Copernicus Ocean Currents\n")

    # 2. Run backward simulation with real ERA5 and Copernicus readers
    result_data = run_polygon_backward_simulation(
        polygon_coordinates=spill_coords,
        detection_time=detection_time,
        duration_hours=duration_hours,
        number_of_particles=number_of_particles,
        time_step_minutes=time_step_minutes,
        horizontal_diffusivity=1.0,
    )

    trajectories = result_data["trajectories"]
    assert len(trajectories) == number_of_particles, f"Expected {number_of_particles} trajectories"

    # 3. Group trajectories by timestamp
    grouped = group_trajectories_by_timestamp(trajectories)
    num_timestamps = len(grouped)
    ts_keys = list(grouped.keys())

    print(f"Trajectory Timestamps Extracted: {num_timestamps}")
    print(f"First Trajectory Timestamp (Observation): {ts_keys[0]}")
    print(f"Last Trajectory Timestamp (Origin):      {ts_keys[-1]}\n")

    # 4. Perform source-support analysis
    support_results = analyze_source_support(grouped)

    valid_results = [r for r in support_results if r.get("status") == "success"]
    skipped_results = [r for r in support_results if r.get("status") != "success"]

    print("=======================================================================")
    print("PER-TIMESTAMP SOURCE-SUPPORT DIAGNOSTICS")
    print("=======================================================================")

    hdr_50_areas_km2 = []
    hdr_90_areas_km2 = []
    all_geoms_valid = True
    area_ordering_valid = True

    for r in valid_results:
        ts = r["timestamp"]
        count = r["particle_count"]

        area_50_km2 = r["hdr_50_area_m2"] / 1e6
        area_90_km2 = r["hdr_90_area_m2"] / 1e6

        hdr_50_areas_km2.append(area_50_km2)
        hdr_90_areas_km2.append(area_90_km2)

        max_dens = r["kde_max_density"]
        g50 = r["hdr_50_geometry"]
        g90 = r["hdr_90_geometry"]

        type_50 = type(g50).__name__
        type_90 = type(g90).__name__

        comp_50 = r["hdr_50_component_count"]
        comp_90 = r["hdr_90_component_count"]

        if not (g50.is_valid and g90.is_valid):
            all_geoms_valid = False

        if area_90_km2 < area_50_km2:
            area_ordering_valid = False

        print(
            f"[{ts}] Particles: {count:3d} | "
            f"50% HDR: {area_50_km2:6.3f} km² ({type_50}, {comp_50} comp) | "
            f"90% HDR: {area_90_km2:6.3f} km² ({type_90}, {comp_90} comp) | "
            f"KDE Max: {max_dens:.2e} m⁻²"
        )

    print("=======================================================================")
    print("END-TO-END INTEGRATION TEST SUMMARY")
    print("=======================================================================")
    print(f"Total Timestamps Processed:        {len(support_results)}")
    print(f"Valid Timestamps:                  {len(valid_results)}")
    print(f"Skipped Timestamps:                {len(skipped_results)}")
    print(f"50% HDR Area Range:                {min(hdr_50_areas_km2):.3f} km² to {max(hdr_50_areas_km2):.3f} km²")
    print(f"90% HDR Area Range:                {min(hdr_90_areas_km2):.3f} km² to {max(hdr_90_areas_km2):.3f} km²")
    print(f"All Non-Empty Geometries Valid:    {all_geoms_valid}")
    print(f"90% Area >= 50% Area Verification: {area_ordering_valid}")
    print("=======================================================================\n")

    assert len(support_results) > 0, "No source support results generated!"
    assert len(valid_results) == num_timestamps, f"Expected {num_timestamps} valid results"
    assert all_geoms_valid, "One or more generated HDR geometries were invalid!"
    assert area_ordering_valid, "90% HDR area was less than 50% HDR area!"

    print("End-to-End Pipeline Integration Test: PASSED")


if __name__ == "__main__":
    test_end_to_end()
