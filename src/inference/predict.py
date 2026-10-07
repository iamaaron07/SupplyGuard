from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

from src.utils import ID_TO_CLASS, image_files

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def predict_one(model: YOLO, image_path: Path, imgsz: int = 224) -> tuple[str, float]:
    result = model.predict(str(image_path), imgsz=imgsz, verbose=False)[0]
    class_id = int(result.probs.top1)
    confidence = float(result.probs.top1conf)
    return ID_TO_CLASS.get(class_id, str(class_id)).upper(), confidence


def print_prediction(image_path: Path, prediction: str, confidence: float) -> None:
    print("================================")
    print("SupplyGuard AI Prediction")
    print("================================")
    print(f"Image: {image_path.name}")
    print("")
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence * 100:.2f}%")
    print("================================")


def validate_image_path(image_path: Path) -> Path:
    if not image_path.exists():
        raise SystemExit(
            f"Image not found:\n{image_path}\n\n"
            "Please provide the path to an existing medicine image."
        )
    if not image_path.is_file():
        raise SystemExit(
            f"Image path is not a file:\n{image_path}\n\n"
            "Please provide the path to an existing medicine image file."
        )
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise SystemExit(
            f"Unsupported image type:\n{image_path}\n\n"
            f"Supported image extensions are: {supported}"
        )
    return image_path


def validate_image_dir(image_dir: Path) -> list[Path]:
    if not image_dir.exists():
        raise SystemExit(
            f"Image directory not found:\n{image_dir}\n\n"
            "Please provide a directory that contains medicine images."
        )
    if not image_dir.is_dir():
        raise SystemExit(
            f"Image directory path is not a directory:\n{image_dir}\n\n"
            "Please provide a directory that contains medicine images."
        )

    paths = [
        path
        for path in image_files(image_dir)
        if path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    if not paths:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise SystemExit(
            f"No supported images found in:\n{image_dir}\n\n"
            f"Supported image extensions are: {supported}"
        )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict REAL or FAKE medicine package images.")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--image-dir", type=Path)
    parser.add_argument("--imgsz", type=int, default=224)
    args = parser.parse_args()

    if not args.image and not args.image_dir:
        raise SystemExit("Provide --image or --image-dir.")

    paths = [validate_image_path(args.image)] if args.image else validate_image_dir(args.image_dir)
    model = YOLO(str(args.model.resolve()))
    for path in paths:
        prediction, confidence = predict_one(model, path, args.imgsz)
        print_prediction(path, prediction, confidence)


if __name__ == "__main__":
    main()
