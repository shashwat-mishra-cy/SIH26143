import torch
from torch.utils.data import DataLoader

from satellite.model.unet import UNet
from satellite.preprocessing.dataset import SARPatchDataset
from satellite.training.losses import BCEDiceLoss
from satellite.training.metrics import segmentation_metrics
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


def build_scene_splits():

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

    return train_ids, validation_ids


def train_one_epoch(
    model,
    loader,
    optimizer,
    criterion,
    device,
):
    model.train()

    total_loss = 0.0
    batches = 0

    for batch in loader:

        images = batch["image"].to(device)
        masks = batch["mask"].to(device)

        optimizer.zero_grad()

        logits = model(images)

        loss = criterion(logits, masks)

        loss.backward()

        optimizer.step()

        total_loss += loss.item()
        batches += 1

    return total_loss / batches


@torch.no_grad()
def validate(
    model,
    loader,
    criterion,
    device,
):
    model.eval()

    total_loss = 0.0
    total_metrics = {
        "dice": 0.0,
        "iou": 0.0,
        "precision": 0.0,
        "recall": 0.0,
    }

    batches = 0

    for batch in loader:

        images = batch["image"].to(device)
        masks = batch["mask"].to(device)

        logits = model(images)

        loss = criterion(logits, masks)

        metrics = segmentation_metrics(
            logits,
            masks,
        )

        total_loss += loss.item()

        for key in total_metrics:
            total_metrics[key] += metrics[key]

        batches += 1

    return (
        total_loss / batches,
        {
            key: value / batches
            for key, value in total_metrics.items()
        },
    )


def main():

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    if device.type == "cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0),
        )

    train_ids, validation_ids = build_scene_splits()

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

    train_loader = DataLoader(
        train_dataset,
        batch_size=4,
        shuffle=True,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=4,
        shuffle=False,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )

    print(
        "Training patches:",
        len(train_dataset),
    )

    print(
        "Validation patches:",
        len(validation_dataset),
    )

    model = UNet(
        in_channels=2,
        out_channels=1,
    ).to(device)

    criterion = BCEDiceLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-4,
    )

    best_dice = -1.0

    epochs = 10

    print("\nStarting training...\n")

    for epoch in range(epochs):

        train_loss = train_one_epoch(
            model,
            train_loader,
            optimizer,
            criterion,
            device,
        )

        validation_loss, metrics = validate(
            model,
            validation_loader,
            criterion,
            device,
        )

        print(
            f"Epoch {epoch + 1}/{epochs} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {validation_loss:.4f} | "
            f"Val Dice: {metrics['dice']:.4f} | "
            f"Val IoU: {metrics['iou']:.4f} | "
            f"Val Precision: {metrics['precision']:.4f} | "
            f"Val Recall: {metrics['recall']:.4f}"
        )

        if metrics["dice"] > best_dice:

            best_dice = metrics["dice"]

            torch.save(
                model.state_dict(),
                "best_unet.pth",
            )

            print(
                f"  -> Saved best model "
                f"(Dice={best_dice:.4f})"
            )

    print("\nTraining complete.")
    print(f"Best validation Dice: {best_dice:.4f}")
    print("Model saved as: best_unet.pth")


if __name__ == "__main__":
    main()