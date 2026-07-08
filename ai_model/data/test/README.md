# `test/` — held-out test set (created BEFORE augmentation)

Populated by **Section 2** of [`../../notebooks/data_imbalance.ipynb`](../../notebooks/data_imbalance.ipynb).

Raw, unaugmented mitral-valve recordings split off at the **patient level before**
any balancing or augmentation runs. Files here must never be augmented — they are
the honest held-out set for final evaluation.

```
test/
  normal/   <patient_id>.wav
  rhd/      <patient_id>.wav
  test_summary.csv
```
