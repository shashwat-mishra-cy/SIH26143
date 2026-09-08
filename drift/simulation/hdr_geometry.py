"""HDR Mask to Geometry Conversion Module.

Converts 2D boolean HDR masks on local metric X/Y grids into Shapely Polygon
or MultiPolygon vector geometries, preserving connected components, boundaries, and holes.
"""

from typing import Union
import numpy as np
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.ops import unary_union

try:
    from shapely.validation import make_valid
except ImportError:
    make_valid = lambda geom: geom.buffer(0)


def hdr_mask_to_geometry(
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    hdr_mask: np.ndarray,
) -> Union[Polygon, MultiPolygon]:
    """Convert a 2D boolean HDR mask on a metric grid into Shapely Polygon or MultiPolygon geometry.

    Args:
        grid_x: 2D numpy array of evaluation X coordinates in meters.
        grid_y: 2D numpy array of evaluation Y coordinates in meters.
        hdr_mask: 2D boolean numpy array indicating selected grid cells.

    Returns:
        Shapely Polygon (for 1 connected region/empty) or MultiPolygon (for disconnected regions)
        in local metric X/Y coordinates (meters).

    Raises:
        ValueError: If array shapes are incompatible or hdr_mask is not boolean.
    """
    grid_x_arr = np.asarray(grid_x, dtype=float)
    grid_y_arr = np.asarray(grid_y, dtype=float)
    hdr_mask_arr = np.asarray(hdr_mask)

    if grid_x_arr.ndim != 2 or grid_y_arr.ndim != 2 or hdr_mask_arr.ndim != 2:
        raise ValueError(
            f"grid_x, grid_y, and hdr_mask must all be 2D arrays (got ndims: {grid_x_arr.ndim}, {grid_y_arr.ndim}, {hdr_mask_arr.ndim})."
        )

    if not (grid_x_arr.shape == grid_y_arr.shape == hdr_mask_arr.shape):
        raise ValueError(
            f"Array shape mismatch: grid_x={grid_x_arr.shape}, grid_y={grid_y_arr.shape}, hdr_mask={hdr_mask_arr.shape}."
        )

    if hdr_mask_arr.dtype != bool:
        raise ValueError(
            f"hdr_mask must be a boolean array (got dtype {hdr_mask_arr.dtype})."
        )

    if not np.any(hdr_mask_arr):
        return Polygon()

    # Calculate grid cell dimensions dx and dy in meters
    dx = abs(float(grid_x_arr[0, 1] - grid_x_arr[0, 0]))
    dy = abs(float(grid_y_arr[1, 0] - grid_y_arr[0, 0]))

    # Construct rectangular bounding boxes for all selected grid cells
    cell_indices = np.argwhere(hdr_mask_arr)
    cell_boxes = [
        box(
            grid_x_arr[i, j] - dx / 2.0,
            grid_y_arr[i, j] - dy / 2.0,
            grid_x_arr[i, j] + dx / 2.0,
            grid_y_arr[i, j] + dy / 2.0,
        )
        for i, j in cell_indices
    ]

    union_geom = unary_union(cell_boxes)

    if not union_geom.is_valid:
        union_geom = make_valid(union_geom)

    if isinstance(union_geom, (Polygon, MultiPolygon)):
        return union_geom

    if isinstance(union_geom, GeometryCollection):
        polys = [g for g in union_geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polys:
            return Polygon()
        filtered_union = unary_union(polys)
        return filtered_union

    return Polygon()


def project_hdr_geometry_to_latlon(
    geometry: Union[Polygon, MultiPolygon],
    reference_longitude: float,
    reference_latitude: float,
) -> Union[Polygon, MultiPolygon]:
    """Project a local metric X/Y Shapely geometry to WGS84 Geographic (Lon/Lat) coordinates.

    Reuses project_xy_to_latlon from drift.simulation.coordinates without duplicating projection math.

    Args:
        geometry: Shapely Polygon or MultiPolygon in local metric X/Y coordinates (meters).
        reference_longitude: Longitude of projection origin (°E).
        reference_latitude: Latitude of projection origin (°N).

    Returns:
        Shapely Polygon or MultiPolygon in decimal degrees (Longitude, Latitude).
    """
    from shapely.ops import transform
    from drift.simulation.coordinates import project_xy_to_latlon

    if geometry.is_empty:
        return geometry

    def _coord_transform(x, y, z=None):
        lons, lats = project_xy_to_latlon(x, y, reference_longitude, reference_latitude)
        if z is not None:
            return lons, lats, z
        return lons, lats

    geo_geom = transform(_coord_transform, geometry)
    if not geo_geom.is_valid:
        geo_geom = make_valid(geo_geom)

    if isinstance(geo_geom, GeometryCollection):
        polys = [g for g in geo_geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polys:
            return Polygon()
        geo_geom = unary_union(polys)

    return geo_geom
