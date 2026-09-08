"""Backward Hindcast Drift Simulation Module.

Provides reverse-in-time particle tracking simulations to estimate the origin
trajectory of detected oil spills using ERA5 wind and Copernicus ocean current forcing.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import random
from shapely.geometry import Point, Polygon, MultiPolygon

# Ensure project root is in sys.path when executed as a direct script
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from opendrift.models.oceandrift import OceanDrift
from drift.data.environment import EnvironmentalDataLoader


def extract_trajectories(result: Any) -> Dict[str, List[List[Dict[str, Any]]]]:
    """Extract machine-readable timestamped trajectories from OpenDrift result dataset.

    Args:
        result: xarray Dataset output from OpenDrift simulation (o.result).

    Returns:
        Dict[str, List[List[Dict[str, Any]]]]: Dictionary containing list of
        particle trajectories with absolute UTC ISO-8601 timestamps and coordinates.
    """
    import numpy as np
    import pandas as pd

    trajectories = []
    num_trajectories = result.sizes["trajectory"]
    times = result.time.values

    lats = result.lat.values
    lons = result.lon.values

    for i in range(num_trajectories):
        points = []
        for t, time_val in enumerate(times):
            lat = float(lats[i, t])
            lon = float(lons[i, t])
            if np.isnan(lat) or np.isnan(lon):
                continue
            ts_str = pd.Timestamp(time_val).strftime("%Y-%m-%dT%H:%M:%SZ")
            points.append({
                "timestamp": ts_str,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6)
            })
        trajectories.append(points)

    return {"trajectories": trajectories}

def sample_points_in_geometry(
    geometry: Union[Polygon, MultiPolygon],
    number_of_points: int,
    seed: int = 42,
) -> Tuple[List[float], List[float]]:
    """Sample random particle starting locations inside a Shapely Polygon or MultiPolygon.

    Args:
        geometry: Shapely Polygon or MultiPolygon object representing spill extent.
        number_of_points: Number of particle locations to generate.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (longitude list, latitude list).
    """
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise TypeError("geometry must be a Shapely Polygon or MultiPolygon object.")

    if not geometry.is_valid:
        raise ValueError("Provided geometry is invalid.")

    min_lon, min_lat, max_lon, max_lat = geometry.bounds

    rng = random.Random(seed)

    longitudes: List[float] = []
    latitudes: List[float] = []

    while len(longitudes) < number_of_points:
        lon = rng.uniform(min_lon, max_lon)
        lat = rng.uniform(min_lat, max_lat)

        point = Point(lon, lat)

        if geometry.contains(point):
            longitudes.append(lon)
            latitudes.append(lat)

    return longitudes, latitudes


def sample_points_in_polygon(
    polygon_coordinates: List[List[float]],
    number_of_points: int,
    seed: int = 42,
) -> Tuple[List[float], List[float]]:
    """Sample random particle starting locations inside a spill polygon.

    Args:
        polygon_coordinates: Polygon vertices as [[lon, lat], ...].
        number_of_points: Number of particle locations to generate.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of longitude list and latitude list.
    """
    polygon = Polygon(polygon_coordinates)
    return sample_points_in_geometry(polygon, number_of_points, seed=seed)


def run_backward_simulation(
    longitude: float,
    latitude: float,
    detection_time: datetime,
    duration_hours: float = 6.0,
    number_of_particles: int = 10,
    time_step_minutes: float = 10.0,
) -> Dict[str, List[List[Dict[str, Any]]]]:
    """Run an OpenDrift backward hindcast particle tracking simulation.

    Args:
        longitude: Spill observation longitude in decimal degrees.
        latitude: Spill observation latitude in decimal degrees.
        detection_time: Datetime object representing the spill observation time (UTC).
        duration_hours: Total backtrack duration in hours (default: 6.0).
        number_of_particles: Number of Lagrangian particles to seed (default: 10).
        time_step_minutes: Time step interval in minutes (default: 10.0).

    Returns:
        Dict[str, List[List[Dict[str, Any]]]]: Extracted machine-readable timestamped trajectories.
    """
    env_loader = EnvironmentalDataLoader()
    readers = env_loader.get_opendrift_readers()

    o = OceanDrift(loglevel=20)
    o.add_reader(readers)

    o.seed_elements(lon=longitude, lat=latitude, number=number_of_particles, time=detection_time)
    o.run(
        duration=timedelta(hours=duration_hours),
        time_step=-timedelta(minutes=time_step_minutes),
    )

    return extract_trajectories(o.result)

def run_polygon_backward_simulation(
    polygon_coordinates: Union[List[List[float]], Polygon, MultiPolygon],
    detection_time: datetime,
    duration_hours: float = 6.0,
    number_of_particles: int = 500,
    time_step_minutes: float = 10.0,
    horizontal_diffusivity: float = 1.0,
) -> Dict[str, List[List[Dict[str, Any]]]]:

    env_loader = EnvironmentalDataLoader()
    readers = env_loader.get_opendrift_readers()

    if isinstance(polygon_coordinates, (Polygon, MultiPolygon)):
        geometry = polygon_coordinates
    else:
        geometry = Polygon(polygon_coordinates)

    longitudes, latitudes = sample_points_in_geometry(
        geometry,
        number_of_particles,
    )

    o = OceanDrift(loglevel=20)

    o.add_reader(readers)

    o.set_config(
        'environment:constant:horizontal_diffusivity',
        horizontal_diffusivity,
    )

    o.seed_elements(
        lon=longitudes,
        lat=latitudes,
        time=detection_time,
    )

    o.run(
        duration=timedelta(hours=duration_hours),
        time_step=-timedelta(minutes=time_step_minutes),
    )

    return extract_trajectories(o.result)

def group_trajectories_by_timestamp(
    trajectories: List[List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, float]]]:
    """Group particle positions by timestamp.

    Args:
        trajectories: Particle trajectories returned by extract_trajectories().

    Returns:
        Dictionary mapping each timestamp to particle positions.
    """

    grouped: Dict[str, List[Dict[str, float]]] = {}

    for trajectory in trajectories:
        for point in trajectory:
            timestamp = point["timestamp"]

            if timestamp not in grouped:
                grouped[timestamp] = []

            grouped[timestamp].append({
                "latitude": point["latitude"],
                "longitude": point["longitude"],
            })

    return grouped


def plot_particle_clouds(
    grouped_data: Dict[str, List[Dict[str, float]]],
    timestamps: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> None:
    """Plot diagnostic scatter map of particle clouds at selected timestamps.

    Args:
        grouped_data: Dictionary mapping timestamps to lists of particle positions.
        timestamps: List of ISO-8601 timestamps to plot. Defaults to
            ["2025-01-01T12:00:00Z", "2025-01-01T09:00:00Z", "2025-01-01T06:00:00Z"].
        output_path: Optional file path to save the generated plot image.
    """
    import matplotlib.pyplot as plt

    if timestamps is None:
        timestamps = [
            "2025-01-01T12:00:00Z",
            "2025-01-01T09:00:00Z",
            "2025-01-01T06:00:00Z",
        ]

    plt.figure(figsize=(9, 7))

    valid_count = 0
    for ts in timestamps:
        if ts not in grouped_data:
            print(f"Warning: Requested timestamp '{ts}' not found in grouped trajectory data.")
            continue

        particles = grouped_data[ts]
        longitudes = [p["longitude"] for p in particles]
        latitudes = [p["latitude"] for p in particles]

        print(f"[plot_particle_clouds Diagnostic] Timestamp: {ts}")
        print(f"  len(particles):  {len(particles)}")
        print(f"  len(longitudes): {len(longitudes)}")
        print(f"  len(latitudes):  {len(latitudes)}")

        plt.scatter(longitudes, latitudes, label=f"t = {ts}", alpha=0.6, s=20)
        valid_count += 1

    if valid_count == 0:
        print("No valid timestamps found to plot.")
        plt.close()
        return

    plt.xlabel("Longitude (°E)")
    plt.ylabel("Latitude (°N)")
    plt.title("Backward Drift Particle Cloud Diagnostic Plot")
    plt.legend(loc="best")
    plt.grid(True, linestyle="--", alpha=0.5)

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Diagnostic particle cloud plot saved to: {output_path}")

    plt.show()




def main() -> None:
    """Run a test backward hindcast drift experiment using run_backward_simulation."""
     
    longitude = 72.5
    latitude = 18.0
    detection_time = datetime(2025, 1, 1, 12, 0, 0)

    result_data = run_backward_simulation(
        longitude=longitude,
        latitude=latitude,
        detection_time=detection_time,
        duration_hours=6.0,
        number_of_particles=10,
        time_step_minutes=10.0,
    )

    trajectories = result_data["trajectories"]
    grouped = group_trajectories_by_timestamp(trajectories)

    print(f"Number of timestamps: {len(grouped)}")

    for timestamp, particles in grouped.items():
        print(
            timestamp,
            "→",
            len(particles),
            "particles"
        )

    
    test_polygon = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.52, 18.01],
        [72.48, 18.01],
    ]

    detection_time = datetime(2025, 1, 1, 12, 0, 0)

    result_data = run_polygon_backward_simulation(
        polygon_coordinates=test_polygon,
        detection_time=detection_time,
        duration_hours=6,
        number_of_particles=500,
        time_step_minutes=10,
    )
    polygon_trajectories = result_data["trajectories"]

    print(f"Number of trajectories: {len(polygon_trajectories)}")
    print(f"Points per trajectory: {len(polygon_trajectories[0])}")

    grouped = group_trajectories_by_timestamp(polygon_trajectories)

    target_timestamps = [
        "2025-01-01T12:00:00Z",
        "2025-01-01T09:00:00Z",
        "2025-01-01T06:00:00Z",
    ]

    print("\n================ DATA FLOW DIAGNOSTIC BEFORE PLOTTING ================")
    print(f"len(grouped_data): {len(grouped)}")
    for ts in target_timestamps:
        if ts in grouped:
            particles_at_ts = grouped[ts]
            print(f"Timestamp '{ts}': len = {len(particles_at_ts)}")
            print(f"  First 5 particle coordinates:")
            for idx, p in enumerate(particles_at_ts[:5]):
                print(f"    [{idx}] lon: {p['longitude']}, lat: {p['latitude']}")
        else:
            print(f"Timestamp '{ts}': NOT FOUND")
    print("======================================================================\n")

    # Plot diagnostic scatter map of particle clouds at default timestamps
    plot_particle_clouds(grouped)

    print(f"Number of timestamps: {len(grouped)}")

    for timestamp, particles in grouped.items():
        print(
            timestamp,
            "→",
            len(particles),
            "particles"
        )

    trajectories = result_data["trajectories"]
    all_points = [
        point
        for trajectory in trajectories
        for point in trajectory
    ]

    print(f"Total trajectory points: {len(all_points)}")

    print(
        "First particle:",
        trajectories[0][0],
    )

    print(
        "Last particle:",
        trajectories[0][-1],
    )

    print(
        "Last timestamp:",
        trajectories[0][-1]["timestamp"],
    )

    print(f"Number of trajectories: {len(trajectories)}")
    print(f"Points in first trajectory: {len(trajectories[0])}")

    


if __name__ == "__main__":
    main()




