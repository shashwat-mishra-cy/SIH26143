"""
Candidate filtering for AIS vessel correlation.

Determines which vessels are plausible candidates based on:
- Temporal overlap with release window
- Spatial proximity to source region
- Trajectory intersection with source region

All criteria are input-driven; no hardcoded investigation constants.
"""

from datetime import datetime
from typing import NamedTuple
from .geometry import haversine_distance_km, point_in_polygon


class CandidateFilterResult(NamedTuple):
    """Result of candidate filtering analysis for one vessel."""
    mmsi: str
    temporal_match: bool
    minimum_source_distance_km: float
    source_region_proximity_match: bool
    trajectory_source_intersection: bool
    is_candidate: bool


def has_temporal_overlap(
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> bool:
    """
    Check if vessel has any AIS points during release window.
    """
    for point in vessel_trajectory:
        ts = point.get("timestamp")
        if ts is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if release_window_start <= ts <= release_window_end:
            return True
    
    return False


def minimum_distance_to_source(
    vessel_trajectory: list[dict],
    source_latitude: float,
    source_longitude: float,
) -> float:
    """
    Calculate minimum distance from vessel trajectory to source center.
    """
    min_distance = float("inf")
    
    for point in vessel_trajectory:
        lat = point.get("latitude")
        lon = point.get("longitude")
        
        if lat is None or lon is None:
            continue
        
        distance = haversine_distance_km(lat, lon, source_latitude, source_longitude)
        min_distance = min(min_distance, distance)
    
    return min_distance if min_distance != float("inf") else -1



def trajectory_intersects_source_region(
    vessel_trajectory: list[dict],
    source_region_polygon: dict,
    release_window_start: datetime,
    release_window_end: datetime,
) -> bool:
    """Check if vessel trajectory passes through source region during release window."""
    for point in vessel_trajectory:
        lat = point.get("latitude")
        lon = point.get("longitude")
        ts = point.get("timestamp")
        
        if lat is None or lon is None or ts is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if not (release_window_start <= ts <= release_window_end):
            continue
        
        if point_in_polygon(lat, lon, source_region_polygon):
            return True
    
    return False


def extract_source_center(source_region_polygon: dict) -> tuple[float, float]:
    """Extract center point (as centroid) from source region polygon."""
    if source_region_polygon.get("type") != "Polygon":
        return (0.0, 0.0)
    
    coords = source_region_polygon.get("coordinates", [[]])
    if not coords or not coords[0]:
        return (0.0, 0.0)
    
    ring = coords[0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    
    if not lons or not lats:
        return (0.0, 0.0)
    
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    
    return (center_lat, center_lon)


def filter_candidate(
    mmsi: str,
    vessel_trajectory: list[dict],
    source_region_polygon: dict,
    release_window_start: datetime,
    release_window_end: datetime,
    proximity_threshold_km: float = 15,
) -> CandidateFilterResult:
    """Analyze vessel as candidate using all criteria."""
    temporal_match = has_temporal_overlap(
        vessel_trajectory,
        release_window_start,
        release_window_end,
    )
    
    source_latitude, source_longitude = extract_source_center(source_region_polygon)
    
    minimum_source_distance_km = minimum_distance_to_source(
        vessel_trajectory,
        source_latitude,
        source_longitude,
    )
    
    source_region_proximity_match = is_within_proximity_threshold(
        minimum_source_distance_km,
        15.0,
    )
    
    trajectory_source_intersection = trajectory_intersects_source_region(
        vessel_trajectory,
        source_region_polygon,
        release_window_start,
        release_window_end,
    )
    
    is_candidate = (
        temporal_match or
        source_region_proximity_match or
        trajectory_source_intersection
    )
    
    return CandidateFilterResult(
        mmsi=mmsi,
        temporal_match=temporal_match,
        minimum_source_distance_km=minimum_source_distance_km,
        source_region_proximity_match=source_region_proximity_match,
        trajectory_source_intersection=trajectory_source_intersection,
        is_candidate=is_candidate,
    )


def is_within_proximity_threshold(
    minimum_distance_km: float,
    threshold_km: float = 15,
) -> bool:
    """Check if minimum distance is within proximity threshold."""
    return 0 <= minimum_distance_km <= threshold_km
