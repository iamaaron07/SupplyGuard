from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

from src.utils import project_root


def train_model(
    dataset: Path,
    model_name: str,
    epochs: int,
    imgsz: int,
    batch: int,
    lr0: float | None,
    seed: int,
    output_dir: Path,
    run_name: str,
) -> None:
    dataset = dataset.resolve()
    output_dir = output_dir.resolve()
    model = YOLO(model_name)
    kwargs = {
        "data": str(dataset),
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "seed": seed,
        "project": str(output_dir),
        "name": run_name,
        "task": "classify",
    }
    if lr0 is not None:
        kwargs["lr0"] = lr0
    model.train(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLOv8 classification for SupplyGuard.")
    parser.add_argument("--dataset", type=Path, default=project_root() / "dataset" / "prepared")
    parser.add_argument("--model", default="yolov8n-cls.pt")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr0", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=project_root() / "runs" / "classification")
    parser.add_argument("--run-name", default="supplyguard_yolov8_cls")
    args = parser.parse_args()

    train_model(
        args.dataset,
        args.model,
        args.epochs,
        args.imgsz,
        args.batch,
        args.lr0,
        args.seed,
        args.output_dir,
        args.run_name,
    )


if __name__ == "__main__":
    main()
