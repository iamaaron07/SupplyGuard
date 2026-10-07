# SupplyGuard

SupplyGuard combines an AI/ML counterfeit medicine detector with an immutable blockchain provenance ledger.

## System Scope

**AI/ML** -> YOLOv8 image classification predicts `REAL` or `FAKE` with confidence.

**BLOCKCHAIN** -> Solidity supply-chain tracking, provenance, and an immutable audit trail for batches and AI verification results.

**Frontend** -> Not implemented yet. The current project is command-line and contract focused.

## Project Objective

The system classifies a medicine package image as:

- `FAKE` = class id `0`
- `REAL` = class id `1`

The required research flow is:

```text
Real medicine images
-> synthetic-data generation
-> realistic counterfeit-looking synthetic fake images
-> label generated images as FAKE
-> train YOLOv8 classification
-> predict REAL or FAKE with confidence
```

## Problem Solved

Counterfeit medicine packaging can be difficult to identify manually. This pipeline provides a reproducible starting point for training an image classifier that learns from genuine medicine images, known counterfeit images, and synthetic counterfeit-like variants.

## AI Architecture

The model is YOLOv8 classification, using `yolov8n-cls.pt` by default. YOLO is used only as a binary image classifier:

```text
Input image -> YOLOv8 Classification -> REAL / FAKE -> confidence score
```

No separate CNN is created after YOLO.

## Blockchain Architecture

The Solidity contract in [contracts/SupplyGuardLedger.sol](contracts/SupplyGuardLedger.sol) stores batch metadata and an append-only history:

```text
Manufacturer -> Packaging -> Warehouse -> Distributor -> Retailer -> AI Verification
```

Each record includes the batch ID, stage, actor wallet, block timestamp, optional location/notes, and a cryptographic hash. AI verification records additionally store `REAL` or `FAKE` and confidence in basis points (`9700` = `97.00%`). Images remain off-chain; only their hash is recorded.

Records are chained with `previousRecordId`, and there are no update or delete functions. Hashes cannot be reused. The owner authorizes manufacturers and supply-chain participants, while reads are publicly available.

## Why YOLOv8 Classification

YOLOv8 classification is lightweight, easy to train, and production-friendly. It gives a simple model artifact, standard training outputs, and direct confidence scores while avoiding unnecessary object detection logic for a binary package-level task.

## Dataset

The expected raw dataset structure is:

```text
dataset/
  Fake/
  Real/
```

The current raw dataset validation found:

- `Fake`: 240 valid images
- `Real`: 421 valid images
- Invalid/corrupted images: 0

The repository also had existing `dataset/train`, `dataset/val`, and `dataset/test` folders. The new pipeline does not overwrite them by default. It prepares a leakage-aware copy under `dataset/prepared/`.

## Synthetic Data Generation

Synthetic data generation is implemented in [src/synthetic/generate_synthetic.py](src/synthetic/generate_synthetic.py). The default backend is a local Hugging Face Diffusers image-to-image pipeline using `runwayml/stable-diffusion-v1-5`. It starts from a genuine package image, preserves the general composition with low image-to-image strength, and introduces subtle counterfeit-looking visual imperfections. Every output is labelled `Fake`.

The previous augmentation-only approach used rotation, brightness, blur, noise, perspective, shadows, and compression. Those transformations are useful augmentation but are not generative AI. The new Diffusers path is the research generator; the old method remains available explicitly with `--backend augmentation` as a CPU/offline fallback.

Default settings use strength `0.35`, 25 inference steps, and seed `42`. Diffusion weights are downloaded from Hugging Face on first use and cached locally. CUDA is used automatically when available. CPU generation is supported through float32 attention slicing but can be very slow; a GPU with at least 8 GB VRAM is recommended.

These AI-generated synthetic counterfeit images are for research purposes. Whether YOLOv8 identifies unseen generated images as `FAKE` must be validated experimentally.

## Dataset Preparation

Run:

