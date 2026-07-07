# SAKA RHD Classifier — Clinical Evaluation Report

Evaluation of the SAKA heart-sound classifier against the held-out test set.
All figures are taken from the trained model artifacts in
`ai_model/models/mitral_classifier_v4/` (`model_comparison.csv` and the exported
confusion-matrix / ROC plots).

---

## 1. Model Selection

Five classifiers were trained on the balanced PhysioNet + CirCOR mitral-valve
dataset with a **patient-level split** (segments from one patient never appear
in both train and test, preventing data leakage). Selected model: **Random
Forest** (`best_model.pkl`, `n_estimators=100`).

| Model | Accuracy | Precision | Recall | F1 | AUC |
|-------|---------:|----------:|-------:|----:|----:|
| **Random Forest** | **0.9844** | **1.0000** | **0.9688** | **0.9841** | **0.9995** |
| Gradient Boosting | 0.9531 | 0.9677 | 0.9375 | 0.9524 | 0.9963 |
| Voting Ensemble | 0.9297 | 0.9508 | 0.9063 | 0.9280 | 0.9858 |
| SVM | 0.8906 | 0.9167 | 0.8594 | 0.8871 | 0.9485 |
| Logistic Regression | 0.7188 | 0.7500 | 0.6563 | 0.7000 | 0.7869 |

_Source: `ai_model/models/mitral_classifier_v4/model_comparison.csv`_

---

## 2. Confusion Matrix (Random Forest)

The test set is a **balanced 64 samples** (32 Normal, 32 RHD). The reported
metrics (accuracy 63/64, precision 1.0, recall 31/32) yield:

|                    | Predicted Normal | Predicted RHD |
|--------------------|:----------------:|:-------------:|
| **Actual Normal**  | 32 (TN)          | 0 (FP)        |
| **Actual RHD**     | 1 (FN)           | 31 (TP)       |

- **True Negatives:** 32 &nbsp;•&nbsp; **False Positives:** 0
- **False Negatives:** 1 &nbsp;•&nbsp; **True Positives:** 31

_Plot: `ai_model/models/mitral_classifier_v4/confusion_matrix_Random_Forest.png`_

---

## 3. Metric Interpretation (Clinical Framing)

| Metric | Value | Clinical meaning |
|--------|------:|------------------|
| Accuracy | 98.44% | Overall correct classifications |
| Precision | 100% | No false RHD alarms → no unnecessary referrals in this test set |
| Recall (Sensitivity) | 96.88% | 31 of 32 true RHD cases detected; **1 missed** |
| Specificity | 100% | All healthy patients correctly cleared (0 FP) |
| F1-Score | 0.9841 | Balanced precision/recall |
| AUC-ROC | 0.9995 | Near-perfect class separability |

_ROC curves: `ai_model/models/mitral_classifier_v4/roc_curves.png`_

### Note on the single false negative
As a screening tool feeding referral decisions, **sensitivity is the priority**
(a missed RHD case is more costly than a false alarm). The one false negative
(recall 96.9%) is the key residual risk. Mitigations in the deployed system:
- Screening is **triage support**, not a standalone diagnosis — the Jones triage
  and clinician judgement run in parallel.
- The confidence-weighted severity grader and Markov prognostic model flag
  borderline cases for follow-up even when the binary label is "Normal".
- Recommend threshold tuning toward higher sensitivity for field deployment.

---

## 4. Production Feature-Pipeline Fidelity

Because the deployment backend cannot run librosa/numba, inference uses a
numba-safe NumPy/SciPy reimplementation of the training feature pipeline
(`backend/api/v1/screening/feature_extraction.py`). This port was validated to:
- **49/51 features** matching the librosa oracle to < 1e-4 absolute error;
- **100% prediction agreement** with librosa across 110 real recordings.

This confirms the reported metrics carry over to the deployed inference path
(the earlier extractor, which zeroed 28/51 features, did **not** preserve them).

---

## 5. Limitations & Future Work
- Test set is modest (n=64); a larger multi-site external validation is advised.
- Single-site pilot (Gisozi); generalization across populations/devices untested.
- Binary Normal/RHD head; the 3-grade severity is heuristic (confidence-based),
  not independently trained — a multi-class severity model is future work.
