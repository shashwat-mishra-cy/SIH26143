import torch


def predict_mask(model, image, device=None, threshold=0.5):
    if device is None:
        device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

    model = model.to(device)
    model.eval()

    if image.ndim == 3:
        image = image.unsqueeze(0)

    image = image.to(device)

    with torch.no_grad():
        logits = model(image)
        probabilities = torch.sigmoid(logits)

    mask = (probabilities >= threshold).float()

    return {
        "probability": probabilities.cpu(),
        "mask": mask.cpu()
    }