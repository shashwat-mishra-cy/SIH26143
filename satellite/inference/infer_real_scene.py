from pathlib import Path
import sys

import numpy as np
import torch
import rasterio

from satellite.model.unet import UNet
from satellite.preprocessing.sar import normalize_sar


PATCH_SIZE = 256
BATCH_SIZE = 16
THRESHOLD = 0.30

MODEL_PATH = Path("best_unet_augmented.pth")


def load_model(model_path, device):

    model = UNet(
        in_channels=2,
        out_channels=1,
    )

    checkpoint = torch.load(
        model_path,
        map_location=device,
        weights_only=True,
    )

    model.load_state_dict(checkpoint)

    model.to(device)
    model.eval()

    return model


def load_scene(image_path):

    image_path = Path(image_path)

    with rasterio.open(image_path) as src:

        image = src.read().astype(np.float32)

        metadata = {
            "crs": src.crs,
            "transform": src.transform,
            "bounds": src.bounds,
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "tags": src.tags(),
        }

    if image.shape[0] != 2:

        raise ValueError(
            f"Expected exactly 2 bands "
            f"(VV/VH), got {image.shape[0]}"
        )

    if metadata["crs"] is None:

        raise ValueError(
            "This image has no CRS/geographic "
            "reference information."
        )

    return image, metadata


def run_full_scene(
    model,
    image,
    device,
):

    _, height, width = image.shape

    if height % PATCH_SIZE != 0:

        raise ValueError(
            f"Scene height {height} is not divisible "
            f"by {PATCH_SIZE}"
        )

    if width % PATCH_SIZE != 0:

        raise ValueError(
            f"Scene width {width} is not divisible "
            f"by {PATCH_SIZE}"
        )

    probability_map = np.zeros(
        (height, width),
        dtype=np.float32,
    )

    patches = []
    positions = []

    for y in range(
        0,
        height,
        PATCH_SIZE,
    ):

        for x in range(
            0,
            width,
            PATCH_SIZE,
        ):

            patch = image[
                :,
                y:y + PATCH_SIZE,
                x:x + PATCH_SIZE,
            ]

            patches.append(patch)
            positions.append((y, x))

    print(
        f"Scene size: {height}x{width}"
    )

    print(
        f"Total patches: {len(patches)}"
    )

    for start in range(
        0,
        len(patches),
        BATCH_SIZE,
    ):

        batch_patches = np.stack(
            patches[
                start:start + BATCH_SIZE
            ]
        )

        batch = torch.from_numpy(
            batch_patches
        ).float().to(device)

        with torch.no_grad():

            logits = model(batch)

            probabilities = torch.sigmoid(
                logits
            )

        probabilities = (
            probabilities[:, 0]
            .cpu()
            .numpy()
        )

        for i, probability in enumerate(
            probabilities
        ):

            y, x = positions[
                start + i
            ]

            probability_map[
                y:y + PATCH_SIZE,
                x:x + PATCH_SIZE,
            ] = probability

    return probability_map


def extract_timestamp(metadata):

    tags = metadata["tags"]

    possible_keys = [
        "ACQUISITION_DATETIME",
        "ACQUISITION_DATE",
        "DATETIME",
        "DATE_TIME",
        "TIMESTAMP",
        "PRODUCT_START_TIME",
    ]

    for key in possible_keys:

        if key in tags:

            return tags[key], "satellite_metadata"

    return None, "unavailable"


def main():

    if len(sys.argv) != 2:

        raise SystemExit(
            "\nUsage:\n"
            "python -m satellite.inference.infer_real_scene "
            "<image_path>\n"
        )

    image_path = Path(
        sys.argv[1]
    )

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        f"Device: {device}"
    )

    if device.type == "cuda":

        print(
            f"GPU: "
            f"{torch.cuda.get_device_name(0)}"
        )

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    print(
        f"\nLoading model:\n{MODEL_PATH}"
    )

    model = load_model(
        MODEL_PATH,
        device,
    )

    print(
        "Model loaded successfully."
    )

    print(
        f"\nLoading Sentinel-1 scene:\n"
        f"{image_path}"
    )

    image, metadata = load_scene(
        image_path
    )

    print(
        f"Image shape: {image.shape}"
    )

    print(
        f"CRS: {metadata['crs']}"
    )

    print(
        f"Bounds: {metadata['bounds']}"
    )

    timestamp, provenance = (
        extract_timestamp(metadata)
    )

    print(
        f"Timestamp: "
        f"{timestamp if timestamp else 'Unavailable'}"
    )

    print(
        f"Timestamp provenance: {provenance}"
    )

    normalized = normalize_sar(
        image
    )

    print(
        "SAR normalization complete."
    )

    probability_map = run_full_scene(
        model=model,
        image=normalized,
        device=device,
    )

    binary_mask = (
        probability_map >= THRESHOLD
    ).astype(np.uint8)

    predicted_pixels = int(
        binary_mask.sum()
    )

    total_pixels = binary_mask.size

    percentage = (
        100.0
        * predicted_pixels
        / total_pixels
    )

    print("\n" + "=" * 60)
    print("REAL SCENE INFERENCE")
    print("=" * 60)

    print(
        f"Scene                 : "
        f"{image_path.stem}"
    )

    print(
        f"Threshold             : "
        f"{THRESHOLD:.2f}"
    )

    print(
        f"Maximum probability   : "
        f"{probability_map.max():.4f}"
    )

    print(
        f"Mean probability      : "
        f"{probability_map.mean():.4f}"
    )

    print(
        f"Predicted oil pixels  : "
        f"{predicted_pixels:,}"
    )

    print(
        f"Predicted image area  : "
        f"{percentage:.4f}%"
    )

    print(
        f"CRS                   : "
        f"{metadata['crs']}"
    )

    print(
        f"Timestamp             : "
        f"{timestamp if timestamp else 'Unavailable'}"
    )

    print(
        f"Timestamp provenance  : "
        f"{provenance}"
    )

    print("=" * 60)

    output_dir = Path(
        "real_scene_output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    mask_path = (
        output_dir
        / f"{image_path.stem}_oil_mask.npy"
    )

    probability_path = (
        output_dir
        / f"{image_path.stem}_oil_probability.npy"
    )

    np.save(
        mask_path,
        binary_mask,
    )

    np.save(
        probability_path,
        probability_map,
    )

    print(
        f"\nSaved oil mask:\n{mask_path}"
    )

    print(
        f"\nSaved probability map:\n"
        f"{probability_path}"
    )

    print(
        "\nNext step:"
    )

    print(
        "Pass the binary mask + georeferenced "
        "metadata to the P1 geographic geometry "
        "pipeline to generate the SpillResult JSON."
    )


if __name__ == "__main__":
    main()