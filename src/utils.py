from __future__ import annotations

import csv
import random
import shutil
from pathlib import Path
from typing import Iterable

from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASSES = ("Fake", "Real")
CLASS_TO_ID = {"Fake": 0, "Real": 1}
ID_TO_CLASS = {0: "Fake", 1: "Real"}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def image_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def ensure_class_dirs(root: Path) -> None:
    for split in ("train", "val", "test"):
        for class_name in CLASSES:
            (root / split / class_name).mkdir(parents=True, exist_ok=True)


def verify_image(path: Path) -> tuple[bool, str]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.convert("RGB")
        return True, ""
    except Exception as exc:  # Pillow exposes several image-specific exceptions.
        return False, str(exc)


def copy_image(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination = unique_path(destination)
    shutil.copy2(source, destination)
    return destination


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 100000):
        candidate = path.with_name(f"{stem}_{index:05d}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique path for {path}")


def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def seeded_shuffle(items: list[Path], seed: int) -> list[Path]:
    shuffled = list(items)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def clean_directory_contents(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