```bash
python -m src.data.prepare_dataset --dataset dataset --output dataset/prepared --synthetic-per-train-real 1 --synthetic-test-count 30 --backend diffusers --model-id runwayml/stable-diffusion-v1-5 --strength 0.35 --steps 25 --seed 42 --overwrite
```

Generate synthetic training fakes only from training real images:

```bash
python -m src.synthetic.generate_synthetic --source-dir dataset/prepared/train/Real --output-dir dataset/prepared/train/Fake --per-image 1 --backend diffusers --split train --seed 10042
```

Generate unseen synthetic test fakes only from test real images:

```bash
python -m src.synthetic.generate_synthetic --source-dir dataset/prepared/test/Real --output-dir dataset/prepared/synthetic_test/Fake --max-images 30 --backend diffusers --split synthetic_test --seed 20042
```

The generator accepts `--model-id`, `--prompt`, `--negative-prompt`, `--strength`, `--steps`, `--guidance-scale`, `--per-image`, `--max-images`, `--seed`, and `--output-dir`.

The verified prepared dataset contains:

- `train/Fake`: 462 images, including 294 synthetic fakes
- `train/Real`: 294 images
- `val/Fake`: 36 images
- `val/Real`: 63 images
- `test/Fake`: 36 images
- `test/Real`: 64 images
- `synthetic_test/Fake`: 30 unseen synthetic fake images

Leakage prevention: synthetic training fakes are generated only from training real images. The separate synthetic-fake test set is generated only from test real images, checked for source overlap, and is not added to YOLO training.

## Training Pipeline

Run a full training job:

```bash
python -m src.training.train --dataset dataset/prepared --model yolov8n-cls.pt --epochs 30 --imgsz 224 --batch 16 --output-dir runs/classification --run-name supplyguard_yolov8_cls
```

A smoke test was verified with:

```bash
python -m src.training.train --dataset dataset/prepared --model yolov8n-cls.pt --epochs 1 --imgsz 64 --batch 8 --output-dir runs/classification --run-name smoke_yolov8_cls_abs
```

Smoke-test output checkpoint:

```text
runs/classification/smoke_yolov8_cls_abs/weights/best.pt
```

## Evaluation

Run:

```bash
python -m src.evaluation.evaluate --model runs/classification/supplyguard_yolov8_cls/weights/best.pt --dataset dataset/prepared --output-dir runs/evaluation/supplyguard_yolov8_cls --imgsz 224
```

The evaluator reports:

- accuracy
- precision
- recall
- F1-score
- confusion matrix
- separate unseen AI-generated synthetic-fake accuracy, precision, recall, and F1

Smoke-test metrics from the one-epoch 64px run:

- Overall test accuracy: 68%
- Fake precision: 0.5370
- Fake recall: 0.8056
- Real precision: 0.8478
- Real recall: 0.6094
- Synthetic fake accuracy: 40%

These are smoke-test metrics only and should not be treated as final model performance.

The key research metric is `synthetic_fake_accuracy`: whether YOLOv8 classifies previously unseen AI-generated counterfeit variants as `FAKE`.

## Inference

Single image:

```bash
python -m src.inference.predict --model runs/classification/supplyguard_yolov8_cls/weights/best.pt --image dataset/prepared/test/Real/images04.jpg --imgsz 224
```

Batch folder:

```bash
python -m src.inference.predict --model runs/classification/supplyguard_yolov8_cls/weights/best.pt --image-dir dataset/prepared/test/Fake --imgsz 224
```

Expected output:

```text
================================
SupplyGuard AI Prediction
================================
Image: medicine.jpg

Prediction: FAKE
Confidence: 95.23%
================================
```

Verified smoke prediction:

```text
Image: Screenshot 2025-09-17 173925.png
Prediction: FAKE
Confidence: 82.60%
```

## Current Performance

The completed 30-epoch model is `runs/classification/supplyguard_yolov8_cls-3/weights/best.pt`.
Measured held-out test metrics:

| Metric | Value |
| --- | ---: |
| Accuracy | 98.00% |
| Fake precision / recall / F1 | 100.00% / 94.44% / 97.14% |
| Real precision / recall / F1 | 96.97% / 100.00% / 98.46% |

