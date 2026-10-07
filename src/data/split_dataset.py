from __future__ import annotations

import argparse
from pathlib import Path

from src.utils import CLASSES, clean_directory_contents, copy_image, ensure_class_dirs, image_files, project_root, seeded_shuffle, write_csv


def split_class_images(
    images: list[Path],
    train_ratio: float,
    val_ratio: float,
) -> dict[str, list[Path]]:
    total = len(images)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    return {
        "train": images[:train_end],
        "val": images[train_end:val_end],
        "test": images[val_end:],
    }


def split_dataset(
    dataset_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
    overwrite: bool = False,
) -> list[dict[str, object]]:
    if overwrite:
        clean_directory_contents(output_dir)
    ensure_class_dirs(output_dir)

    rows: list[dict[str, object]] = []
    for class_name in CLASSES:
        shuffled = seeded_shuffle(image_files(dataset_dir / class_name), seed)
        splits = split_class_images(shuffled, train_ratio, val_ratio)
        for split_name, paths in splits.items():
            for source in paths:
                destination = copy_image(source, output_dir / split_name / class_name / source.name)
                rows.append(
                    {
                        "source_path": str(source),
                        "prepared_path": str(destination),
                        "class": class_name,
                        "split": split_name,
                        "synthetic": False,
                    }
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Split SupplyGuard dataset for YOLOv8 classification.")
    parser.add_argument("--dataset", type=Path, default=project_root() / "dataset")
    parser.add_argument("--output", type=Path, default=project_root() / "dataset" / "prepared")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--manifest", type=Path, default=project_root() / "runs" / "split_manifest.csv")
    args = parser.parse_args()

    rows = split_dataset(
        args.dataset,
        args.output,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
        overwrite=args.overwrite,
    )
    write_csv(args.manifest, rows, ["source_path", "prepared_path", "class", "split", "synthetic"])
    print(f"Prepared {len(rows)} images in {args.output}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()

