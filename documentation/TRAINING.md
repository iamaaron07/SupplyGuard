# Training

## Model

The default model is:

```text
yolov8n-cls.pt
```

This is YOLOv8 classification, not object detection.

## Full Training Command

```bash
python -m src.training.train --dataset dataset/prepared --model yolov8n-cls.pt --epochs 30 --imgsz 224 --batch 16 --output-dir runs/classification --run-name supplyguard_yolov8_cls
```

## Configurable Parameters

- `--dataset`
- `--model`
- `--epochs`
- `--imgsz`
- `--batch`
- `--lr0`
- `--seed`
- `--output-dir`
- `--run-name`

## Smoke Training Run

Verified command:

```bash
python -m src.training.train --dataset dataset/prepared --model yolov8n-cls.pt --epochs 1 --imgsz 64 --batch 8 --output-dir runs/classification --run-name smoke_yolov8_cls_abs
```

Output:

```text
runs/classification/smoke_yolov8_cls_abs/weights/best.pt
runs/classification/smoke_yolov8_cls_abs/weights/last.pt
```

Validation top-1 accuracy after one smoke epoch was about `0.697`. This verifies the pipeline, not final model quality.

## Checkpoints and Outputs

Ultralytics saves checkpoints, plots, and training logs under the selected run directory.

## Reproducibility

Use `--seed` for repeatable splitting and training behavior where supported by the underlying libraries.

