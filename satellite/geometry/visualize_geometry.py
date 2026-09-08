from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio


PROBABILITY_PATH = Path(
    "full_scene_oil_00009_probability.npy"
)

IMAGE_PATH = Path(
    "C:/SIH-Main-Project/"
    "SIH26143_DATA/working/"
    "oil_image/00009.tif"
)

GEOMETRY_PATH = Path(
    "spill_geometry_oil_00009.json"
)

OUTPUT_PATH = Path(
    "spill_geometry_oil_00009_visualization.png"
)

THRESHOLD = 0.30


def load_sar_image():

    with rasterio.open(IMAGE_PATH) as src:

        image = src.read()
        transform = src.transform
        bounds = src.bounds

    return image, transform, bounds


def pixel_to_lonlat(transform, x, y):

    lon, lat = transform * (x, y)

    return float(lon), float(lat)


def plot_polygon(ax, polygon):

    if not polygon:
        return

    lons = [
        point[0]
        for point in polygon
    ]

    lats = [
        point[1]
        for point in polygon
    ]

    # Close polygon
    lons.append(lons[0])
    lats.append(lats[0])

    ax.plot(
        lons,
        lats,
        linewidth=1.5,
    )


def main():

    print("Loading SAR image...")

    image, transform, bounds = load_sar_image()

    print("Loading probability map...")

    probability = np.load(
        PROBABILITY_PATH
    )

    probability = np.squeeze(
        probability
    )

    print("Loading geometry JSON...")

    with open(
        GEOMETRY_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        geometry = json.load(file)

    # --------------------------------------------------------
    # Convert SAR VV to display image
    # --------------------------------------------------------

    vv = image[0]

    low = np.percentile(
        vv,
        2,
    )

    high = np.percentile(
        vv,
        98,
    )

    vv_display = np.clip(
        vv,
        low,
        high,
    )

    # --------------------------------------------------------
    # Geographic extent
    # --------------------------------------------------------

    extent = [
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top,
    ]

    # --------------------------------------------------------
    # Create figure
    # --------------------------------------------------------

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(20, 7),
    )

    # ========================================================
    # PANEL 1: SAR
    # ========================================================

    axes[0].imshow(
        vv_display,
        cmap="gray",
        extent=extent,
        origin="upper",
    )

    axes[0].set_title(
        "Sentinel-1 SAR VV"
    )

    axes[0].set_xlabel(
        "Longitude"
    )

    axes[0].set_ylabel(
        "Latitude"
    )

    # ========================================================
    # PANEL 2: U-NET PROBABILITY
    # ========================================================

    axes[1].imshow(
        probability,
        cmap="gray",
        extent=extent,
        origin="upper",
        vmin=0,
        vmax=1,
    )

    axes[1].set_title(
        f"U-Net Probability Map "
        f"(threshold = {THRESHOLD})"
    )

    axes[1].set_xlabel(
        "Longitude"
    )

    axes[1].set_ylabel(
        "Latitude"
    )

    # ========================================================
    # PANEL 3: GEOGRAPHIC POLYGONS
    # ========================================================

    axes[2].imshow(
        vv_display,
        cmap="gray",
        extent=extent,
        origin="upper",
    )

    axes[2].set_title(
        "Extracted Spill Geometry"
    )

    axes[2].set_xlabel(
        "Longitude"
    )

    axes[2].set_ylabel(
        "Latitude"
    )

    # --------------------------------------------------------
    # Draw components
    # --------------------------------------------------------

    for component in geometry[
        "components"
    ]:

        polygon = component[
            "polygon"
        ]

        plot_polygon(
            axes[2],
            polygon,
        )

        centroid = component[
            "centroid"
        ]

        lon = centroid["lon"]
        lat = centroid["lat"]

        axes[2].scatter(
            lon,
            lat,
            s=25,
        )

        axes[2].text(
            lon,
            lat,
            str(
                component[
                    "component_id"
                ]
            ),
            fontsize=8,
        )

    # --------------------------------------------------------
    # Overall title
    # --------------------------------------------------------

    fig.suptitle(
        "SIH26143 | Satellite Oil Spill Geometry Validation | Scene 00009",
        fontsize=16,
    )

    plt.tight_layout()

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    plt.savefig(
        OUTPUT_PATH,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print()
    print(
        "Visualization saved:"
    )

    print(
        OUTPUT_PATH.resolve()
    )


if __name__ == "__main__":
    main()