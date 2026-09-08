from pathlib import Path

import numpy as np
import rasterio


DATA_ROOT = Path(
    r"C:\SIH-Main-Project\SIH26143_DATA\working"
)

CATEGORIES = {
    "oil": (
        DATA_ROOT / "oil_image",
        DATA_ROOT / "oil_mask",
    ),
    "lookalike": (
        DATA_ROOT / "lookalike_image",
        DATA_ROOT / "lookalike_mask",
    ),
    "no_oil": (
        DATA_ROOT / "no_oil_image",
        DATA_ROOT / "no_oil_mask",
    ),
}

# These are the validation scenes produced by our scene-level split.
VALIDATION_IDS = {
    "oil": ["00009", "00010"],
    "lookalike": ["00005", "00006"],
    "no_oil": ["00005", "00006"],
}

THRESHOLDS = [0.50, 0.40, 0.30, 0.25, 0.20, 0.15]


def load_probability(scene_id):
    """
    Load the already-generated full-scene probability map.

    Currently we have generated scene 00009.
    Other validation scenes will be inferred automatically
    by the next step of this script.
    """
    path = Path(
        f"full_scene_{scene_id}_probability.npy"
    )

    if not path.exists():
        return None

    return np.load(path)


def load_ground_truth(mask_path):
    with rasterio.open(mask_path) as src:
        mask = src.read(1)

    return mask > 0


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

    tn = np.logical_and(
        ~prediction,
        ~ground_truth
    ).sum()

    dice = (
        2.0 * tp
        / (2.0 * tp + fp + fn + 1e-8)
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

    return {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "dice": dice,
        "iou": iou,
        "precision": precision,
        "recall": recall,
    }


def main():

    print("=" * 80)
    print("VALIDATION THRESHOLD SWEEP")
    print("=" * 80)

    print("\nValidation scenes:")

    for category, ids in VALIDATION_IDS.items():
        print(
            f"  {category:10s}: "
            + ", ".join(ids)
        )

    print(
        "\nFirst we need full-scene probability maps "
        "for every validation scene."
    )

    missing = []

    for category, ids in VALIDATION_IDS.items():
        for scene_id in ids:

            probability_path = Path(
                f"full_scene_{scene_id}_probability.npy"
            )

            if not probability_path.exists():
                missing.append(
                    (category, scene_id)
                )

    if missing:

        print("\nMissing probability maps:")

        for category, scene_id in missing:
            print(
                f"  {category:10s} {scene_id}"
            )

        print(
            "\nWe already have 00009. "
            "Run full-scene inference for the missing "
            "validation scenes before running this sweep."
        )

        return

    print("\nAll validation probability maps found.")

    aggregate = {
        threshold: {
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
        }
        for threshold in THRESHOLDS
    }

    category_results = {}

    for category, ids in VALIDATION_IDS.items():

        category_results[category] = {}

        for threshold in THRESHOLDS:

            category_results[category][threshold] = {
                "tp": 0,
                "fp": 0,
                "fn": 0,
                "tn": 0,
            }

        for scene_id in ids:

            probability = load_probability(scene_id)

            _, mask_dir = CATEGORIES[category]

            ground_truth = load_ground_truth(
                mask_dir / f"{scene_id}.tif"
            )

            for threshold in THRESHOLDS:

                prediction = probability >= threshold

                metrics = calculate_metrics(
                    prediction,
                    ground_truth
                )

                for key in ["tp", "fp", "fn", "tn"]:

                    aggregate[threshold][key] += (
                        metrics[key]
                    )

                    category_results[
                        category
                    ][threshold][key] += (
                        metrics[key]
                    )

    print("\n" + "=" * 80)
    print("AGGREGATE VALIDATION RESULTS")
    print("=" * 80)

    print(
        f"{'Threshold':>10} "
        f"{'Dice':>10} "
        f"{'IoU':>10} "
        f"{'Precision':>12} "
        f"{'Recall':>10}"
    )

    print("-" * 80)

    best_threshold = None
    best_dice = -1

    for threshold in THRESHOLDS:

        result = aggregate[threshold]

        tp = result["tp"]
        fp = result["fp"]
        fn = result["fn"]

        dice = (
            2.0 * tp
            / (2.0 * tp + fp + fn + 1e-8)
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

        print(
            f"{threshold:>10.2f} "
            f"{dice:>10.4f} "
            f"{iou:>10.4f} "
            f"{precision:>12.4f} "
            f"{recall:>10.4f}"
        )

        if dice > best_dice:
            best_dice = dice
            best_threshold = threshold

    print("\n" + "=" * 80)
    print("BEST AGGREGATE THRESHOLD")
    print("=" * 80)

    print(
        f"Threshold: {best_threshold:.2f}"
    )
    print(
        f"Dice:      {best_dice:.4f}"
    )

    print("\n" + "=" * 80)
    print("CATEGORY ANALYSIS")
    print("=" * 80)

    for category in VALIDATION_IDS:

        print(f"\n[{category.upper()}]")

        for threshold in THRESHOLDS:

            result = category_results[
                category
            ][threshold]

            tp = result["tp"]
            fp = result["fp"]
            fn = result["fn"]

            predicted_pixels = tp + fp
            actual_pixels = tp + fn

            if actual_pixels == 0:

                # For negative scenes, we care primarily
                # about false-positive area.
                false_positive_rate = (
                    predicted_pixels
                    / (predicted_pixels + 1e-8)
                )

                print(
                    f"  threshold={threshold:.2f} "
                    f"predicted_pixels={predicted_pixels:,}"
                )

            else:

                dice = (
                    2.0 * tp
                    / (2.0 * tp + fp + fn + 1e-8)
                )

                precision = (
                    tp
                    / (tp + fp + 1e-8)
                )

                recall = (
                    tp
                    / (tp + fn + 1e-8)
                )

                print(
                    f"  threshold={threshold:.2f} "
                    f"Dice={dice:.4f} "
                    f"Precision={precision:.4f} "
                    f"Recall={recall:.4f}"
                )


if __name__ == "__main__":
    main()