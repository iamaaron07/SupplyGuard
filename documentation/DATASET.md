# Dataset

## Source Dataset

The project expects a fake-vs-real medicine package image dataset with:

```text
dataset/Fake
dataset/Real
```

The current dataset matches that structure.

## Classes

- `Fake`: existing counterfeit or fake medicine package images
- `Real`: genuine medicine package images

Class ids:

- `0 = Fake`
- `1 = Real`

## Validation Results

Validation command:

```bash
python -m src.data.validate_dataset --dataset dataset --report runs/dataset_validation.csv
```

Results:

- `Fake`: 240 valid, 0 invalid
- `Real`: 421 valid, 0 invalid
- Total: 661 valid, 0 invalid

Non-image files such as `desktop.ini` are ignored.

## Prepared Folder

Preparation writes to:

```text
dataset/prepared/
```

This avoids overwriting the existing raw dataset and existing split folders.

## Split Counts

Prepared counts from the verified run:

| Split | Class | Count |
| --- | --- | ---: |
| train | Fake | 462 |
| train | Real | 294 |
| val | Fake | 36 |
| val | Real | 63 |
| test | Fake | 36 |
| test | Real | 64 |
| synthetic_test | Fake | 30 |

`train/Fake` includes original fake images plus synthetic fake images generated from training real images.

## Synthetic Image Labels

All generated synthetic images are labelled `Fake`.

## Leakage Prevention

Synthetic generation happens after splitting:

- training synthetic images are generated from training real images only
- synthetic-fake test images are generated from test real images only
- synthetic-fake test images are not included in training

This keeps evaluation from being artificially easy.

