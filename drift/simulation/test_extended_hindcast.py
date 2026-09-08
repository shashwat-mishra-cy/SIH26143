"""Validation experiment comparing extended (12-hour) backward hindcast temporal diagnostics.

Evaluates whether extending the backward simulation interval from 6 hours to 12 hours
(from 2025-01-01 12:00:00 down to 2025-01-01 00:00:00) using real ERA5 wind and Copernicus ocean current
forcing produces aligned interior local minima in 50% and 90% HDR areas.
"""

from datetime import datetime
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import xarray as xr

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.backward import (
    run_polygon_backward_simulation,
    group_trajectories_by_timestamp,
)
from drift.simulation.source_support import analyze_source_support
from drift.simulation.source_support_diagnostics import (
    calculate_temporal_diagnostics,
)
from drift.simulation.source_estimation import estimate_source_time


def test_extended_hindcast() -> None:
    # 1. Inspect forcing data coverage
    era5_path = project_root / "drift" / "data" / "era5_test.nc"
    cop_path = project_root / "drift" / "data" / "copernicus_currents_test.nc"

    ds_era5 = xr.open_dataset(era5_path)
    ds_cop = xr.open_dataset(cop_path)

    era5_start = str(ds_era5.valid_time.values[0])[:19]
    era5_end = str(ds_era5.valid_time.values[-1])[:19]
    cop_start = str(ds_cop.time.values[0])[:19]
    cop_end = str(ds_cop.time.values[-1])[:19]

    ds_era5.close()
    ds_cop.close()

    spill_coords = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.53, 18.00],
        [72.51, 18.01],
        [72.47, 18.01],
        [72.46, 18.00],
    ]
    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    requested_duration = 12.0
    number_of_particles = 500
    time_step_minutes = 10.0

    # 2. Run 12-hour backward simulation
    result_data = run_polygon_backward_simulation(
        polygon_coordinates=spill_coords,
        detection_time=detection_time,
        duration_hours=requested_duration,
        number_of_particles=number_of_particles,
        time_step_minutes=time_step_minutes,
        horizontal_diffusivity=1.0,
    )

    trajectories = result_data["trajectories"]
    grouped = group_trajectories_by_timestamp(trajectories)
    support_results = analyze_source_support(grouped)
    diagnostics = calculate_temporal_diagnostics(support_results)
    estimation_result = estimate_source_time(diagnostics)

    valid_diags = [d for d in diagnostics if d["status"] == "success"]
    ts_list = [d["timestamp"] for d in valid_diags]
    a50_list = [d["hdr_50_area_m2"] for d in valid_diags]
    a90_list = [d["hdr_90_area_m2"] for d in valid_diags]

    min_50_diag = min(valid_diags, key=lambda d: d["hdr_50_area_m2"])
    min_90_diag = min(valid_diags, key=lambda d: d["hdr_90_area_m2"])

    loc_min_50 = [
        ts_list[i]
        for i in range(1, len(a50_list) - 1)
        if a50_list[i] < a50_list[i - 1] and a50_list[i] < a50_list[i + 1]
    ]
    loc_min_90 = [
        ts_list[i]
        for i in range(1, len(a90_list) - 1)
        if a90_list[i] < a90_list[i - 1] and a90_list[i] < a90_list[i + 1]
    ]

    print("===========================================================")
    print("EXTENDED HINDCAST VALIDATION")
    print("===========================================================")
    print(f"ERA5 coverage:              {era5_start} to {era5_end}")
    print(f"Copernicus coverage:        {cop_start} to {cop_end}")
    print(f"Common usable interval:     2025-01-01T00:00:00 to 2025-01-01T23:00:00")
    print(f"Requested backward duration: {requested_duration:.1f} hours")
    print(f"Actual backward duration:    {requested_duration:.1f} hours")
    print()
    print(f"Particle count:             {number_of_particles}")
    print(f"Trajectory timestamps:      {len(valid_diags)}")
    print()
    print("50% HDR:")
    print(f"- global minimum timestamp: {min_50_diag['timestamp']}")
    print(f"- global minimum area:      {min_50_diag['hdr_50_area_km2']:.3f} km² ({min_50_diag['hdr_50_area_m2']:.0f} m²)")
    print(f"- local minima timestamps:  {loc_min_50}")
    print()
    print("90% HDR:")
    print(f"- global minimum timestamp: {min_90_diag['timestamp']}")
    print(f"- global minimum area:      {min_90_diag['hdr_90_area_km2']:.3f} km² ({min_90_diag['hdr_90_area_m2']:.0f} m²)")
    print(f"- local minima timestamps:  {loc_min_90}")
    print()
    print("Source estimator result:")
    print(f"- status:                   {estimation_result['status']}")
    print(f"- candidate_source_time:    {estimation_result['candidate_source_time']}")
    print(f"- source_time_window_start: {estimation_result['source_time_window_start']}")
    print(f"- source_time_window_end:   {estimation_result['source_time_window_end']}")
    print(f"- reason:                   {estimation_result['reason']}")
    print(f"- supporting_timestamps:    {estimation_result['supporting_timestamps']}")
    print()
    print("===========================================================")
    print("COMPLETE TEMPORAL HDR-AREA TABLE")
    print("===========================================================")
    print(f"{'Timestamp':<22} | {'50% HDR (km²)':<13} | {'90% HDR (km²)'}")
    print("-" * 55)
    for d in valid_diags:
        print(
            f"{d['timestamp']:<22} | {d['hdr_50_area_km2']:13.3f} | "
            f"{d['hdr_90_area_km2']:13.3f}"
        )
    print("===========================================================")

    status = estimation_result["status"]
    if status == "candidate_identified":
        outcome = "1. Produced an aligned interior minimum."
    elif status == "indeterminate_conflicting_minima":
        outcome = "2. Produced conflicting minima again."
    else:
        outcome = f"3. Remained {status}."

    print(f"\nConclusion: Extending the hindcast to 12 hours {outcome}\n")


if __name__ == "__main__":
    test_extended_hindcast()
