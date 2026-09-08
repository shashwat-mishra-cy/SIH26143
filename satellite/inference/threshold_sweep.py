from pathlib import Path

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

THRESHOLDS = [
    0.50,
    0.40,
    0.30,
    0.25,
    0.20,
    0.15,
]


def load_ground_truth(category, scene_id):
    mask_path = (
        DATA_ROOT
        / f"{category}_mask"
        / f"{scene_id}.tif"
    )

    with rasterio.open(mask_path) as src:
        mask = src.read(1)

    return mask > 0


def load_probability(category, scene_id):
    path = Path(
        f"full_scene_{category}_{scene_id}_probability.npy"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing probability map:\n{path}"
        )

    return np.load(path)


def calculate_metrics(prediction, ground_truth):
    prediction = prediction.astype(bool)
    ground_truth = ground_truth.astype(bool)

    tp = np.logical_and(
        prediction,
        ground_truth,
    ).sum()

    fp = np.logical_and(
        prediction,
        ~ground_truth,
    ).sum()

    fn = np.logical_and(
        ~prediction,
        ground_truth,
    ).sum()

    tn = np.logical_and(
        ~prediction,
        ~ground_truth,
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

    predicted_pixels = int(
        prediction.sum()
    )

    total_pixels = prediction.size

    predicted_area_percent = (
        100.0
        * predicted_pixels
        / total_pixels
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
        "predicted_pixels": predicted_pixels,
        "predicted_area_percent": predicted_area_percent,
    }


def main():

    print("=" * 90)
    print("6-SCENE VALIDATION THRESHOLD SWEEP")
    print("=" * 90)

    # ---------------------------------------------------------
    # Verify all probability maps exist
    # ---------------------------------------------------------

    print("\nChecking probability maps...")

    for category, scene_id in SCENES:

        path = Path(
            f"full_scene_{category}_{scene_id}_probability.npy"
        )

        if not path.exists():

            raise FileNotFoundError(
                f"\nMissing:\n{path}\n\n"
                f"Run full-scene inference for this scene first."
            )

        print(
            f"  OK  {category:10s} {scene_id}"
        )

    # ---------------------------------------------------------
    # Load all scenes once
    # ---------------------------------------------------------

    loaded_scenes = []

    print("\nLoading validation scenes...")

    for category, scene_id in SCENES:

        probability = load_probability(
            category,
            scene_id,
        )

        ground_truth = load_ground_truth(
            category,
            scene_id,
        )

        loaded_scenes.append(
            {
                "category": category,
                "scene_id": scene_id,
                "probability": probability,
                "ground_truth": ground_truth,
            }
        )

    # ---------------------------------------------------------
    # Per-scene results
    # ---------------------------------------------------------

    print("\n" + "=" * 90)
    print("PER-SCENE RESULTS")
    print("=" * 90)

    best_oil_threshold = None
    best_oil_dice = -1.0

    for threshold in THRESHOLDS:

        print(
            f"\n{'=' * 20} "
            f"THRESHOLD {threshold:.2f} "
            f"{'=' * 20}"
        )

        for scene in loaded_scenes:

            category = scene["category"]
            scene_id = scene["scene_id"]

            prediction = (
                scene["probability"]
                >= threshold
            )

            metrics = calculate_metrics(
                prediction,
                scene["ground_truth"],
            )

            if category == "oil":

                print(
                    f"{category:10s} {scene_id} | "
                    f"Dice={metrics['dice']:.4f} | "
                    f"IoU={metrics['iou']:.4f} | "
                    f"Precision={metrics['precision']:.4f} | "
                    f"Recall={metrics['recall']:.4f} | "
                    f"Area={metrics['predicted_area_percent']:.3f}%"
                )

            else:

                print(
                    f"{category:10s} {scene_id} | "
                    f"Predicted={metrics['predicted_pixels']:,} px | "
                    f"Area={metrics['predicted_area_percent']:.3f}% | "
                    f"MaxProb={scene['probability'].max():.4f}"
                )

    # ---------------------------------------------------------
    # Aggregate oil performance
    # ---------------------------------------------------------

    print("\n" + "=" * 90)
    print("AGGREGATE OIL VALIDATION")
    print("=" * 90)

    print(
        f"{'Threshold':>10} "
        f"{'Dice':>10} "
        f"{'IoU':>10} "
        f"{'Precision':>12} "
        f"{'Recall':>10} "
        f"{'Pred Area':>12}"
    )

    print("-" * 90)

    oil_scenes = [
        scene
        for scene in loaded_scenes
        if scene["category"] == "oil"
    ]

    for threshold in THRESHOLDS:

        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_predicted = 0
        total_pixels = 0

        for scene in oil_scenes:

            prediction = (
                scene["probability"]
                >= threshold
            )

            metrics = calculate_metrics(
                prediction,
                scene["ground_truth"],
            )

            total_tp += metrics["tp"]
            total_fp += metrics["fp"]
            total_fn += metrics["fn"]
            total_predicted += (
                metrics["predicted_pixels"]
            )
            total_pixels += prediction.size

        dice = (
            2.0 * total_tp
            / (
                2.0 * total_tp
                + total_fp
                + total_fn
                + 1e-8
            )
        )

        iou = (
            total_tp
            / (
                total_tp
                + total_fp
                + total_fn
                + 1e-8
            )
        )

        precision = (
            total_tp
            / (
                total_tp
                + total_fp
                + 1e-8
            )
        )

        recall = (
            total_tp
            / (
                total_tp
                + total_fn
                + 1e-8
            )
        )

        predicted_area = (
            100.0
            * total_predicted
            / total_pixels
        )

        print(
            f"{threshold:>10.2f} "
            f"{dice:>10.4f} "
            f"{iou:>10.4f} "
            f"{precision:>12.4f} "
            f"{recall:>10.4f} "
            f"{predicted_area:>11.3f}%"
        )

        if dice > best_oil_dice:

            best_oil_dice = dice
            best_oil_threshold = threshold

    # ---------------------------------------------------------
    # Negative scene false-positive analysis
    # ---------------------------------------------------------

    print("\n" + "=" * 90)
    print("LOOK-ALIKE / NO-OIL FALSE-POSITIVE ANALYSIS")
    print("=" * 90)

    negative_scenes = [
        scene
        for scene in loaded_scenes
        if scene["category"] != "oil"
    ]

    print(
        f"{'Threshold':>10} "
        f"{'Look-Alike Avg Area':>22} "
        f"{'No-Oil Avg Area':>20} "
        f"{'Max Negative Area':>20}"
    )

    print("-" * 90)

    for threshold in THRESHOLDS:

        lookalike_areas = []
        no_oil_areas = []

        for scene in negative_scenes:

            prediction = (
                scene["probability"]
                >= threshold
            )

            predicted_area = (
                100.0
                * prediction.sum()
                / prediction.size
            )

            if scene["category"] == "lookalike":
                lookalike_areas.append(
                    predicted_area
                )
            else:
                no_oil_areas.append(
                    predicted_area
                )

        lookalike_avg = (
            np.mean(lookalike_areas)
        )

        no_oil_avg = (
            np.mean(no_oil_areas)
        )

        max_negative = max(
            lookalike_areas
            + no_oil_areas
        )

        print(
            f"{threshold:>10.2f} "
            f"{lookalike_avg:>21.3f}% "
            f"{no_oil_avg:>19.3f}% "
            f"{max_negative:>19.3f}%"
        )

    # ---------------------------------------------------------
    # Final recommendation
    # ---------------------------------------------------------

    print("\n" + "=" * 90)
    print("THRESHOLD DECISION")
    print("=" * 90)

    print(
        f"Best oil Dice threshold: "
        f"{best_oil_threshold:.2f}"
    )

    print(
        f"Best aggregate oil Dice: "
        f"{best_oil_dice:.4f}"
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "This threshold is selected using the "
        "development validation scenes only."
    )

    print(
        "It must NOT be treated as the final "
        "test-set performance."
    )

    print(
        "\nNext step:"
    )

    print(
        "Use the chosen threshold for geometry extraction "
        "and inspect whether the predicted regions are "
        "physically plausible."
    )


if __name__ == "__main__":
    main()