from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio


DATA_ROOT = Path(
    r"C:\SIH-Main-Project\SIH26143_DATA\working"
)

SCENES = [
    ("oil", "00009"),
    ("oil", "00010"),
    ("lookalike", "00005"),
    ("lookalike", "00006"),
    ("no_oil", "00005"),
    ("no_oil", "00006"),
]

THRESHOLD = 0.50

OUTPUT_PATH = Path(
    "validation_scenes_comparison.png"
)


def load_sar(path):
    with rasterio.open(path) as src:
        return src.read().astype(np.float32)


def load_mask(path):
    with rasterio.open(path) as src:
        return src.read(1) > 0


def calculate_metrics(prediction, ground_truth):
    prediction = prediction.astype(bool)
    ground_truth = ground_truth.astype(bool)

    tp = np.logical_and(
        prediction,
        ground_truth
    ).sum()

    fp = np.logical_and(
        prediction,
        ~ground_truth
    ).sum()

    fn = np.logical_and(
        ~prediction,
        ground_truth
    ).sum()

    predicted = prediction.sum()
    actual = ground_truth.sum()

    dice = (
        2 * tp
        / (predicted + actual + 1e-8)
    )

    iou = (
        tp
        / (tp + fp + fn + 1e-8)
    )

    precision = (
        tp
        / (tp + fp + 1e-8)
    )

    recall = (
        tp
        / (tp + fn + 1e-8)
    )

    return dice, iou, precision, recall


def main():

    print("=" * 80)
    print("VALIDATION SCENE VISUALIZATION")
    print("=" * 80)

    fig, axes = plt.subplots(
        6,
        3,
        figsize=(15, 25)
    )

    for row, (category, scene_id) in enumerate(SCENES):

        print(
            f"\nProcessing {category}/{scene_id}"
        )

        image_path = (
            DATA_ROOT
            / f"{category}_image"
            / f"{scene_id}.tif"
        )

        mask_path = (
            DATA_ROOT
            / f"{category}_mask"
            / f"{scene_id}.tif"
        )

        probability_path = Path(
            f"full_scene_{category}_"
            f"{scene_id}_probability.npy"
        )

        # --------------------------------------------------
        # Load data
        # --------------------------------------------------

        image = load_sar(image_path)
        ground_truth = load_mask(mask_path)
        probability = np.load(
            probability_path
        )

        prediction = (
            probability >= THRESHOLD
        )

        # --------------------------------------------------
        # SAR display
        # --------------------------------------------------

        vv = image[0]

        low, high = np.percentile(
            vv,
            [2, 98]
        )

        vv_display = np.clip(
            vv,
            low,
            high
        )

        # --------------------------------------------------
        # Metrics
        # --------------------------------------------------

        dice, iou, precision, recall = (
            calculate_metrics(
                prediction,
                ground_truth
            )
        )

        predicted_pixels = int(
            prediction.sum()
        )

        predicted_percentage = (
            100
            * predicted_pixels
            / prediction.size
        )

        max_probability = float(
            probability.max()
        )

        print(
            f"  Predicted pixels : "
            f"{predicted_pixels:,}"
        )

        print(
            f"  Predicted area   : "
            f"{predicted_percentage:.4f}%"
        )

        print(
            f"  Max probability  : "
            f"{max_probability:.4f}"
        )

        if category == "oil":

            print(
                f"  Dice             : "
                f"{dice:.4f}"
            )

            print(
                f"  IoU              : "
                f"{iou:.4f}"
            )

            print(
                f"  Precision        : "
                f"{precision:.4f}"
            )

            print(
                f"  Recall           : "
                f"{recall:.4f}"
            )

        # --------------------------------------------------
        # Column 1: SAR
        # --------------------------------------------------

        axes[row, 0].imshow(
            vv_display,
            cmap="gray"
        )

        axes[row, 0].set_title(
            f"{category.upper()} {scene_id}\n"
            "Sentinel-1 VV"
        )

        axes[row, 0].axis("off")

        # --------------------------------------------------
        # Column 2: Prediction
        # --------------------------------------------------

        axes[row, 1].imshow(
            vv_display,
            cmap="gray"
        )

        axes[row, 1].imshow(
            prediction,
            alpha=0.45
        )

        axes[row, 1].set_title(
            f"U-Net Prediction\n"
            f"Predicted: {predicted_percentage:.3f}%"
        )

        axes[row, 1].axis("off")

        # --------------------------------------------------
        # Column 3: Ground truth
        # --------------------------------------------------

        axes[row, 2].imshow(
            vv_display,
            cmap="gray"
        )

        axes[row, 2].imshow(
            ground_truth,
            alpha=0.45
        )

        axes[row, 2].set_title(
            "Ground Truth"
        )

        axes[row, 2].axis("off")

    fig.suptitle(
        "Sentinel-1 Oil Spill Segmentation Validation",
        fontsize=18
    )

    plt.tight_layout()

    fig.savefig(
        OUTPUT_PATH,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(
        f"\nSaved visualization:\n"
        f"{OUTPUT_PATH.resolve()}"
    )


if __name__ == "__main__":
    main()