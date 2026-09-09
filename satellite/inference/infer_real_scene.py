from pathlib import Path
import sys

import numpy as np
import torch
import rasterio

from satellite.model.unet import UNet
from satellite.preprocessing.sar import normalize_sar
from satellite.geometry.geographic_geometry import (
    extract_geographic_geometry,
)
from satellite.integration.spill_result import (
    build_spill_result,
    save_spill_result,
)


PATCH_SIZE = 256
BATCH_SIZE = 16

# Experiment 1 operating threshold
THRESHOLD = 0.30
MIN_PIXELS = 50

MODEL_PATH = Path("best_unet_augmented.pth")
OUTPUT_DIR = Path("real_scene_output")


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
            f"Expected VV/VH two-band SAR image. "
            f"Got {image.shape[0]} bands."
        )

    if metadata["crs"] is None:
        raise ValueError(
            "Input GeoTIFF has no CRS. "
            "A georeferenced Sentinel-1 GeoTIFF is required."
        )

    return image, metadata


def run_full_scene(model, image, device):
    _, height, width = image.shape

    probability_map = np.zeros(
        (height, width),
        dtype=np.float32,
    )

    patches = []
    positions = []

    # Process arbitrary scene sizes.
    # Edge patches are zero-padded to 256 x 256.
    for y in range(0, height, PATCH_SIZE):

        for x in range(0, width, PATCH_SIZE):

            patch = image[
                :,
                y:min(y + PATCH_SIZE, height),
                x:min(x + PATCH_SIZE, width),
            ]

            original_h = patch.shape[1]
            original_w = patch.shape[2]

            padded = np.zeros(
                (2, PATCH_SIZE, PATCH_SIZE),
                dtype=np.float32,
            )

            padded[
                :,
                :original_h,
                :original_w,
            ] = patch

            patches.append(padded)

            positions.append(
                (
                    y,
                    x,
                    original_h,
                    original_w,
                )
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

            probabilities = torch.sigmoid(
                model(batch)
            )

        probabilities = (
            probabilities[:, 0]
            .cpu()
            .numpy()
        )

        for i, probability in enumerate(
            probabilities
        ):

            (
                y,
                x,
                original_h,
                original_w,
            ) = positions[start + i]

            probability_map[
                y:y + original_h,
                x:x + original_w,
            ] = probability[
                :original_h,
                :original_w,
            ]

    return probability_map


def extract_timestamp(metadata):
    tags = metadata.get(
        "tags",
        {},
    )

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
            return tags[key]

    return None


def main():

    if len(sys.argv) != 2:

        print(
            "Usage:\n"
            "python -m satellite.inference.infer_real_scene "
            "<path_to_georeferenced_sentinel1.tif>"
        )

        sys.exit(1)

    image_path = Path(
        sys.argv[1]
    )

    if not image_path.exists():

        raise FileNotFoundError(
            f"Input GeoTIFF not found:\n"
            f"{image_path.resolve()}"
        )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print()
    print("=" * 70)
    print("P1 SATELLITE OIL-SPILL INFERENCE")
    print("=" * 70)

    print(
        f"Input       : {image_path}"
    )

    print(
        f"Device      : {device}"
    )

    print(
        f"Model       : {MODEL_PATH}"
    )

    print(
        f"Threshold   : {THRESHOLD}"
    )

    print(
        f"Min pixels  : {MIN_PIXELS}"
    )

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Model checkpoint not found:\n"
            f"{MODEL_PATH.resolve()}"
        )

    # --------------------------------------------------------
    # Load Experiment 1 model
    # --------------------------------------------------------

    model = load_model(
        MODEL_PATH,
        device,
    )

    # --------------------------------------------------------
    # Load georeferenced Sentinel-1 SAR scene
    # --------------------------------------------------------

    image, metadata = load_scene(
        image_path
    )

    print()
    print(
        f"Scene size  : "
        f"{metadata['width']} x "
        f"{metadata['height']}"
    )

    print(
        f"Bands       : "
        f"{metadata['count']}"
    )

    print(
        f"CRS         : "
        f"{metadata['crs']}"
    )

    print(
        f"Bounds      : "
        f"{metadata['bounds']}"
    )

    timestamp = extract_timestamp(
        metadata
    )

    print(
        f"Timestamp   : "
        f"{timestamp if timestamp else 'Unavailable'}"
    )

    # --------------------------------------------------------
    # SAR preprocessing
    # --------------------------------------------------------

    normalized = normalize_sar(
        image
    )

    # --------------------------------------------------------
    # U-Net inference
    # --------------------------------------------------------

    print()
    print("Running U-Net inference...")

    probability_map = run_full_scene(
        model=model,
        image=normalized,
        device=device,
    )

    print(
        f"Probability range: "
        f"{probability_map.min():.4f} - "
        f"{probability_map.max():.4f}"
    )

    # --------------------------------------------------------
    # Geographic spill geometry
    # --------------------------------------------------------

    print()
    print(
        "Extracting geographic spill geometry..."
    )

    geometry_result = extract_geographic_geometry(
        probability_map=probability_map,
        transform=metadata["transform"],
        threshold=THRESHOLD,
        min_pixels=MIN_PIXELS,
    )

    # --------------------------------------------------------
    # Detection gate
    # --------------------------------------------------------

    if not geometry_result.get(
        "spill_detected",
        False,
    ):

        print()
        print("=" * 70)
        print("NO OIL SPILL DETECTED")
        print("=" * 70)

        print(
            "Attribution pipeline should stop."
        )

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        mask = (
            probability_map >= THRESHOLD
        ).astype(np.uint8)

        np.save(
            OUTPUT_DIR
            / f"{image_path.stem}_oil_mask.npy",
            mask,
        )

        np.save(
            OUTPUT_DIR
            / f"{image_path.stem}_oil_probability.npy",
            probability_map,
        )

        return

    # --------------------------------------------------------
    # Build P1 shared SpillResult
    # --------------------------------------------------------

    spill_result = build_spill_result(
        geometry_result=geometry_result,
        spill_id=image_path.stem,
    )

    # --------------------------------------------------------
    # Save outputs
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    mask = (
        probability_map >= THRESHOLD
    ).astype(np.uint8)

    mask_path = (
        OUTPUT_DIR
        / f"{image_path.stem}_oil_mask.npy"
    )

    probability_path = (
        OUTPUT_DIR
        / f"{image_path.stem}_oil_probability.npy"
    )

    result_path = (
        OUTPUT_DIR
        / f"{image_path.stem}_spill_result.json"
    )

    np.save(
        mask_path,
        mask,
    )

    np.save(
        probability_path,
        probability_map,
    )

    save_spill_result(
        spill_result,
        result_path,
    )

    # --------------------------------------------------------
    # Final P1 output
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("P1 SPILL DETECTED")
    print("=" * 70)

    print(
        f"Spill ID    : "
        f"{spill_result.spill_id}"
    )

    print(
        f"Centroid    : "
        f"{spill_result.centroid.latitude:.6f}, "
        f"{spill_result.centroid.longitude:.6f}"
    )

    print(
        f"Area        : "
        f"{spill_result.spill_area_km2:.6f} km2"
    )

    if spill_result.perimeter_km is not None:

        print(
            f"Perimeter   : "
            f"{spill_result.perimeter_km:.6f} km"
        )

    else:

        print(
            "Perimeter   : None"
        )

    print(
        f"Confidence  : "
        f"{spill_result.confidence:.4f}"
    )

    print(
        f"Timestamp   : "
        f"{spill_result.detection_timestamp}"
    )

    print(
        f"Provenance  : "
        f"{spill_result.timestamp_provenance}"
    )

    print(
        f"Geometry    : "
        f"{spill_result.geometry.get('type')}"
    )

    print()
    print("Saved:")

    print(
        f"  Mask        : "
        f"{mask_path.resolve()}"
    )

    print(
        f"  Probability : "
        f"{probability_path.resolve()}"
    )

    print(
        f"  SpillResult : "
        f"{result_path.resolve()}"
    )

    print()
    print(
        "P1 output is ready for downstream processing."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()