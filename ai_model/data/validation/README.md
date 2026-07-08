# `validation/` — held-out validation set (materialised AFTER the validation check)

Populated by **Section 5** of [`../../notebooks/data_imbalance.ipynb`](../../notebooks/data_imbalance.ipynb).

Raw, unaugmented recordings used for model selection / early stopping. Split off at
the **patient level before augmentation**, then written and leakage-checked after
the augmentation step (Section 5 asserts train / validation / test are disjoint).

```
validation/
  normal/   <patient_id>.wav
  rhd/      <patient_id>.wav
  validation_summary.csv
```
