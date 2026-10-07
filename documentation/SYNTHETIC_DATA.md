# Synthetic Data

## Meaning in This Project

Synthetic data means generated counterfeit-like medicine package images that are used as additional `Fake` examples.

## Why Generative AI

Two kinds of synthetic data are possible:

- Standard synthetic augmentation: modifies real images with realistic visual transformations.
- Generative synthetic data: uses an image generation or image editing model to create new counterfeit-like images.

The project now uses a local Hugging Face Diffusers image-to-image pipeline so the research can test whether YOLOv8 detects realistic, previously unseen generative-AI counterfeit variants.

## Implemented Method

[src/synthetic/generate_synthetic.py](../src/synthetic/generate_synthetic.py) uses `StableDiffusionImg2ImgPipeline` with the default model `runwayml/stable-diffusion-v1-5`. The low default strength (`0.35`) and prompt are intended to preserve package layout and appearance while introducing subtle counterfeit characteristics such as imperfect print registration, inconsistent color reproduction, and minor wear.

Generated images are saved as JPEG files and labelled `Fake`.

The former augmentation implementation remains available with `--backend augmentation` for offline fallback or comparison experiments.

## Parameters

Important CLI options:

```bash
python -m src.synthetic.generate_synthetic --source-dir dataset/Real --output-dir dataset/synthetic/Fake --per-image 1 --max-images 50 --seed 42
```

Generative-AI example:

```bash
python -m src.synthetic.generate_synthetic --source-dir dataset/prepared/train/Real --output-dir dataset/prepared/train/Fake --per-image 1 --backend diffusers --model-id runwayml/stable-diffusion-v1-5 --strength 0.35 --steps 25 --split train --seed 10042
```

- `--source-dir`: source real images
- `--output-dir`: where generated fake images are saved
- `--per-image`: variants per source image
- `--max-images`: optional source image limit
- `--seed`: reproducible random seed
- `--manifest`: CSV record of generated files
- `--backend`: `diffusers` by default, or explicit `augmentation` fallback
- `--model-id`: Hugging Face Diffusers model ID
- `--prompt` and `--negative-prompt`: generation controls
- `--strength`: image-to-image change amount; lower values preserve more structure
- `--steps`: diffusion inference steps
- `--guidance-scale`: prompt guidance

## Labels

Every generated image is saved as a fake example and recorded in the manifest with:

```text
label = Fake
method = diffusers
```

## Quality Checks

Synthetic images are generated from valid images only when using the full preparation pipeline. The generated files are written to:

```text
dataset/prepared/train/Fake
dataset/prepared/synthetic_test/Fake
```

The preparation pipeline records source paths in `runs/synthetic_manifest.csv` and rejects overlap between training-real sources and test-real sources. Test variants are stored under `synthetic_test/Fake`, outside the YOLO train, validation, and test directories.

## Limitations

Diffusion generation is resource intensive, especially on CPU, and model outputs can still change text, logos, or package geometry. The default model is general-purpose rather than medicine-specific. No paid API is required, but model weights are downloaded from Hugging Face. CUDA is recommended; CPU fallback is supported but may take minutes per image. Results must be validated experimentally on held-out sources and an independent dataset.

