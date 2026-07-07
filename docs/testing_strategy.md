# SAKA — Testing Strategy

Multiple complementary testing strategies spanning the ML core, the API, the
network layer, and the deployed environment. The runnable suite lives in
[`tests/`](../tests/) (see `tests/README.md` to run).

## 1. Strategy matrix

| Strategy | Layer | Location | Inputs / edge cases exercised |
|----------|-------|----------|-------------------------------|
| **Unit** | Core logic | `tests/unit/test_severity_grading.py`, `test_markov_model.py`, `test_feature_extraction.py` | Parametrized grade matrix; stochastic-matrix invariants; treatment effect; MFCC/`zcr_std` regression guards; NaN/finite checks |
| **Integration (model)** | Trained classifier + DSP | `tests/unit/test_prediction.py` | Real RHD/Normal recordings; **abnormal WAV → RHD alert**; sensitivity & specificity thresholds |
| **Functional** | REST API | `tests/functional/` | Auth, patients, triage calc, screening, recordings — valid + invalid payloads, status-code contracts |
| **Network** | Transport | `tests/network/` | CORS preflight, timeouts, rate limiting |
| **Security** | Input / auth | `tests/security/` | Data validation, JWT/authorization |
| **Performance** | Load | `tests/performance/` | Load, stress, endurance |

## 2. Different inputs & edge cases (evidence)

- **Grade matrix** (`@pytest.mark.parametrize`): `Normal@0.99→0`, `RHD@0.99→2`,
  `RHD@0.55→1`, case-insensitive labels — boundary behaviour of the grader.
- **Auscultation escalation**: borderline RHD at the mitral point escalates to
  Grade 2 (clinical-weight edge case).
- **Markov invariants**: every transition-matrix row sums to 1; steady state is
  a valid distribution; secondary prophylaxis lowers definite-RHD probability.
- **Regression guards**: MFCCs and `zcr_std` must be non-zero (locks in the
  feature-parity fix so the old 28-zeroed-features bug can never silently return).
- **The core deliverable**: `test_abnormal_wav_triggers_rhd_alert` asserts a
  clearly-abnormal recording is flagged RHD; `test_rhd_sensitivity_on_sample`
  and `test_normal_specificity_on_sample` check aggregate performance on real
  labelled PhysioNet/CirCOR WAVs.

## 3. Across hardware/software environments

- **Software parity**: the numba-free extractor was validated to **100%
  prediction agreement** with the librosa training pipeline on 110 recordings —
  proving results transfer from the training environment to the constrained
  deployment environment (no numba/llvmlite).
- **Deployment environment**: the backend was exercised in a clean
  Render-equivalent venv (`gunicorn app:app`) — boot, health, model load, live
  prediction, and PDF generation all verified (see `deployment_plan.md §6`).
- **Environment-portable API tests**: `tests/conftest.py` reads `TEST_BASE_URL`,
  so the functional/network suites run unchanged against **local** or **deployed
  (Render)** backends.
- **Device**: the ESP32 streams 4 kHz PCG over BLE/WebSocket; the dashboard
  ingests it through the same prediction path used by file upload.

## 4. Results

- **25 unit + integration tests pass** (20 unit, 5 model integration).
- Command: `pytest tests/unit/` (fast, offline for units; model tests need the
  serialized artifacts + sample data, both in-repo).

## 5. Gaps / future testing
- Automated **end-to-end UI** tests (Playwright) for the React flows.
- **Field performance** under simulated 2G/3G (network-resilience log).
- **Hardware-in-the-loop** tests with the physical ESP32 stethoscope.
