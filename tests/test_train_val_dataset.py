from collections import Counter

from satellite.preprocessing.dataset import SARPatchDataset
from satellite.training.split import split_scene_ids


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


def test_train_val_dataset():

    train_ids = {}
    validation_ids = {}

    for category, directories in CATEGORIES.items():

        train, validation = split_scene_ids(
            directories[0],
            validation_fraction=0.2,
            seed=42,
        )

        train_ids[category] = train
        validation_ids[category] = validation

    train_dataset = SARPatchDataset(
        categories=CATEGORIES,
        scene_ids=train_ids,
        patch_size=256,
        patches_per_image=16,
        positive_fraction=0.5,
    )

    validation_dataset = SARPatchDataset(
        categories=CATEGORIES,
        scene_ids=validation_ids,
        patch_size=256,
        patches_per_image=16,
        positive_fraction=0.5,
    )

    print("TRAIN DATASET")
    print("Total patches:", len(train_dataset))

    print(
        Counter(
            sample["category"]
            for sample in train_dataset.samples
        )
    )

    print("\nVALIDATION DATASET")
    print("Total patches:", len(validation_dataset))

    print(
        Counter(
            sample["category"]
            for sample in validation_dataset.samples
        )
    )

    # Verify no scene appears in both datasets.
    for category in CATEGORIES:

        train_scene_set = set(train_ids[category])
        validation_scene_set = set(validation_ids[category])

        assert train_scene_set.isdisjoint(
            validation_scene_set
        )

    # Verify every validation sample belongs to validation scenes.
    for sample in validation_dataset.samples:

        assert sample["image_id"] in validation_ids[
            sample["category"]
        ]

    print("\nNo train/validation scene leakage detected.")

    print("\nTrain/validation Dataset test PASSED.")
