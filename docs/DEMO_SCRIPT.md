# SAKA — Human-Centered Design Demo Script (live video)

The core message to open and close with:

> **"The AI is a screening aid, not the final word. Every guardrail here keeps the
> clinician in control — the system fails loudly and helpfully, never silently
> and confidently."**

## Prep (before you hit record)
1. **Wake the backend first.** Open the app once and wait ~30s (free-tier cold
   start). You'll see a *"Server is waking up — retrying…"* toast — that itself
   is a good thing to show, but do it before the main demo so the rest is snappy.
2. **Demo audio pack** is in [`docs/demo_assets/`](demo_assets/) — each file is
   engineered to trigger exactly one guardrail (verified against the real gate):
   | File | Triggers |
   |------|----------|
   | `01_normal_heartbeat.wav` | passes → predicts **Normal** (baseline + override demo) |
   | `02_too_short.wav` | Scenario 2 — too short |
   | `03_silent_faint.wav` | Scenario 3 — too faint |
   | `04_not_a_heartbeat.wav` | Scenario 1 — not a heartbeat |
   | `05_tachycardia_165bpm.wav` | Scenario 5 — high heart rate (warning) |
   | `06_noisy_environment.wav` | Scenario 6 — noisy environment (warning) |
3. Log in, land on the dashboard. Have the **Recordings → Upload** modal and the
   **New Encounter** page ready to switch between.

Toasts appear top-right; blocked recordings also show an inline red panel.

---

## The 8 scenarios — what to do, what they'll see

### 1. Garbage Data — "that isn't a heart"
- **Concept:** a binary model will force Normal/RHD onto *anything* — speech, a
  crying baby, music. That's dangerous.
- **Do:** Upload → select patient → choose `04_not_a_heartbeat.wav` → **Analyze**.
- **Shows:** red block + toast — *"Signal not recognised as a heartbeat (no
  regular Lub-Dub rhythm)…"*. The AI never runs; the Upload button is disabled.
- **Say:** "Before the model sees anything, a signal-quality check looks for the
  Lub-Dub rhythm and low-frequency heart energy. No heartbeat → we refuse to
  guess." *(Bonus authenticity: talk into your laptop mic-recorded clip instead.)*

### 2. Diagnostic Threshold — "too short to trust"
- **Concept:** you can't extract 51 reliable features from a 1–2s fragment.
- **Do:** Upload `02_too_short.wav` → **Analyze**.
- **Shows:** *"Recording is only 2.0s — too short for a reliable diagnosis. Please
  hold the stethoscope steady for the full 10 seconds."*
- **Say:** "Minimum-duration gate — anything under 5 seconds is blocked before
  the AI, so we never produce a low-confidence or NaN result."

### 3. Inaudible / Faint Heart — "silence is not Normal"
- **Concept:** a flat/quiet signal has no murmur, so the model would call it
  *Normal* and miss real disease.
- **Do:** Upload `03_silent_faint.wav` → **Analyze**.
- **Shows:** *"Sound too faint to analyse. Press the diaphragm more firmly…"*
- **Say:** "We check loudness in dBFS. Below threshold we block — 'quiet' must
  never be mistaken for 'healthy'."

### 4. Infrastructure Failure — offline mid-screening
- **Concept:** clinic Wi-Fi/3G drops; the nurse must not lose the patient.
- **Do:** Open DevTools → **Network tab → set to "Offline"** (or turn off Wi-Fi).
  Then upload `01_normal_heartbeat.wav` and submit.
- **Shows:** the amber **offline banner** at the top of the dashboard, and a toast
  *"💾 Saved locally — will sync when the connection returns."* Set the network
  back to **Online** and show the banner switch to *"syncing…"*.
- **Say:** "Recordings queue in the browser and auto-sync when connectivity
  returns — the nurse moves to the next patient with zero data loss."

### 5. Tachycardia — fast heart, overlapping S1/S2
- **Concept:** a frightened/febrile child at 160+ BPM makes S1/S2 overlap.
- **Do:** Upload `05_tachycardia_165bpm.wav` → **Analyze**.
- **Shows:** analysis **runs**, plus a warning toast — *"High heart rate detected
  (~165 BPM). Is the child calm? If crying, settle them and re-record."*
- **Say:** "This is a *soft* warning — we still classify, but flag that the rate
  is outside the paediatric range so the clinician weighs the result carefully."

### 6. Environmental Chaos — generator / traffic noise
- **Do:** Upload `06_noisy_environment.wav` → **Analyze**.
- **Shows:** analysis runs + warning — *"High background noise detected —
  accuracy may be reduced. Try to find a quieter space."*
- **Say:** "We measure how much energy sits above the heart band as a noise
  proxy, and warn without blocking."

### 7. Conflicting Data — the Clinical Red-Flag Override ⭐ (the headline)
- **Concept:** triage says HIGH RISK but the AI says Normal. The nurse must not
  trust the AI and send a sick child home.
- **Do:** Go to **New Encounter**. Enter a patient. In **triage**, enter
  high-risk vitals so Jones scores Orange/Red, e.g.:
  - Respiratory rate **32**, SpO₂ **88**, Temperature **39.6**, Heart rate **130**
  - Symptoms: *"joint pain, fever"*
  - (RR 32 → +4, SpO₂ 88 → +2, Temp 39.6 → +3, HR 130 → +2 = **11 → Orange**;
    push HR 145 / SpO₂ 84 for **Red**.)
  Attach `01_normal_heartbeat.wav` (predicts **Normal**) → **Complete Encounter**.
- **Shows:** the AI reports **Normal**, but a bold red **override** appears and an
  un-dismissable toast: *"The AI detected a normal rhythm, but the clinical
  symptoms are HIGH RISK (Jones triage: …). Do NOT rely on the AI result — refer
  this patient to a specialist regardless."* Auto-redirect is **suppressed** so it
  can't be missed.
- **Say:** "This is the most important human-centered move: when clinical judgment
  and AI disagree, the human wins. High-risk triage overrides a normal AI result."

### 8. Device Health — a dying battery corrupts audio
- **Concept:** a low ESP32 battery makes Bluetooth jitter and drop packets,
  adding clicks that can look like murmurs.
- **Do:** Go to the **IoT Devices** tab. Show the **Battery / Signal** status card
  (updates live from the stethoscope's telemetry).
- **Shows:** when battery < 15%, the **Record button greys out** with *"Charge
  device to ensure signal integrity."* If you can't drain the battery on camera,
  narrate the card and the guard.
- **Say:** "The dashboard always shows device battery and signal. On a dying
  battery we block recording rather than capture corrupted audio."

---

## Bonus to mention: cold-start resilience
When the free-tier backend has been idle, the first action shows *"Server is
waking up — retrying…"* and then succeeds — instead of a cryptic error. Point at
it if it appears: "graceful degradation for real-world low-resource infra."

## Suggested running order (smooth flow, ~5–7 min)
1. Open + wake (mention resilience) → 2. Upload a **normal** clip (happy path,
predicts Normal) → 3. **Garbage** → 4. **Too short** → 5. **Faint** →
6. **Tachycardia** → 7. **Noisy** → 8. **Offline** (DevTools) →
9. **Clinical override** (New Encounter — the finale) → 10. **Device health** card.

Close on the override + the opening line: *the human stays in control.*

## Backup if the live backend is slow on camera
Run the frontend locally (`cd frontend_web && npm run dev` → http://localhost:5173)
pointing at the same backend — identical behaviour, no HTTPS quirks, and Bluetooth
device streaming also works there.
