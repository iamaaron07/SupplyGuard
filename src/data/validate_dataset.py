from __future__ import annotations

import argparse
from pathlib import Path

from src.utils import CLASSES, image_files, project_root, verify_image, write_csv


def validate_dataset(dataset_dir: Path, report_path: Path | None = None) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    summary: dict[str, object] = {"valid": 0, "invalid": 0, "classes": {}}

    for class_name in CLASSES:
        class_dir = dataset_dir / class_name
        valid_count = 0
        invalid_count = 0
        for path in image_files(class_dir):
            is_valid, error = verify_image(path)
            rows.append(
                {
                    "path": str(path),
                    "class": class_name,
                    "valid": is_valid,
                    "error": error,
                }
            )
            valid_count += int(is_valid)
            invalid_count += int(not is_valid)

        summary["classes"][class_name] = {
            "valid": valid_count,
            "invalid": invalid_count,
        }
        summary["valid"] += valid_count
        summary["invalid"] += invalid_count

    if report_path:
        write_csv(report_path, rows, ["path", "class", "valid", "error"])

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate SupplyGuard medicine images.")
    parser.add_argument("--dataset", type=Path, default=project_root() / "dataset")
    parser.add_argument(
        "--report",
        type=Path,
        default=project_root() / "runs" / "dataset_validation.csv",
    )
    args = parser.parse_args()

    summary = validate_dataset(args.dataset, args.report)
    print("SupplyGuard dataset validation")
    print(f"Dataset: {args.dataset}")
    for class_name, counts in summary["classes"].items():
        print(f"{class_name}: {counts['valid']} valid, {counts['invalid']} invalid")
    print(f"Total: {summary['valid']} valid, {summary['invalid']} invalid")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()

