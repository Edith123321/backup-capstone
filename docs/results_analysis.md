# SAKA — Results Analysis

How the delivered system measures against the proposal's objective, research
questions, and scope — with honest accounting of what was met and what diverged.

## 1. Main objective

> *"Develop and implement Saka, an AI-driven IoT acoustic triage system for
> early detection and automated severity grading of RHD in pediatric
> populations within low-resource African settings … a cost-effective
> alternative to expensive echocardiographic hardware."*

**Met (as an MVP).** The repository delivers all four technical pillars: an
ESP32 IoT acquisition device (firmware + BLE/WebSocket streaming), a Random
Forest ML pipeline, a Flask API, and a React clinical dashboard — deployed and
verified (see `deployment_plan.md`). Cost-effectiveness is evidenced by the
[Bill of Materials](../iot/schematic/components_list.csv): **US $35.55**, under
the sub-$50 target and far below echocardiography hardware.

## 2. Research questions

| # | Research question | Status | Evidence / caveat |
|---|-------------------|--------|-------------------|
| RQ1 | Differentiate RHD-induced pathology from physiological murmurs? | **Achieved (in-vitro)** | Binary RF classifier, F1 0.984, AUC 0.9995 on held-out test (`model_comparison.csv`). |
| RQ2 | Accuracy vs **WHF echocardiographic** criteria in East Africa? | **Partially met** | Validated against PhysioNet/CirCOR **labels**, *not* WHF echo ground truth on the Gisozi cohort. This linkage is pending the field pilot. |
| RQ3 | Optimize acoustic capture + mitigate rural environmental noise? | **Addressed** | On-device 20–400 Hz band-pass (`Config.h`); 4 kHz mono capture. Field noise robustness not yet quantified. |
| RQ4 | Do 1D→2D Mel spectrograms + temporal gating improve sensitivity/specificity? | **Diverged** | The shipped model is a **Random Forest over 51 time-frequency features** (statistics, MFCCs, spectral, band-power), not a 2D-Mel-spectrogram CNN with temporal gating. MFCCs are mel-derived, but the proposed CNN + gating approach was not the final architecture (RF generalized better on the available data). |

## 3. Clinical performance vs. proposal benchmark

The proposal cites prior art at **sensitivity > 85%, specificity 80%** for
definite RHD. On the held-out test set (n = 64, balanced):

| Metric | SAKA (RF) | Proposal benchmark |
|--------|----------:|-------------------:|
| Sensitivity (Recall) | **96.9%** | > 85% |
| Specificity | **100%** | 80% |
| Accuracy | 98.4% | — |
| AUC-ROC | 0.9995 | — |

**Exceeds the benchmark on paper**, with two honest caveats: (a) the test set is
small (n = 64) and single-source; (b) there is **1 false negative** (the key
residual clinical risk) — see [Clinical Evaluation Report](clinical_evaluation_report.md).

## 4. Engineering result that protects the metrics

A subtle but critical finding: the deployment feature extractor originally
zeroed 28 of the 51 features (all MFCCs + `zcr_std`), so the reported accuracy
would **not** have held in production. The pipeline was re-implemented
numba-free and validated to **100% prediction parity** with the training
(librosa) extractor across 110 real recordings. Without this, the headline
result would have been unachievable on the target hardware.

## 5. Scope linkage

| Proposal scope item | Delivered? |
|---------------------|-----------|
| ESP32-based IoT acquisition hardware | ✅ Firmware + BLE/WebSocket; physical build + CAD are hardware deliverables |
| React-based dashboard MVP | ✅ Screening wizard, triage, longitudinal history, reports |
| ML pipeline (mitral-valve focus) | ✅ Trained RF on mitral-valve dataset |
| Gisozi pilot: ~100 screenings, 6–10 clinicians, echo validation | ⏳ Field activity — not a code artifact; enables the RQ2 WHF linkage |

## 6. Summary
The software/hardware **MVP objective is met and verified**; the system exceeds
the cited accuracy benchmark on a controlled test set. The principal gaps are
**external validation against WHF echo ground truth** (dependent on the field
pilot) and an **architecture divergence** (Random Forest vs. the proposed
CNN + temporal gating), both stated plainly here rather than glossed over.
