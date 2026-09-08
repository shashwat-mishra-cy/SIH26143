from pathlib import Path

import numpy as np


def split_scene_ids(
    image_dir,
    validation_fraction=0.2,
    seed=42,
):
    """
    Split scene IDs into train and validation sets.

    The split happens at scene level, not patch level.
    """

    image_dir = Path(image_dir)

    image_ids = sorted(
        path.stem
        for path in image_dir.glob("*.tif")
    )

    if not image_ids:
        raise RuntimeError(
            f"No TIFF images found in {image_dir}"
        )

    rng = np.random.default_rng(seed)

    shuffled = image_ids.copy()
    rng.shuffle(shuffled)

    validation_count = max(
        1,
        int(len(shuffled) * validation_fraction),
    )

    validation_ids = sorted(
        shuffled[:validation_count]
    )

    train_ids = sorted(
        shuffled[validation_count:]
    )

    return train_ids, validation_ids