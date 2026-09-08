from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio


DATA_ROOT = Path(
    r"C:\SIH-Main-Project\SIH26143_DATA\working"
)

IMAGE_PATH = DATA_ROOT / "oil_image" / "00009.tif"
MASK_PATH = DATA_ROOT / "oil_mask" / "00009.tif"

PREDICTION_PATH = Path("full_scene_00009_mask.npy")

OUTPUT_PATH = Path("full_scene_00009_comparison.png")


def load_image(path):
    with rasterio.open(path) as src:
        image = src.read().astype(np.float32)

    return image


def load_mask(path):
    with rasterio.open(path) as src:
        mask = src.read(1)

    return mask > 0


def main():

    print("Loading scene...")

    image = load_image(IMAGE_PATH)
    ground_truth = load_mask(MASK_PATH)
    prediction = np.load(PREDICTION_PATH) > 0

    vv = image[0]
    vh = image[1]

    # Display SAR using percentile clipping so the contrast is useful.
    vv_low, vv_high = np.percentile(vv, [2, 98])
    vv_display = np.clip(vv, vv_low, vv_high)

    vh_low, vh_high = np.percentile(vh, [2, 98])
    vh_display = np.clip(vh, vh_low, vh_high)

    intersection = np.logical_and(
        prediction,
        ground_truth
    ).sum()

    union = np.logical_or(
        prediction,
        ground_truth
    ).sum()

    predicted_pixels = prediction.sum()
    actual_pixels = ground_truth.sum()

    dice = (
        2 * intersection
        / (predicted_pixels + actual_pixels + 1e-8)
    )

    iou = (
        intersection
        / (union + 1e-8)
    )

    precision = (
        intersection
        / (predicted_pixels + 1e-8)
    )

    recall = (
        intersection
        / (actual_pixels + 1e-8)
    )

    print("\nFull-scene metrics")
    print("-------------------")
    print(f"Ground-truth oil pixels : {actual_pixels:,}")
    print(f"Predicted oil pixels    : {predicted_pixels:,}")
    print(f"Intersection            : {intersection:,}")
    print(f"Dice                    : {dice:.4f}")
    print(f"IoU                     : {iou:.4f}")
    print(f"Precision               : {precision:.4f}")
    print(f"Recall                  : {recall:.4f}")

    # Create a three-panel diagnostic figure.
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(18, 6)
    )

    axes[0].imshow(
        vv_display,
        cmap="gray"
    )
    axes[0].set_title("Sentinel-1 VV")
    axes[0].axis("off")

    axes[1].imshow(
        vv_display,
        cmap="gray"
    )
    axes[1].imshow(
        prediction,
        alpha=0.45
    )
    axes[1].set_title(
        f"U-Net Prediction\n"
        f"Dice={dice:.3f}, IoU={iou:.3f}"
    )
    axes[1].axis("off")

    axes[2].imshow(
        vv_display,
        cmap="gray"
    )
    axes[2].imshow(
        ground_truth,
        alpha=0.45
    )
    axes[2].set_title("Ground Truth")
    axes[2].axis("off")

    fig.suptitle(
        "Full-Scene Oil Spill Segmentation | Scene 00009",
        fontsize=16
    )

    plt.tight_layout()

    fig.savefig(
        OUTPUT_PATH,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"\nSaved visualization:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()