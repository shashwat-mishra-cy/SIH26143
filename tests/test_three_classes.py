from pathlib import Path

import numpy as np
import rasterio


BASE = Path(
    r"C:\SIH-Main-Project\SIH26143_DATA\working"
)

CATEGORIES = {
    "oil": BASE / "oil_mask",
    "lookalike": BASE / "lookalike_mask",
    "no_oil": BASE / "no_oil_mask",
}


def inspect_category(name, directory):
    print(f"\n{name.upper()}")

    mask_paths = sorted(directory.glob("*.tif"))

    print("Masks:", len(mask_paths))

    total_positive = 0

    for path in mask_paths:
        with rasterio.open(path) as src:
            mask = src.read(1)

        unique = np.unique(mask)
        positive = int((mask > 0).sum())

        total_positive += positive

        print(
            f"{path.stem}: "
            f"shape={mask.shape}, "
            f"unique={unique.tolist()}, "
            f"positive_pixels={positive}"
        )

    print("Total positive pixels:", total_positive)

    return total_positive


def test_three_classes():
    oil_positive = inspect_category(
        "oil",
        CATEGORIES["oil"],
    )

    lookalike_positive = inspect_category(
        "lookalike",
        CATEGORIES["lookalike"],
    )

    no_oil_positive = inspect_category(
        "no_oil",
        CATEGORIES["no_oil"],
    )

    assert oil_positive > 0, (
        "Oil masks unexpectedly contain no positive pixels."
    )

    assert lookalike_positive == 0, (
        "Look-alike masks contain positive pixels."
    )

    assert no_oil_positive == 0, (
        "No-oil masks contain positive pixels."
    )

    print("\nThree-class mask verification PASSED.")
