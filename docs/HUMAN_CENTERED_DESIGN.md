# Human-Centered Design — "What If" Scenarios

SAKA is a screening aid used by nurses in low-resource clinics, not a lab
instrument in ideal conditions. A binary Normal/RHD classifier will happily put
a confident label on *anything* you feed it — silence, a crying baby, a
1-second fragment. That is clinically dangerous. This document describes the
guardrails that keep the human in control of the diagnosis.

The core principle: **the AI must fail loudly and helpfully, never silently and
confidently.** Every guardrail below either (a) refuses to run the AI and tells
the user how to fix the recording, or (b) runs the AI but flags the caveat to
the clinician.

## Where the guardrails live

| Layer | File | Responsibility |
|-------|------|----------------|
| On-device SQA (firmware) | [`iot/src/SignalQuality.cpp`](../iot/src/SignalQuality.cpp) | First-line, at-the-source quality checks on the ESP32 (faint/clip/silence/no-beat) |
| Signal Quality gate | [`backend/api/v1/screening/signal_quality.py`](../backend/api/v1/screening/signal_quality.py) | Scenarios 1, 2, 3, 5, 6 — decide if a recording is a gradeable heartbeat |
| Threshold calibration | [`tools/calibrate_sqa.py`](../tools/calibrate_sqa.py) | Re-derive SQA thresholds from real field recordings |
| Prediction route | [`backend/api/v1/screening/heart_sound.py`](../backend/api/v1/screening/heart_sound.py) | Runs SQA before `classifier.predict`; blocks or annotates |
| Encounter route | [`backend/api/v1/screening/encounter_routes.py`](../backend/api/v1/screening/encounter_routes.py) | SQA + clinical red-flag override (Scenario 7) |
| Upload UI | [`frontend_web/.../UploadHeartSound.jsx`](../frontend_web/src/components/Dashboard/UploadHeartSound.jsx) | Shows block messages / soft warnings, disables submit |
| Encounter UI | [`frontend_web/.../NewEncounter.jsx`](../frontend_web/src/components/Dashboard/NewEncounter.jsx) | Renders the clinical override + signal-quality banners |
| Offline resilience | [`frontend_web/.../offlineQueue.js`](../frontend_web/src/services/offlineQueue.js), [`OfflineBanner.jsx`](../frontend_web/src/components/Common/OfflineBanner.jsx) | Scenario 4 — local queue + status banner |
| Device health | [`frontend_web/.../IoTDevices.jsx`](../frontend_web/src/components/Dashboard/IoTDevices.jsx), [`iot/src/Saka_Stethoscope.ino`](../iot/src/Saka_Stethoscope.ino) | Scenario 8 — battery/signal telemetry & record gate |

Tests: [`tests/unit/test_signal_quality.py`](../tests/unit/test_signal_quality.py) encodes each scenario as a named test.

---

## The 8 scenarios

### 1. Garbage Data — "that isn't a heart"
**What if** someone records speech, a crying baby, or music?
**Guardrail — Signal Quality Assessment (Lub-Dub check).** Before the AI runs,
`assess_signal_quality()` measures (a) the *rhythm strength* — the normalised
autocorrelation peak of the heart-band energy envelope in the cardiac-cycle lag
range — and (b) *low-frequency dominance* — the share of 20–1000 Hz energy that
sits below 200 Hz where S1/S2 live. If both are weak, the recording is rejected:
> *"Signal not recognised as a heartbeat. Please ensure the stethoscope is placed directly on the skin over the heart, keep the room quiet, and try again."*

### 2. Diagnostic Threshold — "too short to trust"
**What if** the recording is only 1–2 seconds, or the stethoscope is pulled away?
**Guardrail — Minimum Duration Gate.** 51 features cannot be reliably extracted
from a fragment. Anything shorter than `MIN_DURATION_S` (5 s; the model was
trained on 10 s clips) is hard-blocked *before* feature extraction, avoiding
low-confidence / NaN results:
> *"Recording is only 2.0s — too short for a reliable diagnosis. Please hold the stethoscope steady for the full 10 seconds and try again."*

A recording between 5–10 s is allowed but nudged with a soft `short_recording`
warning.

### 3. Inaudible / Faint Heart — "silence is not Normal"
**What if** a thick chest wall or loose placement produces near-silence?
**Guardrail — Amplitude Calibration.** A flat signal has no murmur, so the model
would call it *Normal* and miss a real condition. We compute loudness in dBFS
and reject anything below `TOO_FAINT_DBFS` (−50 dBFS) or effectively silent:
> *"Sound too faint to analyse. Press the diaphragm more firmly against the skin and check the device connection, then re-record."*

### 4. Infrastructure Failure — offline mid-screening
**What if** the clinic's Wi-Fi/3G drops while the nurse is screening?
**Guardrail — Optimistic UI & Local Queue.** `offlineQueue.js` persists requests
to browser storage and retries them when connectivity returns. The global
[`OfflineBanner`](../frontend_web/src/components/Common/OfflineBanner.jsx) shows
live status, and the upload flow falls back to the queue on network failure:
> *"💾 Saved locally. Prediction pending (waiting for internet). You can continue to the next patient."*

The nurse never loses a patient's data.

### 5. Tachycardia — fast heart, overlapping S1/S2
**What if** a febrile or frightened child's heart beats at 160 BPM, so S1 and S2
overlap and murmur segmentation fails?
**Guardrail — Physiological Outlier Alert.** SQA estimates heart rate from the
envelope autocorrelation. Outside the paediatric range (`HR_MIN_BPM`–`HR_MAX_BPM`,
60–140), it still classifies but attaches a soft warning:
> *"High heart rate detected (~165 BPM). Is the child calm? If they are crying or upset, please settle them and re-record for the most accurate AI analysis."*

