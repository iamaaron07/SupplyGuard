from __future__ import annotations

import argparse
from pathlib import Path

from src.data.split_dataset import split_dataset
from src.data.validate_dataset import validate_dataset
from src.synthetic.generate_synthetic import (
    DEFAULT_MODEL_ID,
    DEFAULT_NEGATIVE_PROMPT,
    DEFAULT_PROMPT,
    DiffusionImageToImageGenerator,
    generate_synthetic_dataset,
)
from src.utils import copy_image, project_root, write_csv


def prepare_dataset(
    dataset_dir: Path,
    output_dir: Path,
    synthetic_per_train_real: int = 1,
    synthetic_test_count: int = 30,
    seed: int = 42,
    overwrite: bool = False,
    backend: str = "diffusers",
    model_id: str = DEFAULT_MODEL_ID,
    prompt: str | None = None,
    negative_prompt: str | None = None,
    strength: float = 0.35,
    steps: int = 25,
    guidance_scale: float = 7.0,
) -> None:
    validation_report = project_root() / "runs" / "dataset_validation.csv"
    split_manifest = project_root() / "runs" / "split_manifest.csv"
    synthetic_manifest = project_root() / "runs" / "synthetic_manifest.csv"

    summary = validate_dataset(dataset_dir, validation_report)
    if summary["invalid"]:
        raise RuntimeError(
            f"Found {summary['invalid']} invalid images. See {validation_report} before preparing data."
        )

    split_rows = split_dataset(dataset_dir, output_dir, seed=seed, overwrite=overwrite)

    diffusion_generator = None
    if backend == "diffusers":
        diffusion_generator = DiffusionImageToImageGenerator(
            model_id,
            prompt or DEFAULT_PROMPT,
            negative_prompt or DEFAULT_NEGATIVE_PROMPT,
            strength,
            steps,
            guidance_scale,
        )

    train_synthetic_rows = generate_synthetic_dataset(
        output_dir / "train" / "Real",
        output_dir / "train" / "Fake",
        per_image=synthetic_per_train_real,
        seed=seed + 10000,
        split="train",
        backend=backend,
        model_id=model_id,
        prompt=prompt or DEFAULT_PROMPT,
        negative_prompt=negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        strength=strength,
        steps=steps,
        guidance_scale=guidance_scale,
        diffusion_generator=diffusion_generator,
    )

    synthetic_test_source = output_dir / "test" / "Real"
    synthetic_test_dir = output_dir / "synthetic_test" / "Fake"
    synthetic_test_rows = generate_synthetic_dataset(
        synthetic_test_source,
        synthetic_test_dir,
        per_image=1,
        max_images=synthetic_test_count,
        seed=seed + 20000,
        split="synthetic_test",
        backend=backend,
        model_id=model_id,
        prompt=prompt or DEFAULT_PROMPT,
        negative_prompt=negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        strength=strength,
        steps=steps,
        guidance_scale=guidance_scale,
        diffusion_generator=diffusion_generator,
    )

    train_sources = {Path(str(row["source_path"])).resolve() for row in train_synthetic_rows}
    test_sources = {Path(str(row["source_path"])).resolve() for row in synthetic_test_rows}
    overlap = train_sources.intersection(test_sources)
    if overlap:
        raise RuntimeError(f"Synthetic train/test source overlap detected: {sorted(overlap)}")

    for row in train_synthetic_rows:
        split_rows.append(
            {
                "source_path": row["source_path"],
                "prepared_path": row["synthetic_path"],
                "class": "Fake",
                "split": "train",
                "synthetic": True,
            }
        )

    write_csv(split_manifest, split_rows, ["source_path", "prepared_path", "class", "split", "synthetic"])
    write_csv(
        synthetic_manifest,
        train_synthetic_rows + synthetic_test_rows,
        ["source_path", "synthetic_path", "label", "method", "model", "split", "seed"],
    )

    print("SupplyGuard dataset prepared")
    print(f"Validation report: {validation_report}")
    print(f"Split manifest: {split_manifest}")
    print(f"Synthetic manifest: {synthetic_manifest}")
    print(f"YOLO dataset: {output_dir}")
    print(f"Synthetic-fake test set: {synthetic_test_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate, split, and synthesize SupplyGuard dataset.")
    parser.add_argument("--dataset", type=Path, default=project_root() / "dataset")
    parser.add_argument("--output", type=Path, default=project_root() / "dataset" / "prepared")
    parser.add_argument("--synthetic-per-train-real", type=int, default=1)
    parser.add_argument("--synthetic-test-count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--backend", choices=("diffusers", "augmentation"), default="diffusers")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--negative-prompt", default=None)
    parser.add_argument("--strength", type=float, default=0.35)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--guidance-scale", type=float, default=7.0)
    args = parser.parse_args()

    prepare_dataset(
        args.dataset,
        args.output,
        synthetic_per_train_real=args.synthetic_per_train_real,
        synthetic_test_count=args.synthetic_test_count,
        seed=args.seed,
        overwrite=args.overwrite,
        backend=args.backend,
        model_id=args.model_id,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        strength=args.strength,
        steps=args.steps,
        guidance_scale=args.guidance_scale,
    )


if __name__ == "__main__":
    main()

