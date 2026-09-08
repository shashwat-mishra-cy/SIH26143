from pathlib import Path

import numpy as np
import rasterio


def read_sar_image(path):
    """
    Read a Sentinel-1 SAR TIFF.

    Expected format:
        Band 1 = VV
        Band 2 = VH

    Returns:
        image: numpy array with shape (2, H, W)
        metadata: raster metadata including CRS and transform
    """
    path = Path(path)

    with rasterio.open(path) as src:
        image = src.read().astype(np.float32)

        metadata = {
            "crs": src.crs,
            "transform": src.transform,
            "bounds": src.bounds,
            "width": src.width,
            "height": src.height,
        }

    if image.shape[0] != 2:
        raise ValueError(
            f"Expected 2 SAR bands (VV/VH), got {image.shape[0]}"
        )

    return image, metadata


def normalize_sar(image, lower_percentile=2, upper_percentile=98):
    """
    Robustly normalize each SAR channel independently.

    Sentinel-1 values in this dataset are already in dB, so we do
    not apply another logarithmic conversion.

    Each channel is clipped to its percentile range and scaled to [0, 1].
    """
    image = np.asarray(image, dtype=np.float32)

    if image.ndim != 3 or image.shape[0] != 2:
        raise ValueError(
            f"Expected image shape (2, H, W), got {image.shape}"
        )

    normalized = np.empty_like(image)

    for channel in range(image.shape[0]):
        band = image[channel]

        low = np.percentile(band, lower_percentile)
        high = np.percentile(band, upper_percentile)

        if high <= low:
            normalized[channel] = 0.0
            continue

        band = np.clip(band, low, high)
        normalized[channel] = (band - low) / (high - low)

    return normalized.astype(np.float32)


def read_mask(path):
    """
    Read a binary oil-spill mask.

    Returns:
        mask: numpy array with shape (H, W), values 0 or 1.
    """
    path = Path(path)

    with rasterio.open(path) as src:
        mask = src.read(1)

    mask = (mask > 0).astype(np.float32)

    return mask