The current offline augmentation-based synthetic-fake set measured 13.33% accuracy, 100.00% precision, 13.33% recall, and 23.53% F1. This is a research limitation, not a production claim. The Diffusers generator remains available and requires a model download and substantial compute.

## Installation

Create and activate a virtual environment, then install:

```bash
pip install -r requirements.txt
```

The first training run may download `yolov8n-cls.pt` if it is not already cached. The Diffusers backend downloads Stable Diffusion weights from Hugging Face; use `--backend augmentation` when that download or GPU compute is unavailable.

## Application Backend and Frontend

The FastAPI service in `backend/main.py` loads the configured YOLO checkpoint, validates uploaded images, returns the actual verdict/confidence and image SHA-256, and can optionally call the ledger. The responsive frontend is served at `/` by the same service.

```bash
npm run api
```

Open `http://127.0.0.1:8000`. Set `SUPPLYGUARD_MODEL_PATH` to use another checkpoint. Enable the “Record verification” control only after a local ledger is deployed and a batch exists; the app reads `SUPPLYGUARD_CONTRACT_ADDRESS` or `runs/blockchain/deployment.json`.

## Blockchain Development

Install the JavaScript dependencies with `npm install`, then compile and test:

```bash
npm run compile
npm test
```

Start a local node in one terminal and deploy in another:

```bash
npx hardhat node
npm run deploy:local
npx hardhat run scripts/demo.js --network localhost
```

`deploy:local` writes the address to `runs/blockchain/deployment.json`; the demo reuses that address. The API’s optional recording path uses `scripts/record-verification.js` and records only the image hash, verdict, confidence, location, and notes. Sepolia requires a `.env` copied from `.env.example` with real `SEPOLIA_RPC_URL` and `PRIVATE_KEY`; credentials are not included in this project. See [documentation/BLOCKCHAIN.md](documentation/BLOCKCHAIN.md) for the contract API and security notes.

## Complete Local Demo

Use three terminals from `D:\SupplyGuard1`:

```bash
# Terminal 1: local chain (keep running)
npx hardhat node

# Terminal 2: deploy and seed a batch
npm run deploy:local
npx hardhat run scripts/demo.js --network localhost

# Terminal 3: application (keep running), then open the URL
npm run api
```

Upload a known image from `dataset/prepared/test/Real` or `dataset/prepared/test/Fake`. Enter `SG-BATCH-001`, select ledger recording, and click Verify Product. The displayed prediction and transaction are produced by the live model and contract.

## Testing and Evaluation

```bash
npm run compile
npm test
python -m src.data.validate_dataset --dataset dataset
python -m src.evaluation.evaluate --model runs/classification/supplyguard_yolov8_cls-3/weights/best.pt --dataset dataset/prepared --output-dir runs/evaluation/supplyguard_yolov8_cls-3 --imgsz 224
python -m src.inference.predict --model runs/classification/supplyguard_yolov8_cls-3/weights/best.pt --image dataset/prepared/test/Real/images04.jpg
```

There is no separate database, authentication system, or production wallet UI. Images remain off-chain. The API currently stores uploads only temporarily for inference.

## Project Structure

```text
dataset/
  Fake/
  Real/
  prepared/
src/
  data/
  synthetic/
  training/
  evaluation/
  inference/
documentation/
models/
runs/
README.md
requirements.txt
.gitignore
contracts/
  SupplyGuardLedger.sol
scripts/
  deploy.js
  demo.js
test/
  SupplyGuardLedger.test.js
```

## File-by-File Explanation

[src/utils.py](src/utils.py)  
Shared helpers for image discovery, class mappings, image validation, CSV writing, copying, and reproducible shuffling.

[src/data/validate_dataset.py](src/data/validate_dataset.py)  
Validates raw `dataset/Fake` and `dataset/Real` images with Pillow and writes a CSV validation report.

