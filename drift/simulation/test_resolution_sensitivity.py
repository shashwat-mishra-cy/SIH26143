"""KDE/HDR Grid-Resolution Sensitivity Experiment on Real P2 Backward Pipeline.

Evaluates grid resolutions 50, 100, and 200 on representative timestamps from a 12-hour
backward simulation using real ERA5 wind and Copernicus ocean current forcing datasets.
OpenDrift particle tracking is executed ONCE, and KDE is evaluated efficiently
on representative timestamps to ensure minimal computational and memory footprint.
"""

from datetime import datetime
import math
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import numpy as np

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
from drift.simulation.coordinates import project_latlon_to_xy


SPILL_COORDS = [
    [72.48, 17.99],
    [72.52, 17.99],
    [72.53, 18.00],
    [72.51, 18.01],
    [72.47, 18.01],
    [72.46, 18.00],
]


def run_smoke_test() -> None:
    """Run a fast smoke test with 100 particles and 1 timestamp."""
    print("===========================================================")
    print("RUNNING RESOLUTION SENSITIVITY SMOKE TEST (100 particles, 1 timestamp)")
    print("===========================================================", flush=True)
    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    sim_result = run_polygon_backward_simulation(
        polygon_coordinates=SPILL_COORDS,
        detection_time=detection_time,
        duration_hours=0.1,  # 1 step
        number_of_particles=100,
        time_step_minutes=10.0,
        horizontal_diffusivity=1.0,
    )
    trajectories = sim_result["trajectories"]
    grouped = group_trajectories_by_timestamp(trajectories)
    ts_key = list(grouped.keys())[0]
    single_ts_grouped = {ts_key: grouped[ts_key]}

    for res in [50, 100, 200]:
        support = analyze_source_support(single_ts_grouped, grid_resolution=res)
        a50_km2 = support[0]["hdr_50_area_m2"] / 1e6
        a90_km2 = support[0]["hdr_90_area_m2"] / 1e6
        c50 = support[0]["hdr_50_component_count"]
        c90 = support[0]["hdr_90_component_count"]
        print(
            f"[SMOKE] Grid {res}x{res} -> 50% HDR: {a50_km2:.3f} km² (comp: {c50}), "
            f"90% HDR: {a90_km2:.3f} km² (comp: {c90})",
            flush=True,
        )

    print("===========================================================")
    print("SMOKE TEST PASSED SUCCESSFULLY")
    print("===========================================================\n", flush=True)



