"""Local metric coordinate projection module for drift simulations.

Provides forward (Lat/Lon -> X/Y in meters) and inverse (X/Y in meters -> Lat/Lon)
projections using Azimuthal Equidistant (AEQD) projection centered on a reference coordinate.
"""

from typing import Any, Sequence, Tuple, Union
import numpy as np

try:
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


def _get_transformers(reference_longitude: float, reference_latitude: float) -> Tuple[Any, Any, str]:
    """Build PyProj Transformers for local Azimuthal Equidistant projection.

    Args:
        reference_longitude: Longitude of the origin in decimal degrees (°E).
        reference_latitude: Latitude of the origin in decimal degrees (°N).

    Returns:
        Tuple of (forward_transformer, inverse_transformer, projection_string).
    """
    if not PYPROJ_AVAILABLE:
        raise ImportError(
            "pyproj package is not installed. Please install pyproj to perform coordinate projections."
        )

    proj_str = (
        f"+proj=aeqd +lat_0={reference_latitude} +lon_0={reference_longitude} "
        f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    fwd = Transformer.from_crs("EPSG:4326", proj_str, always_xy=True)
    inv = Transformer.from_crs(proj_str, "EPSG:4326", always_xy=True)
    return fwd, inv, proj_str


def project_latlon_to_xy(
    longitudes: Union[float, Sequence[float], np.ndarray],
    latitudes: Union[float, Sequence[float], np.ndarray],
    reference_longitude: float,
    reference_latitude: float,
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """Convert longitude/latitude coordinates to local metric X, Y coordinates in meters.

    The reference point (reference_longitude, reference_latitude) maps to local origin (0, 0) meters.
    Coordinate input order: (longitudes, latitudes) in decimal degrees.
    Coordinate output order: (x, y) in meters easting and northing.

    Args:
        longitudes: Longitude coordinate float or sequence of floats (°E).
        latitudes: Latitude coordinate float or sequence of floats (°N).
        reference_longitude: Longitude of local projection origin (°E).
        reference_latitude: Latitude of local projection origin (°N).

    Returns:
        Tuple of (x, y) coordinates in meters relative to reference origin.
    """
    fwd, _, _ = _get_transformers(reference_longitude, reference_latitude)
    x, y = fwd.transform(longitudes, latitudes)
    return x, y


def project_xy_to_latlon(
    x: Union[float, Sequence[float], np.ndarray],
    y: Union[float, Sequence[float], np.ndarray],
    reference_longitude: float,
    reference_latitude: float,
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """Convert local metric X, Y coordinates in meters back to longitude/latitude.

    Coordinate input order: (x, y) in meters easting and northing.
    Coordinate output order: (longitudes, latitudes) in decimal degrees.

    Args:
        x: Local X coordinate float or sequence of floats (meters easting).
        y: Local Y coordinate float or sequence of floats (meters northing).
        reference_longitude: Longitude of local projection origin (°E).
        reference_latitude: Latitude of local projection origin (°N).

    Returns:
        Tuple of (longitudes, latitudes) in decimal degrees.
    """
    _, inv, _ = _get_transformers(reference_longitude, reference_latitude)
    longitudes, latitudes = inv.transform(x, y)
    return longitudes, latitudes
