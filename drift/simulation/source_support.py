"""Source Support Timeline Analysis Module.

Analyzes backward particle trajectories across time steps to construct spatial probability distributions,
HDR geometries, and area trends for probabilistic source region estimation.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from shapely.geometry import MultiPolygon, Polygon

from drift.simulation.coordinates import project_latlon_to_xy
from drift.simulation.hdr import extract_hdr
from drift.simulation.hdr_geometry import (
    hdr_mask_to_geometry,
    project_hdr_geometry_to_latlon,
)
from drift.simulation.kde import estimate_kde


def analyze_source_support(
    trajectories_by_timestamp: Dict[str, List[Dict[str, float]]],
    grid_resolution: int = 100,
    hdr_levels: Tuple[float, ...] = (0.50, 0.90),
    reference_lon: Optional[float] = None,
    reference_lat: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Perform temporal source-support analysis over grouped backward particle trajectories."""
    if not trajectories_by_timestamp:
        return []

    # Sort timestamps in chronological order
    sorted_timestamps = sorted(trajectories_by_timestamp.keys())

    # Determine reference origin if not provided
    if reference_lon is None or reference_lat is None:
        all_lons = []
        all_lats = []
        for particles in trajectories_by_timestamp.values():
            for p in particles:
                lon = p.get("longitude")
                lat = p.get("latitude")
                if lon is not None and lat is not None and np.isfinite(lon) and np.isfinite(lat):
                    all_lons.append(float(lon))
                    all_lats.append(float(lat))
        if not all_lons:
            raise ValueError("No valid particle coordinates found across any timestamp.")
        reference_lon = float(np.mean(all_lons))
        reference_lat = float(np.mean(all_lats))

    results = []

    for ts in sorted_timestamps:
        particles = trajectories_by_timestamp[ts]
        lons = []
        lats = []
        for p in particles:
            lon = p.get("longitude")
            lat = p.get("latitude")
            if lon is not None and lat is not None and np.isfinite(lon) and np.isfinite(lat):
                lons.append(float(lon))
                lats.append(float(lat))

        particle_count = len(lons)

        if particle_count < 2:
            results.append({
                "timestamp": ts,
                "particle_count": particle_count,
                "status": "skipped_insufficient_particles",
                "kde_max_density": 0.0,
                "hdr_50_area_m2": 0.0,
                "hdr_90_area_m2": 0.0,
                "hdr_50_threshold": 0.0,
                "hdr_90_threshold": 0.0,
                "hdr_50_component_count": 0,
                "hdr_90_component_count": 0,
                "hdr_50_centroid": (None, None),
                "hdr_90_centroid": (None, None),
                "hdr_50_geometry": Polygon(),
                "hdr_90_geometry": Polygon(),
            })
            continue

        # Project Lat/Lon to local metric X/Y in meters
        x, y = project_latlon_to_xy(lons, lats, reference_lon, reference_lat)

        # Estimate KDE density on 2D grid
        grid_x, grid_y, density = estimate_kde(x, y, grid_resolution=grid_resolution)
        kde_max_density = float(np.max(density))

        ts_result: Dict[str, Any] = {
            "timestamp": ts,
            "particle_count": particle_count,
            "status": "success",
            "kde_max_density": kde_max_density,
            "reference_origin": (reference_lon, reference_lat),
        }

        for level in hdr_levels:
            level_percent = int(round(level * 100))

            # Extract HDR mask and metrics
            hdr_data = extract_hdr(grid_x, grid_y, density, probability_mass=level)
            threshold = hdr_data["threshold"]

            # Convert mask to metric geometry (in meters)
            metric_geom = hdr_mask_to_geometry(grid_x, grid_y, hdr_data["mask"])

            # Compute area in square meters from metric geometry BEFORE geographic conversion
            area_m2 = float(metric_geom.area)

            # Component count
            if metric_geom.is_empty:
                comp_count = 0
            elif isinstance(metric_geom, MultiPolygon):
                comp_count = len(metric_geom.geoms)
            else:
                comp_count = 1

            # Project metric geometry to WGS84 geographic Lon/Lat
            geo_geom = project_hdr_geometry_to_latlon(metric_geom, reference_lon, reference_lat)

            # Calculate centroid coordinates
            if not geo_geom.is_empty:
                centroid = (float(geo_geom.centroid.x), float(geo_geom.centroid.y))
            else:
                centroid = (None, None)

            ts_result[f"hdr_{level_percent}_area_m2"] = area_m2
            ts_result[f"hdr_{level_percent}_threshold"] = threshold
            ts_result[f"hdr_{level_percent}_component_count"] = comp_count
            ts_result[f"hdr_{level_percent}_centroid"] = centroid
            ts_result[f"hdr_{level_percent}_geometry"] = geo_geom
            ts_result[f"hdr_{level_percent}_metric_geometry"] = metric_geom

        results.append(ts_result)

    return results
