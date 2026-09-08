import torch


def segmentation_metrics(logits, targets, threshold=0.5, eps=1e-7):
    probabilities = torch.sigmoid(logits)
    predictions = (probabilities >= threshold).float()

    predictions = predictions.view(-1)
    targets = targets.view(-1)

    true_positive = (predictions * targets).sum()
    false_positive = (predictions * (1 - targets)).sum()
    false_negative = ((1 - predictions) * targets).sum()

    intersection = true_positive
    union = true_positive + false_positive + false_negative

    dice = (2 * intersection + eps) / (
        2 * true_positive + false_positive + false_negative + eps
    )

    iou = (intersection + eps) / (union + eps)

    precision = (true_positive + eps) / (
        true_positive + false_positive + eps
    )

    recall = (true_positive + eps) / (
        true_positive + false_negative + eps
    )

    return {
        "dice": dice.item(),
        "iou": iou.item(),
        "precision": precision.item(),
        "recall": recall.item(),
    }