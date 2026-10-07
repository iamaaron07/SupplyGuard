# Development Notes

## Initial Project Goal

Build the AI/ML component and a simple blockchain provenance layer for SupplyGuard. The frontend, database, and API remain out of scope.

## Blockchain Implementation

The existing blockchain implementation uses `contracts/SupplyGuardLedger.sol`. It provides:

- owner-controlled manufacturer and participant authorization
- batch creation with a manufactured history record
- append-only supply-chain events for packaging, warehouse, distributor, retailer, and corrections
- AI verification records with `REAL`/`FAKE`, confidence basis points, and image/verification hashes
- duplicate hash rejection, history getters, emitted events, and linked `previousRecordId` values

The implementation was retained rather than replaced. The contract deliberately stores hashes instead of image bytes and has no mutation or deletion operation for history records.

## Blockchain Validation

The Hardhat suite covers deployment, authorization, batch creation, supply-chain and verification events, invalid verdict/confidence values, duplicate event and verification hashes, complete history retrieval, and append-only correction behavior. Local deployment uses `npx hardhat node` followed by `npm run deploy:local`. Sepolia settings are read from `.env` and never contain a private key in source control.

## Architecture Decision

The model is YOLOv8 classification, not YOLO object detection. The task is package-level binary classification, so bounding boxes are unnecessary.

Class mapping:

- `0 = Fake`
- `1 = Real`

## Why YOLOv8 Classification

YOLOv8 classification was selected because it is lightweight, well-supported, easy to train, and produces direct class confidence scores. `yolov8n-cls.pt` is the default because it is small enough for local CPU smoke testing.

## Dataset Preparation Decisions

The existing project contained only `dataset/`. It had raw `dataset/Fake` and `dataset/Real` folders plus existing `train`, `val`, and `test` folders.

The existing split folders were not overwritten. A fresh prepared dataset is created under `dataset/prepared/` to avoid damaging useful existing data.

## Kaggle Medicine Dataset

The dataset is treated as the Kaggle fake-vs-real medicine package image dataset requested by the project brief. The pipeline expects this structure:

```text
dataset/Fake
dataset/Real
```

## Synthetic Data Generation Approach

The implemented generator now uses a local Diffusers image-to-image pipeline for AI-generated synthetic counterfeit variants. The earlier augmentation path remains available as an explicit offline comparison fallback.

Implemented transformations:

- brightness, contrast, and color shifts
- rotation and scaling
- small perspective changes
- shadow gradients
- blur
- noise
- JPEG compression

Synthetic outputs are labelled `Fake`.

## How Synthetic Images Were Created

During preparation:

- synthetic training fakes were generated from `dataset/prepared/train/Real`
- synthetic test fakes were generated from `dataset/prepared/test/Real`
- synthetic test fakes were stored separately in `dataset/prepared/synthetic_test/Fake`

This prevents synthetic variants of the same source image from appearing in both train and test.

## Problems Encountered

1. The workspace was not a git repository, so git status could not be used to inspect change state.
2. The first YOLO smoke training run failed because `yolov8n-cls.pt` was not cached and the sandbox blocked downloading from GitHub.
3. Ultralytics initially nested a relative output path under its default run directory.
4. The first manual prediction smoke test used a filename that was not present in the prepared test split.

## Diagnosis and Solutions

1. The git command returned `fatal: not a git repository`. Development continued without git assumptions.
2. The training traceback showed failed download attempts for `https://github.com/ultralytics/assets/.../yolov8n-cls.pt`. The command was rerun with approval for network access, and the weights downloaded successfully.
3. The training output showed `save_dir` under `runs/classify/runs/classification/...`. The training script was patched to resolve `dataset` and `output_dir` as absolute paths before calling Ultralytics.
4. The prediction traceback showed `FileNotFoundError`. An actual test image path was selected from `dataset/prepared/test/Fake`, and prediction succeeded.

## Dataset Imbalance

The raw dataset has 421 real images and 240 fake images. Synthetic fakes are added to the training fake class to improve fake-class coverage. The prepared training split has 294 real images and 462 fake images after synthetic generation.

## Data Leakage Considerations

Synthetic images are generated after splitting. Training synthetic fakes come only from training real images. Synthetic-fake evaluation images come only from test real images and are kept outside the YOLO train/val/test folders.

## Training Problems

No code-level training failure remained after downloading weights and fixing output path handling. The smoke training ran on CPU for one epoch at 64px.

## Overfitting and Performance Issues

The smoke model is not expected to generalize strongly. It achieved 68% overall test accuracy and 40% synthetic-fake accuracy. Longer training at a larger image size is needed before judging true model quality.

## Evaluation Decisions

Evaluation calculates sklearn metrics from actual predictions and saves:

- `metrics.csv`
- `classification_report.txt`
- `confusion_matrix.png`
- `test_predictions.csv`
- `synthetic_fake_predictions.csv`

Metrics are not fabricated.

## Final Architecture

```text
Raw dataset -> validation -> leakage-aware split -> synthetic fake generation
-> YOLOv8 classification training -> evaluation -> prediction

Supply-chain actors -> SupplyGuardLedger -> append-only batch history
AI prediction + image hash -> AI verification record -> provenance audit trail
```

## Security Considerations

- Private keys are supplied through environment variables and are not hard-coded.
- Only authorized manufacturers can create batches; only authorized participants can append events.
- Zero hashes, duplicate hashes, invalid verdicts, and confidence above `10000` basis points are rejected.
- The ledger does not expose delete or update methods. Corrections are new records linked to the previous record.
- Wallet authorization is a simple owner-controlled model and should be replaced with stronger identity and key-management controls for production.

## Lessons Learned

Keeping generated data in `dataset/prepared/` protects the original dataset. Synthetic test data should be created from held-out source images. Local smoke tests are useful for catching path, dependency, and model-loading problems before full training.

## Future Improvements

- Compare additional open-source diffusion models and prompts for counterfeit variants.
- Track product or package IDs to support grouped splitting.
- Train for more epochs at `224` or higher image size.
- Evaluate on an external dataset collected from a different source.

