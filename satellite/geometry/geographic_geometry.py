from pathlib import Path
import json

import numpy as np
import rasterio
from pyproj import Geod
from skimage.measure import label, regionprops, find_contours


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_THRESHOLD = 0.30
DEFAULT_MIN_PIXELS = 50

GEOD = Geod(ellps="WGS84")


# ============================================================
# PIXEL -> GEOGRAPHIC COORDINATE
# ============================================================

def pixel_to_geo(
    row,
    col,
    transform,
):
    """
    Convert raster pixel coordinates to geographic
    longitude/latitude.

    Parameters
    ----------
    row : float
        Pixel row.
    col : float
        Pixel column.
    transform : rasterio.transform.Affine
        Raster geographic transform.

    Returns
    -------
    lon : float
    lat : float
    """

    lon, lat = rasterio.transform.xy(
        transform,
        row,
        col,
    )

    return float(lon), float(lat)


# ============================================================
# GEOGRAPHIC AREA
# ============================================================

def calculate_geographic_area(
    polygon,
):
    """
    Calculate polygon area in square meters using
    WGS84 geodesic calculations.

    Polygon format:
        [[lon, lat], [lon, lat], ...]
    """

    if polygon is None or len(polygon) < 3:
        return 0.0

    lons = [
        point[0]
        for point in polygon
    ]

    lats = [
        point[1]
        for point in polygon
    ]

    area, _ = GEOD.polygon_area_perimeter(
        lons,
        lats,
    )

    return abs(float(area))


# ============================================================
# GEOGRAPHIC PERIMETER
# ============================================================

def calculate_geographic_perimeter(
    polygon,
):
    """
    Calculate polygon perimeter in meters using
    WGS84 geodesic calculations.

    Polygon format:
        [[lon, lat], [lon, lat], ...]
    """

    if polygon is None or len(polygon) < 2:
        return 0.0

    lons = [
        point[0]
        for point in polygon
    ]

    lats = [
        point[1]
        for point in polygon
    ]

    _, perimeter = GEOD.polygon_area_perimeter(
        lons,
        lats,
    )

    return float(perimeter)


# ============================================================
# GEOGRAPHIC POLYGON
# ============================================================

def extract_geographic_polygon(
    binary_component,
    transform,
):
    """
    Convert a binary connected component into a
    geographic polygon.

    Returns:
        [[lon, lat], ...]
    """

    contours = find_contours(
        binary_component.astype(float),
        level=0.5,
    )

    if not contours:
        return None

    # Select the largest contour.
    contour = max(
        contours,
        key=len,
    )

    polygon = []

    for row, col in contour:

        lon, lat = pixel_to_geo(
            row,
            col,
            transform,
        )

        polygon.append(
            [
                lon,
                lat,
            ]
        )

    # Need at least 3 points for a polygon.
    if len(polygon) < 3:
        return None

    # Close polygon.
    if polygon[0] != polygon[-1]:
        polygon.append(
            polygon[0]
        )

    return polygon


# ============================================================
# GEOGRAPHIC BOUNDING BOX
# ============================================================

def calculate_geographic_bbox(
    polygon,
):
    """
    Calculate geographic bounding box.

    Returns:
        {
            "min_lon": ...,
            "min_lat": ...,
            "max_lon": ...,
            "max_lat": ...
        }
    """

    if polygon is None or len(polygon) == 0:
        return None

    lons = [
        point[0]
        for point in polygon
    ]

    lats = [
        point[1]
        for point in polygon
    ]

    return {
        "min_lon": float(min(lons)),
        "min_lat": float(min(lats)),
        "max_lon": float(max(lons)),
        "max_lat": float(max(lats)),
    }


# ============================================================
# EXTRACT GEOGRAPHIC GEOMETRY
# ============================================================

