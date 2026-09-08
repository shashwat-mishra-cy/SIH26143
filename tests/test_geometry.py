import numpy as np

from satellite.geometry.spill_geometry import (
    extract_spill_geometry
)


def main():

    # Create a synthetic image containing TWO
    # disconnected spill regions.
    mask = np.zeros((100, 100), dtype=np.uint8)

    # Spill component 1
    mask[20:40, 20:40] = 1

    # Spill component 2
    mask[60:80, 65:90] = 1

    result = extract_spill_geometry(mask)

    print("Spill detected:", result["spill_detected"])
    print("Geometry type:", result["geometry_type"])
    print("Number of components:", len(result["components"]))
    print("Total area (pixels):", result["total_area_pixels"])

    for index, component in enumerate(
        result["components"],
        start=1
    ):
        print(f"\nComponent {index}")
        print("  Area:", component["area_pixels"])
        print("  Centroid:", component["centroid_pixel"])
        print(
            "  Polygon points:",
            len(component["polygon_pixel"])
            if component["polygon_pixel"]
            else 0
        )


if __name__ == "__main__":
    main()