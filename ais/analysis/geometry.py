"""
Geometric calculations for AIS analysis.

- Haversine distance between geographic points
- Polygon containment (point-in-polygon)
- Course difference (circular)
"""

import math
from typing import NamedTuple


class Coordinate(NamedTuple):
    """Geographic coordinate in WGS84."""
    latitude: float
    longitude: float


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: First point (decimal degrees)
        lat2, lon2: Second point (decimal degrees)
    
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def circular_course_difference(course1: float, course2: float) -> float:
    """
    Calculate the smallest angular difference between two courses (degrees).
    
    Courses are in range [0, 360). Returns [0, 180].
    
    Args:
        course1, course2: Courses in degrees (0-360)
    
    Returns:
        Minimum angular difference in degrees (0-180)
    """
    diff = abs(course1 - course2) % 360
    return min(diff, 360 - diff)


def point_in_polygon(lat: float, lon: float, polygon: dict) -> bool:
    """
    Check if a point is inside a GeoJSON polygon using ray casting algorithm.
    
    Args:
        lat, lon: Point coordinates (WGS84)
        polygon: GeoJSON Polygon dict with "type" and "coordinates"
    
    Returns:
        True if point is inside polygon, False otherwise
    """
    if polygon.get("type") != "Polygon":
        return False
    
    coords = polygon.get("coordinates", [[]])
    if not coords or not coords[0]:
        return False
    
    # Use exterior ring (index 0)
    ring = coords[0]
    
    # Ray casting algorithm
    inside = False
    x, y = lon, lat
    p1x, p1y = ring[0]
    
    for i in range(1, len(ring)):
        p2x, p2y = ring[i]
        
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        
        p1x, p1y = p2x, p2y
    
    return inside


def polygon_bounds(polygon: dict) -> dict | None:
    """
    Extract geographic bounds from a GeoJSON Polygon.
    
    Args:
        polygon: GeoJSON Polygon dict
    
    Returns:
        Dict with minLat, maxLat, minLon, maxLon, or None if invalid
    """
    if polygon.get("type") != "Polygon":
        return None
    
    coords = polygon.get("coordinates", [[]])
    if not coords or not coords[0]:
        return None
    
    # Flatten all coordinates from exterior ring
    ring = coords[0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    
    if not lons or not lats:
        return None
    
    return {
        "minLatitude": min(lats),
        "maxLatitude": max(lats),
        "minLongitude": min(lons),
        "maxLongitude": max(lons),
    }
