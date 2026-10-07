from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from src.utils import image_files, project_root, unique_path, write_csv

DEFAULT_MODEL_ID = "runwayml/stable-diffusion-v1-5"
DEFAULT_PROMPT = (
    "subtle counterfeit medicine package, same package layout and branding, "
    "slightly imperfect print registration, inconsistent color reproduction, "
    "minor packaging wear, realistic product photography"
)
DEFAULT_NEGATIVE_PROMPT = (
    "different package, redesigned label, changed text, extra objects, "
    "cartoon, illustration, blurry, deformed, unreadable composition"
)


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _change_lighting(image: Image.Image, rng: random.Random) -> Image.Image:
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.72, 1.25))
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.78, 1.28))
    image = ImageEnhance.Color(image).enhance(rng.uniform(0.82, 1.18))
    return image


def _rotate_scale(image: Image.Image, rng: random.Random) -> Image.Image:
    angle = rng.uniform(-8, 8)
    scale = rng.uniform(0.92, 1.05)
    width, height = image.size
    canvas = ImageOps.expand(image, border=int(max(width, height) * 0.08), fill=(245, 245, 245))
    canvas = canvas.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(245, 245, 245))
    new_size = (max(1, int(canvas.width * scale)), max(1, int(canvas.height * scale)))
    canvas = canvas.resize(new_size, Image.Resampling.BICUBIC)
    left = max(0, (canvas.width - width) // 2)
    top = max(0, (canvas.height - height) // 2)
    return canvas.crop((left, top, min(left + width, canvas.width), min(top + height, canvas.height))).resize(
        (width, height), Image.Resampling.BICUBIC
    )


def _perspective(image: Image.Image, rng: random.Random) -> Image.Image:
    array = np.array(image)
    height, width = array.shape[:2]
    max_shift = int(min(width, height) * 0.045)
    source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    dest = np.float32(
        [
            [rng.randint(0, max_shift), rng.randint(0, max_shift)],
            [width - rng.randint(0, max_shift), rng.randint(0, max_shift)],
            [width - rng.randint(0, max_shift), height - rng.randint(0, max_shift)],
            [rng.randint(0, max_shift), height - rng.randint(0, max_shift)],
        ]
    )
    matrix = cv2.getPerspectiveTransform(source, dest)
    warped = cv2.warpPerspective(array, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(warped)


def _shadow_and_degradation(image: Image.Image, rng: random.Random) -> Image.Image:
    array = np.array(image).astype(np.float32)
    height, width = array.shape[:2]
    x_gradient = np.linspace(rng.uniform(0.72, 1.0), rng.uniform(0.9, 1.18), width)
    y_gradient = np.linspace(rng.uniform(0.85, 1.05), rng.uniform(0.72, 1.1), height)
    mask = np.outer(y_gradient, x_gradient)
    array *= mask[:, :, None]

    noise = np.random.default_rng(rng.randint(0, 2**32 - 1)).normal(0, rng.uniform(2, 7), array.shape)
    array = np.clip(array + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(array)

    if rng.random() < 0.45:
        image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.25, 1.2)))
    return image


def make_synthetic_fake(source: Path, output: Path, seed: int) -> Path:
    rng = _rng(seed)
    with Image.open(source) as opened:
        image = opened.convert("RGB")

    image = _change_lighting(image, rng)
    image = _rotate_scale(image, rng)
    image = _perspective(image, rng)
    image = _shadow_and_degradation(image, rng)

    output.mkdir(parents=True, exist_ok=True)
    destination = unique_path(output / f"synthetic_fake_{source.stem}_{seed}.jpg")
    quality = rng.randint(48, 82)
    image.save(destination, "JPEG", quality=quality, optimize=True)
    return destination


class DiffusionImageToImageGenerator:
    def __init__(
        self,
        model_id: str,
        prompt: str,
        negative_prompt: str,
        strength: float,
        steps: int,
        guidance_scale: float,
    ) -> None:
        try:
            from diffusers import StableDiffusionImg2ImgPipeline
        except ImportError as exc:
            raise RuntimeError(
                "Diffusers is not installed. Run `pip install -r requirements.txt`, "
                "or use --backend augmentation for a non-generative fallback."
            ) from exc

        if not 0.0 < strength <= 1.0:
            raise ValueError("--strength must be greater than 0 and at most 1")
        if steps < 1:
            raise ValueError("--steps must be at least 1")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        load_kwargs: dict[str, Any] = {"torch_dtype": dtype, "safety_checker": None}
        if self.device == "cuda":
            load_kwargs["variant"] = "fp16"

        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(model_id, **load_kwargs)
        self.pipeline = self.pipeline.to(self.device)
        if self.device == "cpu":
            self.pipeline.enable_attention_slicing()

        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.strength = strength
        self.steps = steps
        self.guidance_scale = guidance_scale
        self.model_id = model_id

    @staticmethod
    def _generation_size(image: Image.Image) -> tuple[int, int]:
        width, height = image.size
        scale = min(768 / max(width, height), 1.0)
        width = max(256, int(width * scale))
        height = max(256, int(height * scale))
        return width - width % 8, height - height % 8

    def generate(self, source: Path, output: Path, seed: int) -> Path:
        with Image.open(source) as opened:
            source_image = opened.convert("RGB")
        width, height = self._generation_size(source_image)
        source_image = source_image.resize((width, height), Image.Resampling.LANCZOS)
        generator = torch.Generator(device=self.device).manual_seed(seed)
        result = self.pipeline(
            prompt=self.prompt,
            negative_prompt=self.negative_prompt,
            image=source_image,
            strength=self.strength,
            num_inference_steps=self.steps,
            guidance_scale=self.guidance_scale,
            generator=generator,
            width=width,
            height=height,
        ).images[0]

        output.mkdir(parents=True, exist_ok=True)
        destination = unique_path(output / f"synthetic_fake_{source.stem}_{seed}.jpg")
        result.convert("RGB").save(destination, "JPEG", quality=95, optimize=True)
        return destination


def generate_synthetic_dataset(
    source_dir: Path,
    output_dir: Path,
    per_image: int = 1,
    max_images: int | None = None,
    seed: int = 42,
    split: str = "unassigned",
    backend: str = "diffusers",
    model_id: str = DEFAULT_MODEL_ID,
    prompt: str = DEFAULT_PROMPT,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    strength: float = 0.35,
    steps: int = 25,
    guidance_scale: float = 7.0,
    diffusion_generator: DiffusionImageToImageGenerator | None = None,
) -> list[dict[str, object]]:
    sources = image_files(source_dir)
    if max_images is not None:
        sources = sources[:max_images]

    if backend == "diffusers" and diffusion_generator is None:
        diffusion_generator = DiffusionImageToImageGenerator(
            model_id,
            prompt,
            negative_prompt,
            strength,
            steps,
            guidance_scale,
        )

    rows: list[dict[str, object]] = []
    for source_index, source in enumerate(sources):
        for variant in range(per_image):
            variant_seed = seed + source_index * 1000 + variant
            if backend == "diffusers" and diffusion_generator is not None:
                destination = diffusion_generator.generate(source, output_dir, variant_seed)
            elif backend == "augmentation":
                destination = make_synthetic_fake(source, output_dir, variant_seed)
            else:
                raise ValueError(f"Unsupported synthetic backend: {backend}")
            rows.append(
                {
                    "source_path": str(source),
                    "synthetic_path": str(destination),
                    "label": "Fake",
                    "method": backend,
                    "model": model_id if backend == "diffusers" else "",
                    "split": split,
                    "seed": variant_seed,
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AI-generated synthetic counterfeit medicine images.")
    parser.add_argument("--source-dir", type=Path, default=project_root() / "dataset" / "Real")
    parser.add_argument("--output-dir", type=Path, default=project_root() / "dataset" / "synthetic" / "Fake")
    parser.add_argument("--per-image", type=int, default=1)
    parser.add_argument("--max-images", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--split", default="unassigned")
    parser.add_argument("--backend", choices=("diffusers", "augmentation"), default="diffusers")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE_PROMPT)
    parser.add_argument("--strength", type=float, default=0.35)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--guidance-scale", type=float, default=7.0)
    parser.add_argument("--manifest", type=Path, default=project_root() / "runs" / "synthetic_manifest.csv")
    args = parser.parse_args()

    rows = generate_synthetic_dataset(
        args.source_dir,
        args.output_dir,
        per_image=args.per_image,
        max_images=args.max_images,
        seed=args.seed,
        split=args.split,
        backend=args.backend,
        model_id=args.model_id,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        strength=args.strength,
        steps=args.steps,
        guidance_scale=args.guidance_scale,
    )
    write_csv(
        args.manifest,
        rows,
        ["source_path", "synthetic_path", "label", "method", "model", "split", "seed"],
    )
    print(f"Generated {len(rows)} synthetic fake images in {args.output_dir}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()

