from satellite.training.split import split_scene_ids


BASE = r"C:\SIH-Main-Project\SIH26143_DATA\working"


CATEGORIES = {
    "oil": rf"{BASE}\oil_image",
    "lookalike": rf"{BASE}\lookalike_image",
    "no_oil": rf"{BASE}\no_oil_image",
}


def test_split():

    for category, image_dir in CATEGORIES.items():

        train_ids, validation_ids = split_scene_ids(
            image_dir,
            validation_fraction=0.2,
            seed=42,
        )

        print(f"\n{category.upper()}")

        print("Train:", train_ids)
        print("Validation:", validation_ids)

        assert len(train_ids) == 8
        assert len(validation_ids) == 2

        assert set(train_ids).isdisjoint(
            validation_ids
        )

        assert set(train_ids) | set(validation_ids) == {
            path.stem
            for path in __import__("pathlib")
            .Path(image_dir)
            .glob("*.tif")
        }

    print("\nScene-level split test PASSED.")
