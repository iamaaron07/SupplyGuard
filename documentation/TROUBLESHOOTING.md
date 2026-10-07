# Troubleshooting

## `fatal: not a git repository`

The workspace did not contain a `.git` directory. This is not a pipeline problem. Development proceeded without relying on git status.

## YOLO Weight Download Failed

Initial error:

```text
Download failure for https://github.com/ultralytics/assets/.../yolov8n-cls.pt
```

Cause: the sandbox blocked network access and `yolov8n-cls.pt` was not cached locally.

Solution: rerun the training command with network approval so Ultralytics can download the pretrained classification weights.

## Ultralytics Output Path Was Nested Unexpectedly

Initial run saved under:

```text
runs/classify/runs/classification/...
```

Cause: a relative `project` path was interpreted under Ultralytics' default runs directory.

Solution: `src/training/train.py` now resolves `dataset` and `output_dir` to absolute paths before calling `model.train()`.

## Prediction Image Not Found

Initial error:

```text
FileNotFoundError: dataset/prepared/test/Fake/... does not exist
```

Cause: the manually chosen sample image was not part of the prepared test split.

Solution: select an actual file from `dataset/prepared/test/Fake` or use `--image-dir`.

## Low Smoke-Test Synthetic Accuracy

The one-epoch smoke model achieved 40% synthetic-fake accuracy. This is expected for a tiny CPU sanity run at 64px. Run full training at a larger image size before interpreting model quality.

