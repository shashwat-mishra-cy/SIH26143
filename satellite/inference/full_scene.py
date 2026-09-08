from pathlib import Path
import sys

import numpy as np
import torch
import rasterio

from satellite.model.unet import UNet
from satellite.preprocessing.sar import normalize_sar


PATCH_SIZE = 256
BATCH_SIZE = 16
THRESHOLD = 0.5


def load_model(model_path, device):
    """Load the trained U-Net checkpoint."""

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


def run_full_scene(model, image, device):
    """
    Run U-Net over the complete SAR scene using
    non-overlapping 256x256 tiles.

    Input:
        image: numpy array with shape (2, H, W)

    Output:
        probability_map: numpy array with shape (H, W)
    """

    _, height, width = image.shape

    if height % PATCH_SIZE != 0:
        raise ValueError(
            f"Scene height {height} is not divisible by "
            f"patch size {PATCH_SIZE}"
        )

    if width % PATCH_SIZE != 0:
        raise ValueError(
            f"Scene width {width} is not divisible by "
            f"patch size {PATCH_SIZE}"
        )

    probability_map = np.zeros(
        (height, width),
        dtype=np.float32,
    )

    patches = []
    positions = []

    # Create all scene tiles.
    for y in range(0, height, PATCH_SIZE):
        for x in range(0, width, PATCH_SIZE):

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
        f"Patch size: {PATCH_SIZE}x{PATCH_SIZE}"
    )

    print(
        f"Total patches: {len(patches)}"
    )

    # Process patches in GPU batches.
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
        ).float()

        batch = batch.to(device)

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

        # Put each predicted tile back into
        # its original scene position.
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


def load_scene(image_path):
    """
    Load Sentinel-1 SAR scene and metadata.
    """

    image_path = Path(image_path)

    with rasterio.open(image_path) as src:

        image = src.read().astype(
            np.float32
        )

        metadata = {
            "crs": src.crs,
            "transform": src.transform,
            "bounds": src.bounds,
            "width": src.width,
            "height": src.height,
        }

    if image.shape[0] != 2:

        raise ValueError(
            f"Expected 2 SAR bands "
            f"(VV/VH), got {image.shape[0]}"
        )

    return image, metadata


def infer_scene(
    model,
    image_path,
    device,
    threshold=THRESHOLD,
):
    """
    Complete full-scene inference pipeline.

    Sentinel-1 SAR
        ↓
    normalization
        ↓
    tiled U-Net inference
        ↓
    probability map
        ↓
    binary mask
    """

    image_path = Path(image_path)

    print(
        f"\nLoading scene:\n{image_path}"
    )

    image, metadata = load_scene(
        image_path
    )

    print(
        f"Original image shape: "
        f"{image.shape}"
    )

    # Normalize the complete scene first.
    normalized = normalize_sar(
        image
    )

    print(
        "SAR normalization complete."
    )

    # Run tiled inference.
    probability_map = run_full_scene(
        model,
        normalized,
        device,
    )

    # Convert probabilities into binary mask.
    binary_mask = (
        probability_map >= threshold
    ).astype(np.uint8)

    return {
        "image_id": image_path.stem,
        "probability": probability_map,
        "mask": binary_mask,
        "metadata": metadata,
    }


def save_outputs(
    result,
    category,
    output_directory=Path("."),
):
    """
    Save probability map and binary mask.

    Category is included in the filename so that
    look-alike/00005 and no-oil/00005 cannot
    overwrite each other.
    """

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_id = result["image_id"]

    mask_path = (
        output_directory
        / f"full_scene_{category}_{image_id}_mask.npy"
    )

    probability_path = (
        output_directory
        / f"full_scene_{category}_{image_id}_probability.npy"
    )

    np.save(
        mask_path,
        result["mask"],
    )

    np.save(
        probability_path,
        result["probability"],
    )

    return mask_path, probability_path


def print_results(
    result,
    category,
    threshold,
):
    """Print useful full-scene inference statistics."""

    probability = result["probability"]
    mask = result["mask"]

    predicted_pixels = int(
        mask.sum()
    )

    total_pixels = mask.size

    predicted_percentage = (
        100.0
        * predicted_pixels
        / total_pixels
    )

    print("\n" + "=" * 60)
    print("FULL-SCENE INFERENCE RESULTS")
    print("=" * 60)

    print(
        f"Category              : {category}"
    )

    print(
        f"Scene                  : "
        f"{result['image_id']}"
    )

    print(
        f"Scene dimensions       : "
        f"{mask.shape[0]} x {mask.shape[1]}"
    )

    print(
        f"Threshold              : "
        f"{threshold:.2f}"
    )

    print(
        f"Maximum probability    : "
        f"{probability.max():.4f}"
    )

    print(
        f"Mean probability       : "
        f"{probability.mean():.4f}"
    )

    print(
        f"Predicted oil pixels   : "
        f"{predicted_pixels:,}"
    )

    print(
        f"Predicted oil area     : "
        f"{predicted_percentage:.4f}%"
    )

    print(
        f"CRS                    : "
        f"{result['metadata']['crs']}"
    )

    print(
        f"Bounds                 : "
        f"{result['metadata']['bounds']}"
    )

    print("=" * 60)


def main():

    # ---------------------------------------------------------
    # Command-line arguments
    #
    # Usage:
    #
    # python -m satellite.inference.full_scene \
    #     <image_path> <category>
    #
    # Example:
    #
    # python -m satellite.inference.full_scene \
    #     "...\\oil_image\\00009.tif" oil
    # ---------------------------------------------------------

    if len(sys.argv) != 3:

        raise SystemExit(
            "\nUsage:\n"
            "python -m satellite.inference.full_scene "
            "<image_path> <category>\n\n"
            "Categories:\n"
            "  oil\n"
            "  lookalike\n"
            "  no_oil\n"
        )

    image_path = Path(
        sys.argv[1]
    )

    category = sys.argv[2].lower()

    valid_categories = {
        "oil",
        "lookalike",
        "no_oil",
    }

    if category not in valid_categories:

        raise SystemExit(
            f"Invalid category '{category}'. "
            f"Choose from: "
            f"{', '.join(sorted(valid_categories))}"
        )

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    # ---------------------------------------------------------
    # Device
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Model
    # ---------------------------------------------------------

    model_path = Path(
        "best_unet.pth"
    )

    if not model_path.exists():

        raise FileNotFoundError(
            "Could not find best_unet.pth "
            "in the current directory."
        )

    model = load_model(
        model_path,
        device,
    )

    print(
        "Model loaded successfully."
    )

    # ---------------------------------------------------------
    # Inference
    # ---------------------------------------------------------

    result = infer_scene(
        model=model,
        image_path=image_path,
        device=device,
        threshold=THRESHOLD,
    )

    # ---------------------------------------------------------
    # Results
    # ---------------------------------------------------------

    print_results(
        result,
        category,
        THRESHOLD,
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    mask_path, probability_path = (
        save_outputs(
            result,
            category,
        )
    )

    print(
        f"\nSaved mask:"
        f"\n{mask_path}"
    )

    print(
        f"\nSaved probability map:"
        f"\n{probability_path}"
    )


if __name__ == "__main__":
    main()