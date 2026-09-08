from pathlib import Path

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset

from satellite.preprocessing.sar import normalize_sar


class SARPatchDataset(Dataset):
    """
    Patch-based Sentinel-1 SAR segmentation dataset.

    Categories:
        oil       -> positive segmentation samples
        lookalike -> negative segmentation samples
        no_oil    -> negative segmentation samples

    scene_ids can be supplied to ensure that train and validation
    contain completely separate SAR scenes.
    """

    def __init__(
        self,
        categories,
        scene_ids=None,
        patch_size=256,
        patches_per_image=16,
        positive_fraction=0.5,
        min_positive_pixels=20,
    ):
        self.categories = categories
        self.scene_ids = scene_ids

        self.patch_size = patch_size
        self.patches_per_image = patches_per_image
        self.positive_fraction = positive_fraction
        self.min_positive_pixels = min_positive_pixels

        self.samples = self._build_samples()

    def _build_samples(self):
        samples = []

        rng = np.random.default_rng(42)

        for category, directories in self.categories.items():

            image_dir = Path(directories[0])
            mask_dir = Path(directories[1])

            image_paths = sorted(image_dir.glob("*.tif"))

            if self.scene_ids is not None:
                image_paths = [
                    path
                    for path in image_paths
                    if path.stem in self.scene_ids.get(category, [])
                ]

            if not image_paths:
                raise RuntimeError(
                    f"No matching TIFF images found for category "
                    f"'{category}'"
                )

            for image_path in image_paths:

                image_id = image_path.stem
                mask_path = mask_dir / f"{image_id}.tif"

                if not mask_path.exists():
                    raise FileNotFoundError(
                        f"Missing mask for {category} image "
                        f"{image_id}: {mask_path}"
                    )

                with rasterio.open(mask_path) as src:
                    mask = src.read(1)

                mask = (mask > 0).astype(np.uint8)

                height, width = mask.shape

                if height < self.patch_size or width < self.patch_size:
                    raise ValueError(
                        f"Image {image_id} is smaller than patch size"
                    )

                positive_positions = []
                negative_positions = []

                stride = self.patch_size

                for y in range(
                    0,
                    height - self.patch_size + 1,
                    stride,
                ):
                    for x in range(
                        0,
                        width - self.patch_size + 1,
                        stride,
                    ):
                        patch_mask = mask[
                            y:y + self.patch_size,
                            x:x + self.patch_size,
                        ]

                        positive_pixels = int(
                            patch_mask.sum()
                        )

                        if positive_pixels >= self.min_positive_pixels:
                            positive_positions.append((x, y))
                        else:
                            negative_positions.append((x, y))

                if category == "oil":

                    requested_positive = int(
                        self.patches_per_image
                        * self.positive_fraction
                    )

                    requested_negative = (
                        self.patches_per_image
                        - requested_positive
                    )

                    if positive_positions:

                        count = min(
                            requested_positive,
                            len(positive_positions),
                        )

                        indices = rng.choice(
                            len(positive_positions),
                            size=count,
                            replace=False,
                        )

                        for index in indices:

                            x, y = positive_positions[index]

                            samples.append({
                                "image_path": image_path,
                                "mask_path": mask_path,
                                "image_id": image_id,
                                "category": category,
                                "x": x,
                                "y": y,
                                "contains_oil": True,
                            })

                    if negative_positions:

                        count = min(
                            requested_negative,
                            len(negative_positions),
                        )

                        indices = rng.choice(
                            len(negative_positions),
                            size=count,
                            replace=False,
                        )

                        for index in indices:

                            x, y = negative_positions[index]

                            samples.append({
                                "image_path": image_path,
                                "mask_path": mask_path,
                                "image_id": image_id,
                                "category": category,
                                "x": x,
                                "y": y,
                                "contains_oil": False,
                            })

                else:

                    count = min(
                        self.patches_per_image,
                        len(negative_positions),
                    )

                    if count == 0:
                        continue

                    indices = rng.choice(
                        len(negative_positions),
                        size=count,
                        replace=False,
                    )

                    for index in indices:

                        x, y = negative_positions[index]

                        samples.append({
                            "image_path": image_path,
                            "mask_path": mask_path,
                            "image_id": image_id,
                            "category": category,
                            "x": x,
                            "y": y,
                            "contains_oil": False,
                        })

        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):

        sample = self.samples[index]

        x = sample["x"]
        y = sample["y"]

        with rasterio.open(sample["image_path"]) as src:
            image = src.read().astype(np.float32)

        image = normalize_sar(image)

        with rasterio.open(sample["mask_path"]) as src:
            mask = src.read(1)

        mask = (mask > 0).astype(np.float32)

        image = image[
            :,
            y:y + self.patch_size,
            x:x + self.patch_size,
        ]

        mask = mask[
            y:y + self.patch_size,
            x:x + self.patch_size,
        ]

        image = torch.from_numpy(image.copy()).float()
        mask = torch.from_numpy(mask.copy()).float().unsqueeze(0)

        return {
            "image": image,
            "mask": mask,
            "image_id": sample["image_id"],
            "category": sample["category"],
            "contains_oil": sample["contains_oil"],
            "x": x,
            "y": y,
        }