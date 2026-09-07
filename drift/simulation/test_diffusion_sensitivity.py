"""Diffusion Sensitivity Experiment for Backward Drift Simulation.

Runs backward particle tracking simulations under three horizontal diffusivity values:
0 m²/s, 1 m²/s, and 5 m²/s to analyze particle cloud dispersion over time.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from opendrift.models.oceandrift import OceanDrift
from drift.data.environment import EnvironmentalDataLoader
from drift.simulation.backward import (
    extract_trajectories,
    group_trajectories_by_timestamp,
    plot_particle_clouds,
    sample_points_in_polygon,
)


def run_diffusion_sensitivity_experiment() -> None:
    """Run sensitivity analysis for horizontal_diffusivity values: 0, 1, 5 m²/s."""

    test_polygon = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.52, 18.01],
        [72.48, 18.01],
    ]
    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    diffusivity_values = [0.0, 1.0, 5.0]

    target_timestamps = [
        "2025-01-01T12:00:00Z",
        "2025-01-01T09:00:00Z",
        "2025-01-01T06:00:00Z",
    ]

    print("=======================================================================")
    print("STARTING CONTROLLED DIFFUSION SENSITIVITY EXPERIMENT")
    print("=======================================================================")

    summaries = []

    for diff_val in diffusivity_values:
        print(f"\n--- RUNNING SIMULATION WITH horizontal_diffusivity = {diff_val} m²/s ---")

        env_loader = EnvironmentalDataLoader()
        readers = env_loader.get_opendrift_readers()

        longitudes, latitudes = sample_points_in_polygon(
            polygon_coordinates=test_polygon,
            number_of_points=500,
            seed=42,
        )

        o = OceanDrift(loglevel=20)
        o.add_reader(readers)

        o.set_config("environment:constant:horizontal_diffusivity", diff_val)

        o.seed_elements(
            lon=longitudes,
            lat=latitudes,
            time=detection_time,
        )

        o.run(
            duration=timedelta(hours=6),
            time_step=-timedelta(minutes=10),
        )

        applied_val = o.get_config("environment:constant:horizontal_diffusivity")

        result_data = extract_trajectories(o.result)
        trajectories = result_data["trajectories"]
        grouped = group_trajectories_by_timestamp(trajectories)

        print(f"Diffusion config confirmed applied: {applied_val} m²/s")
        print(f"Number of trajectories: {len(trajectories)}")
        print(f"Points per trajectory: {len(trajectories[0])}")

        # Compute bounding boxes / spread metrics for comparison across 12:00, 09:00, 06:00
        ts_metrics = {}
        for ts in target_timestamps:
            if ts in grouped:
                pts = grouped[ts]
                lons = [p["longitude"] for p in pts]
                lats = [p["latitude"] for p in pts]
                lon_span = max(lons) - min(lons)
                lat_span = max(lats) - min(lats)
                ts_metrics[ts] = {
                    "count": len(pts),
                    "lon_range": (round(min(lons), 6), round(max(lons), 6)),
                    "lat_range": (round(min(lats), 6), round(max(lats), 6)),
                    "lon_span": round(lon_span, 6),
                    "lat_span": round(lat_span, 6),
                }

        summaries.append({
            "diffusivity": diff_val,
            "applied_diffusivity": applied_val,
            "ts_metrics": ts_metrics,
        })

        # Render diagnostic plot
        plot_particle_clouds(grouped, output_path=f"diffusion_{int(diff_val)}_m2s.png")

    print("\n=======================================================================")
    print("SENSITIVITY EXPERIMENT SUMMARY")
    print("=======================================================================")
    for run in summaries:
        diff = run["diffusivity"]
        applied = run["applied_diffusivity"]
        print(f"\nDiffusivity Setting: {diff} m²/s | Applied Config: {applied} m²/s")
        for ts, m in run["ts_metrics"].items():
            print(
                f"  [{ts}] Particles: {m['count']} | "
                f"Lon Span: {m['lon_span']}° ({m['lon_range'][0]} to {m['lon_range'][1]}) | "
                f"Lat Span: {m['lat_span']}° ({m['lat_range'][0]} to {m['lat_range'][1]})"
            )
    print("=======================================================================\n")


if __name__ == "__main__":
    run_diffusion_sensitivity_experiment()