def extract_geographic_geometry(
    probability_map,
    transform,
    threshold=DEFAULT_THRESHOLD,
    min_pixels=DEFAULT_MIN_PIXELS,
):
    """
    Extract geographic spill geometry from a probability map.

    Pipeline:

        probability map
              ↓
        threshold
              ↓
        binary mask
              ↓
        connected components
              ↓
        geographic polygons
              ↓
        area / perimeter / centroid
    """

    # --------------------------------------------------------
    # Threshold probability map
    # --------------------------------------------------------

    binary_mask = (
        probability_map >= threshold
    ).astype(np.uint8)

    # --------------------------------------------------------
    # Connected components
    # --------------------------------------------------------

    labeled_mask = label(
        binary_mask,
        connectivity=2,
    )

    regions = regionprops(
        labeled_mask,
        intensity_image=probability_map,
    )

    components = []

    # --------------------------------------------------------
    # Process each component
    # --------------------------------------------------------

    component_id = 1

    for region in regions:

        area_pixels = int(
            region.area
        )

        # Ignore tiny components.
        if area_pixels < min_pixels:
            continue

        # ----------------------------------------------------
        # Pixel centroid
        # ----------------------------------------------------

        centroid_y, centroid_x = (
            region.centroid
        )

        # ----------------------------------------------------
        # Geographic centroid
        # ----------------------------------------------------

        centroid_lon, centroid_lat = (
            pixel_to_geo(
                centroid_y,
                centroid_x,
                transform,
            )
        )

        # ----------------------------------------------------
        # Pixel bounding box
        # ----------------------------------------------------

        min_row, min_col, max_row, max_col = (
            region.bbox
        )

        pixel_bbox = {
            "min_x": int(min_col),
            "min_y": int(min_row),
            "max_x": int(max_col),
            "max_y": int(max_row),
        }

        # ----------------------------------------------------
        # Geographic bounding box
        # ----------------------------------------------------

        bbox_corners = [
            pixel_to_geo(
                min_row,
                min_col,
                transform,
            ),
            pixel_to_geo(
                max_row,
                min_col,
                transform,
            ),
            pixel_to_geo(
                max_row,
                max_col,
                transform,
            ),
            pixel_to_geo(
                min_row,
                max_col,
                transform,
            ),
        ]

        bbox_lons = [
            point[0]
            for point in bbox_corners
        ]

        bbox_lats = [
            point[1]
            for point in bbox_corners
        ]

        geographic_bbox = {
            "min_lon": float(
                min(bbox_lons)
            ),
            "min_lat": float(
                min(bbox_lats)
            ),
            "max_lon": float(
                max(bbox_lons)
            ),
            "max_lat": float(
                max(bbox_lats)
            ),
        }

        # ----------------------------------------------------
        # Component binary mask
        # ----------------------------------------------------

        component_mask = (
            labeled_mask
            == region.label
        )

        # ----------------------------------------------------
        # Geographic polygon
        # ----------------------------------------------------

        polygon = extract_geographic_polygon(
            component_mask,
            transform,
        )

        # ----------------------------------------------------
        # Geographic area / perimeter
        # ----------------------------------------------------

        area_m2 = calculate_geographic_area(
            polygon
        )

        perimeter_m = calculate_geographic_perimeter(
            polygon
        )

        # ----------------------------------------------------
        # Length / width
        # ----------------------------------------------------

        try:
            major_axis = float(
                region.axis_major_length
            )

            minor_axis = float(
                region.axis_minor_length
            )

        except AttributeError:

            major_axis = None
            minor_axis = None

        # Approximate conversion using geographic
        # bounding box dimensions.

        length_m = None
        width_m = None

        if (
            geographic_bbox is not None
            and major_axis is not None
            and minor_axis is not None
        ):

            min_lon = geographic_bbox[
                "min_lon"
            ]

            max_lon = geographic_bbox[
                "max_lon"
            ]

            min_lat = geographic_bbox[
                "min_lat"
            ]

            max_lat = geographic_bbox[
                "max_lat"
            ]

            _, _, width_m_geo = GEOD.inv(
                min_lon,
                min_lat,
                max_lon,
                min_lat,
            )

            _, _, height_m_geo = GEOD.inv(
                min_lon,
                min_lat,
                min_lon,
                max_lat,
            )

            pixel_width = (
                max_col - min_col
            )

            pixel_height = (
                max_row - min_row
            )

            if pixel_width > 0:
                meters_per_pixel_x = (
                    width_m_geo
                    / pixel_width
                )
            else:
                meters_per_pixel_x = 0.0

            if pixel_height > 0:
                meters_per_pixel_y = (
                    height_m_geo
                    / pixel_height
                )
            else:
                meters_per_pixel_y = 0.0

            length_m = (
                major_axis
                * (
                    meters_per_pixel_x
                    + meters_per_pixel_y
                )
                / 2.0
            )

            width_m = (
                minor_axis
                * (
                    meters_per_pixel_x
                    + meters_per_pixel_y
                )
                / 2.0
            )

        # ----------------------------------------------------
        # Aspect ratio
        # ----------------------------------------------------

        if (
            length_m is not None
            and width_m is not None
            and width_m > 0
        ):

            aspect_ratio = (
                length_m
                / width_m
            )

        else:

            aspect_ratio = None

        # ----------------------------------------------------
        # Orientation
        # ----------------------------------------------------

        orientation_degrees = (
            float(
                np.degrees(
                    0.5
                    * np.arctan2(
                        2
                        * region.inertia_tensor[0, 1],
                        (
                            region.inertia_tensor[0, 0]
                            - region.inertia_tensor[1, 1]
                        ),
                    )
                )
            )
        )

        # ----------------------------------------------------
        # Probability statistics
        # ----------------------------------------------------

        component_probabilities = (
            probability_map[
                component_mask
            ]
        )

        mean_probability = float(
            component_probabilities.mean()
        )

        max_probability = float(
            component_probabilities.max()
        )

        # ----------------------------------------------------
        # Component dictionary
        # ----------------------------------------------------

        component = {

            "component_id": int(
                component_id
            ),

            "area_pixels": int(
                area_pixels
            ),

            "area_m2": float(
                area_m2
            ),

            "perimeter_m": float(
                perimeter_m
            ),

            "centroid_pixel": {
                "x": float(
                    centroid_x
                ),
                "y": float(
                    centroid_y
                ),
            },

            "centroid": {
                "lon": float(
                    centroid_lon
                ),
                "lat": float(
                    centroid_lat
                ),
            },

            "pixel_bbox": pixel_bbox,

            "geographic_bbox": geographic_bbox,

            "length_m": (
                float(length_m)
                if length_m is not None
                else None
            ),

            "width_m": (
                float(width_m)
                if width_m is not None
                else None
            ),

            "aspect_ratio": (
                float(aspect_ratio)
                if aspect_ratio is not None
                else None
            ),

            "orientation_degrees": (
                float(
                    orientation_degrees
                )
            ),

            "axis_major_length_pixels": (
                major_axis
            ),

            "axis_minor_length_pixels": (
                minor_axis
            ),

            "mean_probability": (
                mean_probability
            ),

            "max_probability": (
                max_probability
            ),

            "polygon": polygon,
        }

        components.append(
            component
        )

        component_id += 1

    # --------------------------------------------------------
    # Overall statistics
    # --------------------------------------------------------

    total_area_pixels = sum(
        component["area_pixels"]
        for component in components
    )

    total_area_m2 = sum(
        component["area_m2"]
        for component in components
    )

    # --------------------------------------------------------
    # Overall centroid
    # --------------------------------------------------------
    #
    # Area-weighted centroid across all detected components.
    # This provides one representative centroid for the
    # complete predicted spill geometry.
    # --------------------------------------------------------

    total_weight = sum(
        component["area_m2"]
        for component in components
    )

    if total_weight > 0:

        overall_centroid_lat = (
            sum(
                component["centroid"]["lat"]
                * component["area_m2"]
                for component in components
            )
            / total_weight
        )

        overall_centroid_lon = (
            sum(
                component["centroid"]["lon"]
                * component["area_m2"]
                for component in components
            )
            / total_weight
        )

    else:

        overall_centroid_lat = None
        overall_centroid_lon = None

    # --------------------------------------------------------
    # Overall perimeter
    # --------------------------------------------------------
    #
    # This is the sum of the perimeters of all detected
    # connected components.
    #
    # It is the aggregate perimeter of the detected components,
    # not the perimeter of a dissolved/unioned geometry.
    # --------------------------------------------------------

    total_perimeter_m = sum(
        component["perimeter_m"]
        for component in components
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    max_confidence = float(
        probability_map.max()
    )

    if components:

        mean_component_probability = float(
            np.mean([
                component[
                    "mean_probability"
                ]
                for component in components
            ])
        )

    else:

        mean_component_probability = 0.0

    # --------------------------------------------------------
    # GeoJSON geometry
    # --------------------------------------------------------

    valid_polygons = [
        component["polygon"]
        for component in components
        if (
            component["polygon"] is not None
            and len(component["polygon"]) >= 3
        )
    ]

    if len(valid_polygons) == 1:

        geometry_type = "Polygon"

        coordinates = [
            valid_polygons[0]
        ]

        geojson_geometry = {
            "type": "Polygon",
            "coordinates": coordinates,
        }

    elif len(valid_polygons) > 1:

        geometry_type = "MultiPolygon"

        coordinates = [
            [polygon]
            for polygon in valid_polygons
        ]

        geojson_geometry = {
            "type": "MultiPolygon",
            "coordinates": coordinates,
        }

    else:

        geometry_type = None
        geojson_geometry = None

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {

        "spill_detected": (
            len(components) > 0
        ),

        "centroid": {

            "lat": (
                float(
                    overall_centroid_lat
                )
                if overall_centroid_lat is not None
                else None
            ),

            "lon": (
                float(
                    overall_centroid_lon
                )
                if overall_centroid_lon is not None
                else None
            ),
        },

        "total_perimeter_m": float(
            total_perimeter_m
        ),

        "geometry_type": (
            geometry_type
        ),

        "threshold": float(
            threshold
        ),

        "min_pixels": int(
            min_pixels
        ),

        "component_count": len(
            components
        ),

        "total_area_pixels": int(
            total_area_pixels
        ),

        "total_area_m2": float(
            total_area_m2
        ),

        "max_confidence": (
            max_confidence
        ),

        "mean_probability": (
            mean_component_probability
        ),

        "components": components,

        "geojson": (

            {
                "type": "Feature",

                "properties": {

                    "spill_detected": (
                        len(components) > 0
                    ),

                    "threshold": float(
                        threshold
                    ),

                    "component_count": len(
                        components
                    ),

                    "total_area_pixels": int(
                        total_area_pixels
                    ),

                    "total_area_m2": float(
                        total_area_m2
                    ),

                    "total_perimeter_m": float(
                        total_perimeter_m
                    ),

                    "max_confidence": (
                        max_confidence
                    ),

                    "centroid": {

                        "lat": (
                            float(
                                overall_centroid_lat
                            )
                            if overall_centroid_lat is not None
                            else None
                        ),

                        "lon": (
                            float(
                                overall_centroid_lon
                            )
                            if overall_centroid_lon is not None
                            else None
                        ),
                    },
                },

                "geometry": (
                    geojson_geometry
                ),
            }

            if geojson_geometry is not None
            else None
        ),
    }


# ============================================================
# SAVE JSON
# ============================================================

def save_geometry_json(
    geometry,
    output_path,
):
    """
    Save extracted spill geometry to JSON.
    """

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            geometry,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


# ============================================================
# LOAD SAR METADATA
# ============================================================

def load_transform(
    image_path,
):
    """
    Read geographic transform and CRS from
    the original georeferenced SAR image.
    """

    with rasterio.open(
        image_path
    ) as src:

        return (
            src.transform,
            src.crs,
            src.bounds,
            src.width,
            src.height,
        )


# ============================================================
# PRINT RESULTS
# ============================================================

def print_results(
    geometry,
    crs=None,
):
    """
    Print human-readable geometry information.
    """

    print()
    print("=" * 70)
    print("SPILL GEOMETRY")
    print("=" * 70)

    print(
        f"Spill detected : "
        f"{geometry['spill_detected']}"
    )

    print(
        f"Geometry type  : "
        f"{geometry['geometry_type']}"
    )

    print(
        f"Components     : "
        f"{geometry['component_count']}"
    )

    print(
        f"Total area px  : "
        f"{geometry['total_area_pixels']:,}"
    )

    print(
        f"Total area m²  : "
        f"{geometry['total_area_m2']:,.2f}"
    )

    print(
        f"Total perimeter: "
        f"{geometry['total_perimeter_m']:,.2f} m"
    )

    if geometry["centroid"]["lat"] is not None:

        print(
            f"Overall centroid: "
            f"{geometry['centroid']['lat']:.6f}, "
            f"{geometry['centroid']['lon']:.6f}"
        )

    else:

        print(
            "Overall centroid: N/A"
        )

    print(
        f"Max confidence : "
        f"{geometry['max_confidence']:.4f}"
    )

    if crs is not None:

        print(
            f"CRS            : {crs}"
        )

    print()
    print("Components:")
    print()

    for component in geometry[
        "components"
    ]:

        print(
            f"  Component "
            f"{component['component_id']}"
        )

        print(
            f"    Area       : "
            f"{component['area_pixels']:,} px"
        )

        print(
            f"    Area       : "
            f"{component['area_m2']:,.2f} m²"
        )

        print(
            f"    Perimeter  : "
            f"{component['perimeter_m']:,.2f} m"
        )

        print(
            f"    Centroid   : "
            f"{component['centroid']['lat']:.6f}, "
            f"{component['centroid']['lon']:.6f}"
        )

        print(
            f"    Length     : "
            f"{component['length_m']:.2f} m"
        )

        print(
            f"    Width      : "
            f"{component['width_m']:.2f} m"
        )

        aspect = component[
            "aspect_ratio"
        ]

        if aspect is None:

            aspect_text = "N/A"

        else:

            aspect_text = (
                f"{aspect:.2f}"
            )

        print(
            f"    Aspect     : "
            f"{aspect_text}"
        )

        print(
            f"    Orientation: "
            f"{component['orientation_degrees']:.2f}°"
        )

        print(
            f"    Mean prob. : "
            f"{component['mean_probability']:.4f}"
        )

        print(
            f"    Max prob.  : "
            f"{component['max_probability']:.4f}"
        )

        print()


# ============================================================
# DEMO / COMMAND LINE
# ============================================================

def main():
    """
    Run geometry extraction for oil scene 00009.

    This is currently a prototype CLI.
    """

    probability_path = Path(
        "full_scene_oil_00009_probability.npy"
    )

    image_path = Path(
        "C:/SIH-Main-Project/"
        "SIH26143_DATA/working/"
        "oil_image/00009.tif"
    )

    output_path = Path(
        "spill_geometry_oil_00009.json"
    )

    # --------------------------------------------------------
    # Verify files
    # --------------------------------------------------------

    if not probability_path.exists():

        raise FileNotFoundError(
            f"Probability map not found:\n"
            f"{probability_path.resolve()}"
        )

    if not image_path.exists():

        raise FileNotFoundError(
            f"SAR image not found:\n"
            f"{image_path}"
        )

    # --------------------------------------------------------
    # Load probability map
    # --------------------------------------------------------

    probability_map = np.load(
        probability_path
    )

    # --------------------------------------------------------
    # Load geographic information
    # --------------------------------------------------------

    (
        transform,
        crs,
        bounds,
        width,
        height,
    ) = load_transform(
        image_path
    )

    print(
        f"CRS: {crs}"
    )

    print(
        f"Threshold: "
        f"{DEFAULT_THRESHOLD}"
    )

    # --------------------------------------------------------
    # Extract geometry
    # --------------------------------------------------------

    geometry = extract_geographic_geometry(
        probability_map=probability_map,
        transform=transform,
        threshold=DEFAULT_THRESHOLD,
        min_pixels=DEFAULT_MIN_PIXELS,
    )

    # --------------------------------------------------------
    # Add scene metadata
    # --------------------------------------------------------

    geometry["scene"] = {

        "image_id": "00009",

        "category": "oil",

        "width": int(
            width
        ),

        "height": int(
            height
        ),

        "crs": str(
            crs
        ),

        "bounds": {

            "left": float(
                bounds.left
            ),

            "bottom": float(
                bounds.bottom
            ),

            "right": float(
                bounds.right
            ),

            "top": float(
                bounds.top
            ),
        },
    }

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print_results(
        geometry,
        crs=crs,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    saved_path = save_geometry_json(
        geometry,
        output_path,
    )

    print(
        "Saved geometry JSON:"
    )

    print(
        saved_path.resolve()
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