### 6. Environmental Chaos — generators, traffic
**What if** loud ambient noise gets mistaken for a blowing murmur?
**Guardrail — Ambient Noise Flag.** SQA uses the high-band (200–1000 Hz) energy
ratio as a noise proxy. Above `NOISE_RATIO_WARN`, it classifies but warns:
> *"High background noise detected — accuracy may be reduced. Try to find a quieter space and re-record if possible."*

### 7. Conflicting Data — the ultimate override
**What if** triage says high-risk (joint pain + fever, Jones Red/Orange) but the
AI says *Normal Heart*?
**Guardrail — Clinical Red-Flag Override.** `clinical_red_flag_override()` in the
encounter route detects this exact conflict and emits an un-ignorable override
that takes priority over the AI recommendation. The UI renders it *above* the
success message and **suppresses the auto-redirect** so it cannot be missed:
> *"The AI detected a normal rhythm, but the clinical symptoms are HIGH RISK (Jones triage: Red). Do NOT rely on the AI result — refer this patient to a specialist regardless."*

This is the strongest human-centered move: the clinician's judgement wins.

### 8. Device Health — a dying battery corrupts audio
**What if** the ESP32 battery is at 5%, causing BLE to jitter and drop packets,
adding clicks that look like murmurs?
**Guardrail — Stethoscope Status Bar.** The firmware
(`getDeviceStatus()` → `readBatteryPercent()`) now reports `battery_percent`,
`battery_low`, and `rssi`. The dashboard shows a live battery/signal card and
**greys out the Record button** below `BATTERY_CRITICAL_PERCENT` (15%):
> *"Charge device to ensure signal integrity."*

---

## Response contract

Both `/api/v1/screening/predict` and `/api/v1/encounter` return a
`signal_quality` object; the encounter also returns `clinical_override`.

```jsonc
// Blocked (hard gate) — the AI did NOT run
{
  "success": false,
  "blocked": true,
  "prediction": null,
  "signal_quality": {
    "ok": false, "blocked": true, "code": "too_short",
    "title": "Recording too short",
    "message": "Recording is only 2.0s — too short ...",
    "quality_score": 20,
    "warnings": [],
    "metrics": { "duration_s": 2.0, "rms_dbfs": -3.0, "estimated_bpm": 62, ... }
  }
}

// Passed with a soft warning — the AI ran, caveat attached
{
  "success": true,
  "blocked": false,
  "prediction": "Normal",
  "confidence": 0.71,
  "probabilities": { "Normal": 0.71, "RHD": 0.29 },
  "signal_quality": {
    "ok": true, "blocked": false, "code": "ok", "quality_score": 88,
    "warnings": [
      { "code": "heart_rate_outlier", "title": "Unusual heart rate",
        "message": "High heart rate detected (~165 BPM)..." }
    ]
  }
}

// Encounter with clinical override (Scenario 7)
{
  "clinical_override": {
    "active": true, "priority": "OVERRIDE",
    "title": "⚠️ Clinical override: refer regardless of AI",
    "message": "The AI detected a normal rhythm, but ... HIGH RISK ...",
    "action": "Refer to a specialist / cardiologist regardless of AI result"
  }
}
```

## Defense in depth: on-device SQA (firmware)

The backend gate is authoritative, but a bad recording shouldn't have to travel
to the cloud to be caught. [`iot/src/SignalQuality.cpp`](../iot/src/SignalQuality.cpp)
runs a cheap, streaming subset of the same checks *on the ESP32* while audio is
captured — loudness (faint), clipping/jitter, silence, minimum duration, and a
beat-activity proxy (a threshold-crossing Lub-Dub presence test, no FFT). During
a recording the device broadcasts a `signal_quality` message roughly once a
second (and a final summary on stop); [`IoTDevices.jsx`](../frontend_web/src/components/Dashboard/IoTDevices.jsx)
shows the nurse instant "too faint / no heartbeat / clipping" feedback before
anything is uploaded. Thresholds live in [`Config.h`](../iot/src/Config.h)
(`SQA_*`) and mirror the backend values.

Three layers now guard every recording: **device → backend gate → clinical override.**

## Tuning & calibration

All thresholds are named constants — in `signal_quality.py` (durations, dBFS
floor, rhythm/low-freq/noise ratios, HR range), in `Config.h` (`SQA_*`,
`BATTERY_CRITICAL_PERCENT`). They ship as conservative defaults.

**Calibrate them from real data** with the harness:

```bash
# Profile known-good clips (all real heartbeats) and see what the current
# gate would wrongly block:
python tools/calibrate_sqa.py ai_model/data/test

# Separation mode — once you collect bad-quality samples, arrange them as
# quality-named subfolders (good/ faint/ noise/ garbage/ short/) and re-run:
python tools/calibrate_sqa.py path/to/labeled_recordings --out report.json
```

The harness reuses the real `signal_quality.py` functions (so it measures
exactly what the gate measures), reports the per-class metric distributions,
recommends thresholds as safe percentiles, and — the key number — tells you what
fraction of your *good* recordings the current thresholds reject.

> Calibration already earned its keep: running it against the 86 real clips in
> `ai_model/data/test` showed the original synthetic-tuned cutoffs (`rhythm 0.30`,
> `low_freq 0.55`) wrongly blocked **9.3%** of genuine heartbeats. Loosening them
> to `0.15` / `0.45` cut that to **1.2%** while still rejecting white noise,
> silence and fragments (verified by `tests/unit/test_signal_quality.py`).