def test_resolution_sensitivity() -> None:
    print("===========================================================")
    print("GRID RESOLUTION SENSITIVITY EXPERIMENT (50 vs 100 vs 200)")
    print("===========================================================", flush=True)

    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    duration_hours = 12.0
    number_of_particles = 500
    time_step_minutes = 10.0

    print("Step 1: Running OpenDrift particle tracking (1 single simulation)...", flush=True)
    sim_result = run_polygon_backward_simulation(
        polygon_coordinates=SPILL_COORDS,
        detection_time=detection_time,
        duration_hours=duration_hours,
        number_of_particles=number_of_particles,
        time_step_minutes=time_step_minutes,
        horizontal_diffusivity=1.0,
    )
    trajectories = sim_result["trajectories"]
    grouped = group_trajectories_by_timestamp(trajectories)
    all_timestamps = sorted(grouped.keys())

    rep_timestamps = [
        t for t in all_timestamps
        if t.endswith(":00:00Z") or t.endswith(":00:00")
    ]
    if len(rep_timestamps) < 3:
        rep_timestamps = all_timestamps[::15]

    rep_grouped = {t: grouped[t] for t in rep_timestamps if t in grouped}
    print(f"Step 2: Selected {len(rep_grouped)} representative timestamps out of {len(all_timestamps)}:", flush=True)
    for t in rep_grouped:
        print(f"  - {t}", flush=True)

    resolutions = [50, 100, 200]
    res_summary = {}
    res_diagnostics = {}

    for res in resolutions:
        print(f"\nEvaluating grid resolution {res}x{res}...", flush=True)
        support = analyze_source_support(rep_grouped, grid_resolution=res)
        diags = calculate_temporal_diagnostics(support)
        estimation = estimate_source_time(diags)

        valid_diags = [d for d in diags if d["status"] == "success"]
        res_diagnostics[res] = valid_diags

        a50 = [d["hdr_50_area_km2"] for d in valid_diags]
        a90 = [d["hdr_90_area_km2"] for d in valid_diags]
        comp50 = [d["hdr_50_component_count"] for d in valid_diags]
        comp90 = [d["hdr_90_component_count"] for d in valid_diags]

        min_50_diag = min(valid_diags, key=lambda d: d["hdr_50_area_km2"])
        min_90_diag = min(valid_diags, key=lambda d: d["hdr_90_area_km2"])

        res_summary[res] = {
            "mean_50_km2": float(np.mean(a50)),
            "min_50_km2": float(min(a50)),
            "max_50_km2": float(max(a50)),
            "min_50_ts": min_50_diag["timestamp"],
            "min_50_centroid": (min_50_diag["hdr_50_centroid_lon"], min_50_diag["hdr_50_centroid_lat"]),
            "comp_50_min_max": (min(comp50), max(comp50)),
            "mean_90_km2": float(np.mean(a90)),
            "min_90_km2": float(min(a90)),
            "max_90_km2": float(max(a90)),
            "min_90_ts": min_90_diag["timestamp"],
            "min_90_centroid": (min_90_diag["hdr_90_centroid_lon"], min_90_diag["hdr_90_centroid_lat"]),
            "comp_90_min_max": (min(comp90), max(comp90)),
            "status": estimation["status"],
            "candidate_source_time": estimation["candidate_source_time"],
            "supporting_timestamps": estimation["supporting_timestamps"],
        }

        s = res_summary[res]
        print(f"--- RESULTS FOR {res}x{res} GRID ---", flush=True)
        print(f"A. 50% HDR Area Min/Max/Mean: {s['min_50_km2']:.3f} / {s['max_50_km2']:.3f} / {s['mean_50_km2']:.3f} km²", flush=True)
        print(f"   Min TS: {s['min_50_ts']} | Centroid: ({s['min_50_centroid'][0]:.5f}, {s['min_50_centroid'][1]:.5f}) | Comp Count: {s['comp_50_min_max'][0]}-{s['comp_50_min_max'][1]}", flush=True)
        print(f"B. 90% HDR Area Min/Max/Mean: {s['min_90_km2']:.3f} / {s['max_90_km2']:.3f} / {s['mean_90_km2']:.3f} km²", flush=True)
        print(f"   Min TS: {s['min_90_ts']} | Centroid: ({s['min_90_centroid'][0]:.5f}, {s['min_90_centroid'][1]:.5f}) | Comp Count: {s['comp_90_min_max'][0]}-{s['comp_90_min_max'][1]}", flush=True)
        print(f"C. Estimator Status: {s['status']} | Candidate: {s['candidate_source_time']}", flush=True)

    mean50_100 = res_summary[100]["mean_50_km2"]
    mean90_100 = res_summary[100]["mean_90_km2"]

    diff50_50 = abs(res_summary[50]["mean_50_km2"] - mean50_100) / mean50_100 * 100
    diff50_200 = abs(res_summary[200]["mean_50_km2"] - mean50_100) / mean50_100 * 100
    max_rel_diff_50 = max(diff50_50, diff50_200)

    diff90_50 = abs(res_summary[50]["mean_90_km2"] - mean90_100) / mean90_100 * 100
    diff90_200 = abs(res_summary[200]["mean_90_km2"] - mean90_100) / mean90_100 * 100
    max_rel_diff_90 = max(diff90_50, diff90_200)

    max_c50_dist_m = 0.0
    max_c90_dist_m = 0.0
    for d100, d50, d200 in zip(res_diagnostics[100], res_diagnostics[50], res_diagnostics[200]):
        for d_other in [d50, d200]:
            x50, y50 = project_latlon_to_xy(
                d_other["hdr_50_centroid_lon"], d_other["hdr_50_centroid_lat"],
                d100["hdr_50_centroid_lon"], d100["hdr_50_centroid_lat"]
            )
            dist50 = math.hypot(x50, y50)
            if dist50 > max_c50_dist_m:
                max_c50_dist_m = dist50

            x90, y90 = project_latlon_to_xy(
                d_other["hdr_90_centroid_lon"], d_other["hdr_90_centroid_lat"],
                d100["hdr_90_centroid_lon"], d100["hdr_90_centroid_lat"]
            )
            dist90 = math.hypot(x90, y90)
            if dist90 > max_c90_dist_m:
                max_c90_dist_m = dist90

    comp50_ranges = [res_summary[r]["comp_50_min_max"] for r in resolutions]
    comp90_ranges = [res_summary[r]["comp_90_min_max"] for r in resolutions]

    print("\n===========================================================")
    print("D. COMPARISON ACROSS RESOLUTIONS (Baseline: 100x100)")
    print("===========================================================")
    print(f"Relative difference in mean 50% HDR area vs 100x100: (50x50: {diff50_50:.2f}%, 200x200: {diff50_200:.2f}%)", flush=True)
    print(f"Relative difference in mean 90% HDR area vs 100x100: (50x50: {diff90_50:.2f}%, 200x200: {diff90_200:.2f}%)", flush=True)
    print(f"Maximum 50% centroid displacement vs 100x100 across timesteps: {max_c50_dist_m:.2f} meters", flush=True)
    print(f"Maximum 90% centroid displacement vs 100x100 across timesteps: {max_c90_dist_m:.2f} meters", flush=True)
    print(f"50% Component count ranges (50, 100, 200): {comp50_ranges}", flush=True)
    print(f"90% Component count ranges (50, 100, 200): {comp90_ranges}", flush=True)

    is_spatial_stable = (max_rel_diff_50 < 5.0) and (max_rel_diff_90 < 5.0) and (max(max_c50_dist_m, max_c90_dist_m) < 500.0)

    max_comps = [res_summary[r]["comp_50_min_max"][1] for r in resolutions] + [res_summary[r]["comp_90_min_max"][1] for r in resolutions]
    is_comp_sensitive = (max(max_comps) - min(max_comps)) > 2 or (max(max_comps) > 3 * min(max_comps) if min(max_comps) > 0 else True)

    print("\n===========================================================")
    print("SENSITIVITY EXPERIMENT CONCLUSIONS")
    print("===========================================================")
    if is_spatial_stable:
        print("Spatial results are resolution-stable", flush=True)
    else:
        print("Spatial results are resolution-sensitive", flush=True)

    if is_comp_sensitive:
        print("Component counts are strongly resolution-sensitive", flush=True)
    else:
        print("Component counts are resolution-stable", flush=True)
    print("===========================================================\n", flush=True)


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        run_smoke_test()
    else:
        test_resolution_sensitivity()
