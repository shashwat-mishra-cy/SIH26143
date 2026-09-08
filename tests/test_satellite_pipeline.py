import torch

from satellite.model.unet import UNet
from satellite.training.losses import BCEDiceLoss
from satellite.training.metrics import segmentation_metrics
from satellite.inference.predict import predict_mask


def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    model = UNet(
        in_channels=2,
        out_channels=1
    ).to(device)

    image = torch.randn(
        2, 2, 256, 256,
        device=device
    )

    target = torch.randint(
        0,
        2,
        (2, 1, 256, 256),
        device=device
    ).float()

    criterion = BCEDiceLoss()

    logits = model(image)

    loss = criterion(logits, target)

    metrics = segmentation_metrics(
        logits,
        target
    )

    result = predict_mask(
        model,
        image
    )

    print("Input:", image.shape)
    print("Output:", logits.shape)
    print("Loss:", loss.item())
    print("Metrics:", metrics)
    print("Probability:", result["probability"].shape)
    print("Mask:", result["mask"].shape)


if __name__ == "__main__":
    main()