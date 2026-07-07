# SAKA — Test Suite

Multiple, complementary testing strategies covering the whole stack.

## Layout
| Suite | Marker | What it proves | Needs |
|-------|--------|----------------|-------|
| `unit/` (severity, markov, features) | `unit` | Core logic is correct across inputs/edge cases | backend deps only, fast, offline |
| `unit/test_prediction.py` | `integration` | Trained model works end-to-end; **abnormal WAV → RHD alert**, sensitivity/specificity on real recordings | model artifacts + sample WAVs |
| `functional/` | `functional` | REST endpoints (auth, patients, triage, screening, recordings) | a running API (`TEST_BASE_URL`) |
| `network/` | `network` | CORS, timeouts, rate limiting | running API |
| `performance/` | `performance` | Load / stress / endurance | running API |
| `security/` | `security` | Input validation / auth | running API |

## Install
```bash
pip install -r requirements.txt
pip install -r ../backend/requirements.txt   # numpy/scipy/sklearn/joblib/soundfile
```

## Run
```bash
# Fast, offline unit tests (no server, no network)
pytest unit/ -m unit

# Model deliverable — abnormal WAV triggers RHD alert (needs model + data)
pytest unit/test_prediction.py

# Endpoint tests against a LOCAL backend
TEST_BASE_URL=http://localhost:5001 pytest functional/ -m functional

# Against the deployed backend (default)
pytest functional/ network/ -m "functional or network"
```

`conftest.py` reads `TEST_BASE_URL` (default: the deployed Render URL), so the
same suite runs against local and remote environments.

## Strategy summary
- **Unit** — deterministic, offline; parametrized edge cases (grade matrix,
  stochastic-matrix invariants, MFCC/zcr regression guards).
- **Integration** — real classifier on labelled PhysioNet/CirCOR recordings;
  asserts the RHD alert fires and checks sensitivity/specificity thresholds.
- **Functional / network / security / performance** — black-box tests against a
  deployed environment, so behaviour is validated on the real target stack.
