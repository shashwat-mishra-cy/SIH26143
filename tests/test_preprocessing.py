import numpy as np

from satellite.preprocessing.sar import (
    read_sar_image,
    normalize_sar,
    read_mask,
)


IMAGE_PATH = r"C:\SIH-Main-Project\SIH26143_DATA\working\oil_image\00000.tif"
MASK_PATH = r"C:\SIH-Main-Project\SIH26143_DATA\working\oil_mask\00000.tif"


def test_preprocessing():
    image, metadata = read_sar_image(IMAGE_PATH)
    mask = read_mask(MASK_PATH)

    print("IMAGE")
    print("Shape:", image.shape)
    print("Dtype:", image.dtype)

    print("\nMETADATA")
    print("CRS:", metadata["crs"])
    print("Bounds:", metadata["bounds"])

    print("\nMASK")
    print("Shape:", mask.shape)
    print("Unique:", np.unique(mask))

    normalized = normalize_sar(image)

    print("\nNORMALIZED IMAGE")
    print("Shape:", normalized.shape)
    print("Dtype:", normalized.dtype)

    for i, name in enumerate(["VV", "VH"]):
        print(
            f"{name}: "
            f"min={normalized[i].min():.4f}, "
            f"max={normalized[i].max():.4f}, "
            f"mean={normalized[i].mean():.4f}"
        )

    assert image.shape == (2, 2048, 2048)
    assert mask.shape == (2048, 2048)
    assert set(np.unique(mask)).issubset({0.0, 1.0})
    assert np.isfinite(normalized).all()
    assert normalized.min() >= 0.0
    assert normalized.max() <= 1.0

    print("\nPreprocessing test PASSED.")
