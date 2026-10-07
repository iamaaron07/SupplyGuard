from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from ultralytics import YOLO

from src.utils import CLASS_TO_ID, CLASSES, ID_TO_CLASS, image_files, project_root, write_csv


def predict_images(model: YOLO, image_paths: list[Path], imgsz: int) -> tuple[list[int], list[float]]:
    predictions: list[int] = []
    confidences: list[float] = []
    for result in model.predict([str(path) for path in image_paths], imgsz=imgsz, verbose=False):
        probs = result.probs
        pred_id = int(probs.top1)
        predictions.append(pred_id)
        confidences.append(float(probs.top1conf))
    return predictions, confidences


def collect_split_images(dataset: Path, split: str) -> tuple[list[Path], list[int]]:
    paths: list[Path] = []
    labels: list[int] = []
    for class_name in CLASSES:
        class_paths = image_files(dataset / split / class_name)
        paths.extend(class_paths)
        labels.extend([CLASS_TO_ID[class_name]] * len(class_paths))
    return paths, labels


def save_confusion_matrix(y_true: list[int], y_pred: list[int], output_path: Path) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], labels=["Fake", "Real"])
    ax.set_yticks([0, 1], labels=["Fake", "Real"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    for row in range(2):
        for col in range(2):
            ax.text(col, row, matrix[row, col], ha="center", va="center", color="black")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def evaluate_model(model_path: Path, dataset: Path, output_dir: Path, imgsz: int = 224) -> dict[str, object]:
    model_path = model_path.resolve()
    dataset = dataset.resolve()
    output_dir = output_dir.resolve()
    model = YOLO(str(model_path))
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths, y_true = collect_split_images(dataset, "test")
    y_pred, confidences = predict_images(model, image_paths, imgsz)

    rows = [
        {
            "path": str(path),
            "actual": ID_TO_CLASS[actual],
            "predicted": ID_TO_CLASS[predicted],
            "confidence": confidence,
        }
        for path, actual, predicted, confidence in zip(image_paths, y_true, y_pred, confidences)
    ]
    write_csv(output_dir / "test_predictions.csv", rows, ["path", "actual", "predicted", "confidence"])
    save_confusion_matrix(y_true, y_pred, output_dir / "confusion_matrix.png")

    report_text = classification_report(y_true, y_pred, labels=[0, 1], target_names=["Fake", "Real"], zero_division=0)
    (output_dir / "classification_report.txt").write_text(report_text, encoding="utf-8")

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1], zero_division=0
    )
    metrics = {
        "overall_accuracy": accuracy_score(y_true, y_pred) if y_true else 0.0,
        "fake_precision": precision[0],
        "fake_recall": recall[0],
        "fake_f1": f1[0],
        "real_precision": precision[1],
        "real_recall": recall[1],
        "real_f1": f1[1],
    }

    synthetic_paths = image_files(dataset / "synthetic_test" / "Fake")
    if synthetic_paths:
        synthetic_pred, synthetic_conf = predict_images(model, synthetic_paths, imgsz)
        synthetic_true = [CLASS_TO_ID["Fake"]] * len(synthetic_paths)
        synthetic_rows = [
            {
                "path": str(path),
                "actual": "Fake",
                "predicted": ID_TO_CLASS[pred],
                "confidence": conf,
            }
            for path, pred, conf in zip(synthetic_paths, synthetic_pred, synthetic_conf)
        ]
        write_csv(
            output_dir / "synthetic_fake_predictions.csv",
            synthetic_rows,
            ["path", "actual", "predicted", "confidence"],
        )
        synthetic_precision, synthetic_recall, synthetic_f1, _ = precision_recall_fscore_support(
            synthetic_true, synthetic_pred, labels=[CLASS_TO_ID["Fake"]], zero_division=0
        )
        metrics["synthetic_fake_accuracy"] = accuracy_score(synthetic_true, synthetic_pred)
        metrics["synthetic_fake_precision"] = synthetic_precision[0]
        metrics["synthetic_fake_recall"] = synthetic_recall[0]
        metrics["synthetic_fake_f1"] = synthetic_f1[0]
    else:
        metrics["synthetic_fake_accuracy"] = None
        metrics["synthetic_fake_precision"] = None
        metrics["synthetic_fake_recall"] = None
        metrics["synthetic_fake_f1"] = None

    pd.DataFrame([metrics]).to_csv(output_dir / "metrics.csv", index=False)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SupplyGuard YOLOv8 classification model.")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=project_root() / "dataset" / "prepared")
    parser.add_argument("--output-dir", type=Path, default=project_root() / "runs" / "evaluation")
    parser.add_argument("--imgsz", type=int, default=224)
    args = parser.parse_args()

    metrics = evaluate_model(args.model, args.dataset, args.output_dir, args.imgsz)
    print("SupplyGuard evaluation")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print(f"Outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
