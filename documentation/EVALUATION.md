# Evaluation

## Metrics

Evaluation calculates:

- accuracy
- precision
- recall
- F1-score
- confusion matrix
- unseen AI-generated synthetic-fake accuracy
- unseen AI-generated synthetic-fake precision, recall, and F1

## Command

```bash
python -m src.evaluation.evaluate --model runs/classification/supplyguard_yolov8_cls/weights/best.pt --dataset dataset/prepared --output-dir runs/evaluation/supplyguard_yolov8_cls --imgsz 224
```

## Outputs

The evaluator writes:

```text
metrics.csv
classification_report.txt
confusion_matrix.png
test_predictions.csv
synthetic_fake_predictions.csv
```

The synthetic-fake metrics are calculated only on `dataset/prepared/synthetic_test/Fake`, whose sources are held-out `dataset/prepared/test/Real` images. This directory is outside the YOLO train, validation, and test directories.

## Smoke-Test Results

Command used:

```bash
python -m src.evaluation.evaluate --model runs/classification/smoke_yolov8_cls_abs/weights/best.pt --dataset dataset/prepared --output-dir runs/evaluation/smoke_yolov8_cls_abs --imgsz 64
```

Actual metrics:

- overall accuracy: 0.68
- fake precision: 0.5370
- fake recall: 0.8056
- fake F1: 0.6444
- real precision: 0.8478
- real recall: 0.6094
- real F1: 0.7091
- synthetic fake accuracy: 0.40

The metrics above are from the earlier augmentation-based smoke run and are not results for the new Diffusers generator. New Diffusers results must be generated and evaluated after installing the model dependencies.

## Interpretation

The smoke model learned enough to verify end-to-end training and inference, but it is not a production-quality classifier. The synthetic-fake accuracy shows that full training and stronger synthetic generation are still needed.

## Limitations

The test data comes from the same source dataset, although synthetic test sources are separated from synthetic training sources. A stronger evaluation should include an external dataset and more synthetic-fake categories. The most important research result is unseen AI-generated synthetic-fake accuracy; it must be measured rather than assumed.

