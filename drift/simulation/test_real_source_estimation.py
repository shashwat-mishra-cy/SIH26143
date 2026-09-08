"""Validation test for model-supported source-time estimation using real forcing data.

Runs the existing estimate_source_time() function against the temporal diagnostics
produced by the end-to-end backward drift pipeline with real ERA5 wind and Copernicus ocean currents.
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
from drift.simulation.source_support_diagnostics import (
    calculate_temporal_diagnostics,
)
from drift.simulation.source_estimation import estimate_source_time


def test_real_source_estimation() -> None:
    # 1. Spill polygon in real data domain (around 72.5°E, 18.0°N)
    spill_coords = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.53, 18.00],
        [72.51, 18.01],
        [72.47, 18.01],
        [72.46, 18.00],
    ]
    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    duration_hours = 6.0
    number_of_particles = 500
    time_step_minutes = 10.0

    # 2. Backward simulation with real ERA5 + Copernicus
    result_data = run_polygon_backward_simulation(
        polygon_coordinates=spill_coords,
        detection_time=detection_time,
        duration_hours=duration_hours,
        number_of_particles=number_of_particles,
        time_step_minutes=time_step_minutes,
        horizontal_diffusivity=1.0,
    )

    # 3. Group trajectories
    trajectories = result_data["trajectories"]
    grouped = group_trajectories_by_timestamp(trajectories)

    # 4. Source support analysis
    support_results = analyze_source_support(grouped)

    # 5. Temporal diagnostics
    diagnostics = calculate_temporal_diagnostics(support_results)

    # 6. Estimate source time using existing estimator
    estimation_result = estimate_source_time(diagnostics)

    # 7. Print validation metrics
    valid_diags = [d for d in diagnostics if d["status"] == "success"]
    ts_list = [d["timestamp"] for d in valid_diags]

    min_50_diag = min(valid_diags, key=lambda d: d["hdr_50_area_m2"])
    min_90_diag = min(valid_diags, key=lambda d: d["hdr_90_area_m2"])

    print("===========================================================")
    print("REAL SOURCE-TIME ESTIMATION VALIDATION")
    print("===========================================================")
    print(f"Detection time:             {detection_time.isoformat()}Z")
    print(f"First backward timestamp:   {ts_list[0] if ts_list else 'N/A'}")
    print(f"Last backward timestamp:    {ts_list[-1] if ts_list else 'N/A'}")
    print(f"Number of valid timestamps: {len(valid_diags)}")
    print()
    print("50% HDR minimum:")
    print(f"- timestamp: {min_50_diag['timestamp']}")
    print(f"- area:      {min_50_diag['hdr_50_area_km2']:.3f} km² ({min_50_diag['hdr_50_area_m2']:.0f} m²)")
    print()
    print("90% HDR minimum:")
    print(f"- timestamp: {min_90_diag['timestamp']}")
    print(f"- area:      {min_90_diag['hdr_90_area_km2']:.3f} km² ({min_90_diag['hdr_90_area_m2']:.0f} m²)")
    print()
    print("Source estimator result:")
    print(f"- status:                   {estimation_result['status']}")
    print(f"- candidate_source_time:    {estimation_result['candidate_source_time']}")
    print(f"- source_time_window_start: {estimation_result['source_time_window_start']}")
    print(f"- source_time_window_end:   {estimation_result['source_time_window_end']}")
    print(f"- reason:                   {estimation_result['reason']}")
    print(f"- supporting_timestamps:    {estimation_result['supporting_timestamps']}")
    print()
    print("Result Classification Check:")
    print(f"- candidate_identified:             {estimation_result['status'] == 'candidate_identified'}")
    print(f"- indeterminate_flat_signal:        {estimation_result['status'] == 'indeterminate_flat_signal'}")
    print(f"- indeterminate_boundary_minimum:   {estimation_result['status'] == 'indeterminate_boundary_minimum'}")
    print(f"- indeterminate_conflicting_minima: {estimation_result['status'] == 'indeterminate_conflicting_minima'}")
    print(f"- insufficient_temporal_data:       {estimation_result['status'] == 'insufficient_temporal_data'}")
    print("===========================================================\n")


if __name__ == "__main__":
    test_real_source_estimation()
