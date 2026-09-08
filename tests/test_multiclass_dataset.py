from collections import Counter

from satellite.preprocessing.dataset import SARPatchDataset


BASE = r"C:\SIH-Main-Project\SIH26143_DATA\working"


CATEGORIES = {
    "oil": (
        rf"{BASE}\oil_image",
        rf"{BASE}\oil_mask",
    ),

    "lookalike": (
        rf"{BASE}\lookalike_image",
        rf"{BASE}\lookalike_mask",
    ),

    "no_oil": (
        rf"{BASE}\no_oil_image",
        rf"{BASE}\no_oil_mask",
    ),
}


def test_multiclass_dataset():

    dataset = SARPatchDataset(
        categories=CATEGORIES,
        patch_size=256,
        patches_per_image=16,
        positive_fraction=0.5,
    )

    print("Total samples:", len(dataset))

    category_counts = Counter(
        sample["category"]
        for sample in dataset.samples
    )

    print("\nCATEGORY COUNTS")

    for category, count in category_counts.items():
        print(f"{category}: {count}")

    print("\nFIRST SAMPLES")

    for index in range(min(5, len(dataset))):

        sample = dataset[index]

        print(
            index,
            "| category:", sample["category"],
            "| image:", sample["image"].shape,
            "| mask:", sample["mask"].shape,
            "| oil:", sample["contains_oil"],
        )

    # Verify categories exist.
    assert "oil" in category_counts
    assert "lookalike" in category_counts
    assert "no_oil" in category_counts

    # Verify tensor shapes.
    sample = dataset[0]

    assert sample["image"].shape == (2, 256, 256)
    assert sample["mask"].shape == (1, 256, 256)

    print("\nMulti-category Dataset test PASSED.")
