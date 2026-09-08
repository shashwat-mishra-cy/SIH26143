import numpy as np
from skimage.measure import find_contours, label, regionprops


def extract_spill_geometry(mask, min_pixels=20):
    """
    Extract spill geometry from a binary segmentation mask.

    Multiple disconnected spill regions are preserved separately.

    Args:
        mask: 2D binary mask. 0 = background, 1 = spill.
        min_pixels: Minimum component size to keep.

    Returns:
        Dictionary containing pixel-based geometry.
    """

    mask = np.asarray(mask)

    if mask.ndim != 2:
        raise ValueError(
            f"Expected a 2D mask, got shape {mask.shape}"
        )

    binary_mask = mask > 0

    labeled_mask = label(binary_mask)

    regions = [
        region
        for region in regionprops(labeled_mask)
        if region.area >= min_pixels
    ]

    # No significant spill detected
    if not regions:
        return {
            "spill_detected": False,
            "geometry_type": None,
            "components": [],
            "total_area_pixels": 0,
        }

    components = []

    for region in regions:
        region_mask = labeled_mask == region.label

        contours = find_contours(
            region_mask.astype(float),
            level=0.5
        )

        if not contours:
            polygon = None
        else:
            # Keep the longest contour for this component.
            contour = max(contours, key=len)

            # find_contours returns [row, column] = [y, x].
            # Convert to [x, y].
            polygon = [
                [float(point[1]), float(point[0])]
                for point in contour
            ]

        centroid_y, centroid_x = region.centroid

        components.append({
            "area_pixels": int(region.area),
            "centroid_pixel": {
                "x": float(centroid_x),
                "y": float(centroid_y),
            },
            "polygon_pixel": polygon,
        })

    total_area = sum(
        component["area_pixels"]
        for component in components
    )

    if len(components) == 1:
        geometry_type = "Polygon"
    else:
        geometry_type = "MultiPolygon"

    return {
        "spill_detected": True,
        "geometry_type": geometry_type,
        "components": components,
        "total_area_pixels": total_area,
    }