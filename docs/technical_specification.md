# SAKA (HeartSound AI) — Technical Specification

**System:** AI-driven IoT ecosystem for Rheumatic Heart Disease (RHD) screening
in low-resource settings.
**Version:** 2.0.0
**Scope:** System architecture, data-acquisition, the Numba-safe DSP/feature
pipeline, ML inference, and the clinical decision-support services.

---

## 1. System Architecture

```
[ IoT Stethoscope ] --BLE/WebSocket--> [ React Dashboard ] --HTTPS/REST--> [ Flask API ]
     (ESP32 + INMP441)                    (Vite + MUI)                          |
                                                                                v
                              [ Numba-safe DSP + Random Forest ] <----- [ SQLite Database ]
```

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| Acquisition | ESP32 (WROOM-32) + INMP441 I2S MEMS mic | 4 kHz / 16-bit mono PCG capture; BLE + WebSocket streaming |
| Frontend | React 19 + Vite + MUI | Screening wizard, Jones triage, longitudinal history |
| Backend | Flask 3 (Blueprints), Gunicorn | REST API, auth, inference orchestration |
| DSP / ML | NumPy + SciPy + scikit-learn | Numba-safe feature extraction, Random Forest inference |
| Persistence | SQLite | Patients, triage, recordings, severity history, devices |
| Auth | Google OAuth 2.0 + JWT | Provider authentication |

### API surface (`/api/v1`)
- `auth/google/*` — OAuth login/callback
- `screening/predict` — audio → RHD classification + severity
- `screening/validate`, `screening/history/<patient_id>`
- `database/*` — patients, triage, recordings, devices
- `severity/*`, `prognosis/*` — grading and Markov risk
- `reports/generate`, `reports/download/<file>` — PDF referrals

---

## 2. Data Acquisition (IoT)

Configuration is fixed in `iot/src/Config.h`:

| Parameter | Value |
|-----------|-------|
| Sample rate | 4000 Hz |
| Bit depth | 16-bit |
| Channels | 1 (mono) |
| I2S pins | WS=GPIO25, BCK=GPIO26, DIN=GPIO35 |
| Bandpass (on-device) | 20–400 Hz |
| Transport | BLE (GATT) + WebSocket (port 80) |

4 kHz is chosen because diagnostic heart-sound energy (S1, S2, and pathological
murmurs) lies below ~400 Hz; a 4 kHz rate satisfies Nyquist with margin while
minimizing bandwidth for constrained networks.

---

## 3. The Numba-Safe DSP / Feature Pipeline

### 3.1 Motivation
The classifier (Random Forest) was trained on 51 time-frequency features
extracted with **librosa** (see `ai_model/src/classifier.py`). librosa depends
on **numba/llvmlite**, whose JIT/native build fails on the constrained
deployment target. The backend therefore reimplements the *identical* feature
math in **pure NumPy + SciPy** — no numba, no librosa import — in
`backend/api/v1/screening/feature_extraction.py`.

### 3.2 Signal path
```
WAV --load_audio_safe--> mono float @ 4kHz, 10s --> 51-feature vector --> StandardScaler --> RandomForest
     (soundfile/scipy)                              (feature_extraction.py)   (scaler.pkl)    (best_model.pkl)
```

### 3.3 The 51 features
| Group | Count | Features |
|-------|------:|----------|
| Basic stats | 4 | mean, std, rms, peak |
| Zero-crossing rate | 2 | zcr_mean, zcr_std |
| Spectral | 7 | spec mean/std/max, centroid, centroid_std, bandwidth, rolloff |
| MFCC | 26 | mfcc_0..12 mean + std |
| Mel summary | 4 | mel mean/std/max/energy |
| Tempo | 1 | tempo (BPM) |
| Envelope | 4 | env mean/std/peak/peak_ratio |
| Band power | 3 | 20–80, 80–200, 200–400 Hz power ratios |

### 3.4 Numba-safe equivalents of librosa
| librosa call | Numba-safe replacement |
|--------------|------------------------|
| `librosa.stft` | Manual framing + `numpy.fft.rfft`, periodic Hann, center-pad `'constant'` |
| `librosa.filters.mel` (Slaney) | Pure-NumPy Slaney mel filterbank (matched to 1e-9) |
| `librosa.feature.mfcc` | mel power → `power_to_db` → `scipy.fft.dct(type=2, norm='ortho')` |
| `librosa.amplitude_to_db` / `power_to_db` | NumPy log-scaling with `ref`, `amin`, `top_db` |
| `librosa.feature.zero_crossing_rate` | Frame-based sign-change rate |
| `librosa.beat.beat_track` | Onset-autocorrelation tempo estimate (low-importance feature) |

### 3.5 Validation
The port was validated against a librosa oracle (used only as a reference, not a
runtime dependency):
- **Feature level:** 49/51 features match to < 1e-4 absolute (median relative
  error ~4e-8); only `tempo` (feature-importance rank 49/51) differs materially.
- **Prediction level:** 100% agreement with librosa on 110 real PhysioNet/CirCOR
  recordings; mean confidence delta ~1%.

> Historical note: a prior inline extractor hardcoded all 26 MFCCs and `zcr_std`
> (the 2nd most important feature) to 0, so only 3/51 features were valid. The
> current pipeline resolves this.

---

## 4. ML Inference

- **Model:** Random Forest (`n_estimators=100`), serialized as `best_model.pkl`
  with a `StandardScaler` (`scaler.pkl`), pinned to scikit-learn 1.7.2.
- **Output:** binary class (Normal / RHD) + probability.
- **Severity mapping** (`services/severity_grading.py`): Grade 0 Normal,
  Grade 1 Borderline RHD, Grade 2 Definite RHD — escalated by confidence,
  auscultation point, and triage context.

---

## 5. Clinical Decision Support

- **Jones Triage:** five color-coded urgency levels stored in `triage_records`.
- **Prognostic risk (`services/markov_model.py`):** a 3-state monthly Markov
  chain (Normal → Borderline → Definite) yields a 0–100 risk score, risk level,
  and 24-month progression projection, adjusted by age/treatment/risk factors.
- **Referral engine (`services/report_generator.py`):** color-coded PDF report
  combining AI severity, triage, prognosis, and the real recorded waveform
  (omitted when no audio is stored — never fabricated).

---

## 6. Non-Functional Notes

- **Offline/low-bandwidth:** client offline queue (`services/offlineQueue.js`)
  and an offline-status endpoint support intermittent connectivity.
- **Security:** Google OAuth 2.0 + JWT; CORS restricted to known origins;
  50 MB upload cap; parameterized SQL.
- **Portability:** SQLite + Dockerized backend for local hospital workstations.