[src/data/split_dataset.py](src/data/split_dataset.py)  
Creates train, validation, and test copies for YOLOv8 classification without modifying raw data.

[src/data/prepare_dataset.py](src/data/prepare_dataset.py)  
Runs validation, creates `dataset/prepared/`, generates synthetic fake training images, and creates a separate synthetic-fake test set.

[src/synthetic/generate_synthetic.py](src/synthetic/generate_synthetic.py)  
Generates AI-generated synthetic counterfeit images with a configurable Diffusers image-to-image pipeline and labels them as `Fake`. The legacy augmentation backend remains available explicitly for comparison or offline fallback.

[src/training/train.py](src/training/train.py)  
Trains a YOLOv8 classification model with configurable model, epochs, image size, batch size, learning rate, seed, and output directory.

[src/evaluation/evaluate.py](src/evaluation/evaluate.py)  
Calculates test accuracy, precision, recall, F1-score, confusion matrix, prediction CSVs, and synthetic-fake test accuracy.

[src/inference/predict.py](src/inference/predict.py)  
Runs single-image or batch-folder inference and prints the predicted class plus confidence.

[contracts/SupplyGuardLedger.sol](contracts/SupplyGuardLedger.sol)  
Stores batches, append-only supply-chain records, AI verdicts, confidence, and verification hashes with authorization controls.

[scripts/deploy.js](scripts/deploy.js) and [scripts/demo.js](scripts/demo.js)  
Deploy the ledger to a selected Hardhat network and demonstrate a complete supply-chain history.

[test/SupplyGuardLedger.test.js](test/SupplyGuardLedger.test.js)  
Covers deployment, authorization, batch creation, emitted events, supply-chain events, AI verification, validation, duplicate hashes, history retrieval, and append-only behavior.

[src/__init__.py](src/__init__.py), [src/data/__init__.py](src/data/__init__.py), [src/synthetic/__init__.py](src/synthetic/__init__.py), [src/training/__init__.py](src/training/__init__.py), [src/evaluation/__init__.py](src/evaluation/__init__.py), [src/inference/__init__.py](src/inference/__init__.py)  
Package marker files that make the modules importable with `python -m`.

[documentation/DEVELOPMENT.md](documentation/DEVELOPMENT.md)  
Development journey, decisions, actual problems encountered, and current status.

[documentation/DATASET.md](documentation/DATASET.md)  
Dataset source assumptions, structure, validation results, split counts, synthetic labels, and leakage prevention.

[documentation/SYNTHETIC_DATA.md](documentation/SYNTHETIC_DATA.md)  
Synthetic data definition, implemented generation method, parameters, quality checks, and limitations.

[documentation/TRAINING.md](documentation/TRAINING.md)  
YOLOv8 training process, parameters, outputs, smoke run, and full training command.

[documentation/EVALUATION.md](documentation/EVALUATION.md)  
Evaluation metrics, confusion matrix output, synthetic-fake evaluation, and interpretation.

[documentation/TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md)  
Real issues encountered during development and how they were resolved.

[requirements.txt](requirements.txt)  
Python dependencies used by the pipeline.

[.gitignore](.gitignore)  
Ignores generated datasets, runs, cache files, secrets, virtual environments, and model checkpoints.

## Limitations

- Diffusion output may change package text, logos, or geometry despite low image-to-image strength.
- The one-epoch smoke model is only proof that the pipeline runs.
- More data, stronger validation, and longer training are required before real-world use.
- The model may learn dataset-specific artifacts if the raw dataset is narrow or screenshot-heavy.
- The blockchain contract is a simple student-project ledger; it does not replace regulatory systems, identity verification, or a production key-management service.

## Future Improvements

- Compare additional open-source image-to-image models and prompts for counterfeit variants.
- Add stronger split grouping if product IDs or batch metadata become available.
- Train longer at larger image sizes and compare YOLOv8 model sizes.
- Add calibration and confidence thresholds for deployment.
- Evaluate on an independently sourced external counterfeit medicine test set.
- Build a frontend/API integration for wallet connection, batch history, and AI hash submission.
