from collections import Counter

from satellite.preprocessing.dataset import SARPatchDataset


IMAGE_DIR = (
    r"C:\SIH-Main-Project\SIH26143_DATA"
    r"\working\oil_image"
)

MASK_DIR = (
    r"C:\SIH-Main-Project\SIH26143_DATA"
    r"\working\oil_mask"
)


def test_dataset():
    dataset = SARPatchDataset(
    categories={
        "oil": (
            IMAGE_DIR,
            MASK_DIR,
        )
    },
    patch_size=256,
    patches_per_image=16,
    positive_fraction=0.5,
)

    print("Dataset size:", len(dataset))

    first = dataset[0]

    print("\nFIRST SAMPLE")
    print("Image shape:", first["image"].shape)
    print("Mask shape:", first["mask"].shape)
    print("Image ID:", first["image_id"])
    print("Contains oil:", first["contains_oil"])
    print("Patch position:", first["x"], first["y"])

    counts = Counter(
        sample["contains_oil"]
        for sample in dataset.samples
    )

    print("\nPATCH BALANCE")
    print("Oil-containing patches:", counts[True])
    print("Background patches:", counts[False])

    assert first["image"].shape == (2, 256, 256)
    assert first["mask"].shape == (1, 256, 256)

    print("\nDataset test PASSED.")
