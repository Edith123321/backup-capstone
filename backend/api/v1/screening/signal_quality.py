# backend/api/v1/screening/signal_quality.py
"""
Signal Quality Assessment (SQA) for the SAKA heart-sound classifier.

This is the *human-centered guardrail* that runs BEFORE the AI classifier. The
binary Normal/RHD model will happily force a label onto any 51-feature vector we
hand it — even one extracted from speech, silence, or a 1-second fragment. That
is clinically dangerous. This module inspects the raw waveform first and decides
whether the recording is even a gradeable heartbeat, returning plain-language
guidance the nurse can act on instead of a misleading diagnosis.

It is pure NumPy + SciPy (no numba/librosa) to match feature_extraction.py and
stay buildable on the deployment target.

Scenarios covered (see docs/HUMAN_CENTERED_DESIGN.md):
    1. Garbage data      -> is this even a heartbeat? (Lub-Dub rhythm check)
    2. Diagnostic gate   -> is the recording long enough? (duration gate)
    3. Inaudible/faint    -> is it loud enough to grade? (RMS calibration)
    5. Tachycardia       -> is the heart rate physiologically plausible?
    6. Environmental chaos -> is the recording drowned in ambient noise?

A HARD failure (blocked=True) means "do not run the AI, tell the user why."
A SOFT warning means "run the AI, but flag reduced confidence to the clinician."
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

# ---------------------------------------------------------------------------
# Tunable thresholds (documented so clinicians/engineers can calibrate them).
# ---------------------------------------------------------------------------
SR = 4000

# Scenario 2 — minimum gradeable duration. The model was trained on 10 s clips;
# below MIN we cannot reliably extract the 51 features, so we hard-block.
RECOMMENDED_DURATION_S = 10.0
MIN_DURATION_S = 5.0

# Scenario 3 — loudness. RMS is reported in dBFS (0 = full scale, more negative
# = quieter). Below TOO_FAINT we cannot trust "no murmur" == "normal".
TOO_FAINT_DBFS = -50.0
NEAR_SILENCE_PEAK = 1e-3          # effectively flat-line / disconnected device

# Scenario 1 — "is this a heartbeat?". Heart sounds are quasi-periodic and
# concentrate energy at low frequencies. We require BOTH a periodic envelope and
# low-frequency dominance; speech/music/crying fail one or both.
# CALIBRATED against ai_model/data/test (86 real clips) via tools/calibrate_sqa.py:
# the original synthetic-validated cutoffs (0.55 / 0.30) wrongly blocked ~9% of
# genuine heartbeats, so they were loosened toward the real "good" distribution
# (low_freq p5≈0.46, rhythm p5≈0.06) while still rejecting white noise
# (rhythm≈0.09, low_freq≈0.18 — both remain well below the gate).
LOW_FREQ_BAND = (20.0, 200.0)     # S1/S2 live here
LOW_FREQ_ENERGY_MIN = 0.45        # fraction of 20-1000 Hz energy that must sit <200 Hz
RHYTHM_STRENGTH_MIN = 0.15        # normalised autocorrelation peak in cardiac-lag range

# Scenario 5 — plausible paediatric heart rate. Outside this we still classify
# but warn: fast/overlapping S1-S2 degrades murmur segmentation.
HR_MIN_BPM = 60.0
HR_MAX_BPM = 140.0

# Scenario 6 — ambient noise. Energy leaking above the heart band is our noise
# proxy; a poor ratio means a generator/traffic/room is competing with the heart.
NOISE_RATIO_WARN = 0.45           # high-band / total energy above this -> noisy


@dataclass
class SignalQualityReport:
    """Structured, UI-ready verdict on a recording's fitness for the AI."""
    ok: bool                       # safe to run the classifier
    blocked: bool                  # a hard gate failed -> DO NOT classify
    code: str                      # machine code of the primary issue
    title: str                     # short headline for the UI
    message: str                   # plain-language, action-oriented guidance
    quality_score: int             # 0-100 overall gradeability
    warnings: List[Dict] = field(default_factory=list)   # soft flags (still classify)
    metrics: Dict = field(default_factory=dict)          # raw numbers for transparency

    def to_dict(self) -> Dict:
        return {
            'ok': self.ok,
            'blocked': self.blocked,
            'code': self.code,
            'title': self.title,
            'message': self.message,
            'quality_score': self.quality_score,
            'warnings': self.warnings,
            'metrics': self.metrics,
        }


# ---------------------------------------------------------------------------
# Low-level signal helpers (numba-free).
# ---------------------------------------------------------------------------
def _bandpass(y: np.ndarray, low: float, high: float, sr: int) -> np.ndarray:
    """Zero-phase Butterworth band-pass; degrades gracefully on short clips."""
    nyq = sr / 2.0
    low_n = max(low / nyq, 1e-4)
    high_n = min(high / nyq, 0.999)
    if high_n <= low_n:
        return y
    try:
        b, a = butter(4, [low_n, high_n], btype='band')
        # filtfilt needs len(y) > 3*max(len(a),len(b)); guard tiny inputs.
        if len(y) <= 3 * max(len(a), len(b)):
            return y
        return filtfilt(b, a, y)
    except Exception:
        return y


def _band_energy(y: np.ndarray, low: float, high: float, sr: int) -> float:
    """Energy in a frequency band via a single rFFT."""
    fft = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(len(y), 1.0 / sr)
    power = np.abs(fft) ** 2
    mask = (freqs >= low) & (freqs < high)
    return float(np.sum(power[mask]))


def _envelope(y: np.ndarray, sr: int) -> np.ndarray:
    """Smoothed Shannon-energy envelope of the heart-band signal."""
    band = _bandpass(y, LOW_FREQ_BAND[0], LOW_FREQ_BAND[1], sr)
    band = band / (np.max(np.abs(band)) + 1e-9)
    # Shannon energy emphasises S1/S2 over background hiss.
    shannon = -(band ** 2) * np.log(band ** 2 + 1e-9)
    win = max(1, int(0.05 * sr))            # 50 ms smoothing
    env = np.convolve(shannon, np.ones(win) / win, mode='same')
    env = env - np.min(env)
    return env / (np.max(env) + 1e-9)


def _rhythm_strength_and_bpm(env: np.ndarray, sr: int):
    """
    Measure how periodic the envelope is and estimate heart rate from it.

    Returns (strength, bpm) where strength is the normalised autocorrelation
    peak (0-1) within the plausible cardiac-cycle lag range, and bpm is derived
    from that dominant lag (0 if none found).
    """
    env = env - np.mean(env)
    if np.allclose(env, 0):
        return 0.0, 0.0
    ac = np.correlate(env, env, mode='full')[len(env) - 1:]
    ac = ac / (ac[0] + 1e-9)                 # normalise so lag-0 == 1

    # Cardiac cycle (S1->S1) for 40-200 BPM -> lag 0.3 s to 1.5 s.
    lag_lo = int(0.30 * sr)
    lag_hi = min(len(ac) - 1, int(1.5 * sr))
    if lag_hi <= lag_lo:
        return 0.0, 0.0

    segment = ac[lag_lo:lag_hi + 1]
    peaks, _ = find_peaks(segment)
    if len(peaks) == 0:
        return 0.0, 0.0
    best = peaks[np.argmax(segment[peaks])]
    strength = float(segment[best])
    lag = lag_lo + best
    bpm = 60.0 * sr / lag
    return max(0.0, strength), float(bpm)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------
def assess_signal_quality(y: np.ndarray, sr: int = SR) -> SignalQualityReport:
    """
    Inspect a loaded mono waveform and return a SignalQualityReport.

    The caller (the /predict and /encounter routes) uses `blocked` to decide
    whether to run the classifier at all, and `warnings` to annotate a result
    that was produced under sub-optimal conditions.
    """
    y = np.asarray(y, dtype=float).flatten()
    duration = len(y) / float(sr) if sr else 0.0

    # --- metrics we always compute -----------------------------------------
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    rms = float(np.sqrt(np.mean(y ** 2))) if len(y) else 0.0
    rms_dbfs = 20.0 * np.log10(rms + 1e-9)

    low_e = _band_energy(y, LOW_FREQ_BAND[0], LOW_FREQ_BAND[1], sr) if len(y) > 16 else 0.0
    total_e = _band_energy(y, LOW_FREQ_BAND[0], 1000.0, sr) if len(y) > 16 else 0.0
    high_e = _band_energy(y, LOW_FREQ_BAND[1], 1000.0, sr) if len(y) > 16 else 0.0
    low_ratio = low_e / (total_e + 1e-9)
    noise_ratio = high_e / (total_e + 1e-9)

    env = _envelope(y, sr) if len(y) > sr // 2 else np.zeros(1)
    rhythm, bpm = _rhythm_strength_and_bpm(env, sr)

    metrics = {
        'duration_s': round(duration, 2),
        'rms_dbfs': round(rms_dbfs, 1),
        'peak_amplitude': round(peak, 4),
        'estimated_bpm': round(bpm, 0),
        'low_freq_energy_ratio': round(low_ratio, 3),
        'noise_ratio': round(noise_ratio, 3),
        'rhythm_strength': round(rhythm, 3),
    }

    warnings: List[Dict] = []

    # === HARD GATES (return immediately, do NOT classify) ===================

    # Scenario 2 — recording too short.
    if duration < MIN_DURATION_S:
        return SignalQualityReport(
            ok=False, blocked=True, code='too_short',
            title='Recording too short',
            message=(f'Recording is only {duration:.1f}s — too short for a reliable '
                     f'diagnosis. Please hold the stethoscope steady for the full '
                     f'{int(RECOMMENDED_DURATION_S)} seconds and try again.'),
            quality_score=max(0, int(100 * duration / RECOMMENDED_DURATION_S)),
            warnings=warnings, metrics=metrics,
        )

    # Scenario 3 — inaudible / device not on skin / disconnected.
    if peak < NEAR_SILENCE_PEAK or rms_dbfs < TOO_FAINT_DBFS:
        return SignalQualityReport(
            ok=False, blocked=True, code='too_faint',
            title='Sound too faint',
            message=('Sound too faint to analyse. Press the diaphragm more firmly '
                     'against the skin and check the device connection, then '
                     're-record. A silent recording can hide a real murmur.'),
            quality_score=max(0, int(60 + rms_dbfs)),   # e.g. -50 dBFS -> ~10
            warnings=warnings, metrics=metrics,
        )

    # Scenario 1 — this doesn't look like a heartbeat at all.
    if rhythm < RHYTHM_STRENGTH_MIN and low_ratio < LOW_FREQ_ENERGY_MIN:
        return SignalQualityReport(
            ok=False, blocked=True, code='not_heartbeat',
            title='Signal not recognised as a heartbeat',
            message=('Signal not recognised as a heartbeat (no regular Lub-Dub '
                     'rhythm detected). Please ensure the stethoscope is placed '
                     'directly on the skin over the heart, keep the room quiet, '
                     'and try again.'),
            quality_score=int(40 * max(rhythm / RHYTHM_STRENGTH_MIN,
                                       low_ratio / LOW_FREQ_ENERGY_MIN)),
            warnings=warnings, metrics=metrics,
        )

    # === SOFT WARNINGS (classify, but flag to the clinician) ===============

    # Scenario 6 — noisy environment.
    if noise_ratio > NOISE_RATIO_WARN:
        warnings.append({
            'code': 'noisy_environment',
            'title': 'Noisy environment',
            'message': ('High background noise detected — accuracy may be reduced. '
                        'Try to find a quieter space and re-record if possible.'),
        })

    # Scenario 5 — heart rate outside the paediatric range.
    if bpm > 0 and (bpm < HR_MIN_BPM or bpm > HR_MAX_BPM):
        if bpm > HR_MAX_BPM:
            msg = (f'High heart rate detected (~{bpm:.0f} BPM). Is the child calm? '
                   f'If they are crying or upset, please settle them and re-record '
                   f'for the most accurate AI analysis.')
        else:
            msg = (f'Low heart rate detected (~{bpm:.0f} BPM). Please confirm the '
                   f'reading and re-record if the child seems distressed or the '
                   f'placement shifted.')
        warnings.append({
            'code': 'heart_rate_outlier',
            'title': 'Unusual heart rate',
            'message': msg,
        })

    # Borderline-short (5-10 s) is allowed but nudged.
    if duration < RECOMMENDED_DURATION_S:
        warnings.append({
            'code': 'short_recording',
            'title': 'Short recording',
            'message': (f'Recording is {duration:.1f}s. For best accuracy, aim for the '
                        f'full {int(RECOMMENDED_DURATION_S)} seconds next time.'),
        })

    # Overall gradeability score: rhythm + loudness + cleanliness, all in [0,1].
    loud_score = np.clip((rms_dbfs - TOO_FAINT_DBFS) / (0 - TOO_FAINT_DBFS), 0, 1)
    clean_score = np.clip(1 - noise_ratio / NOISE_RATIO_WARN, 0, 1)
    rhythm_score = np.clip(rhythm / RHYTHM_STRENGTH_MIN, 0, 1)
    quality_score = int(100 * (0.4 * rhythm_score + 0.3 * loud_score + 0.3 * clean_score))

    return SignalQualityReport(
        ok=True, blocked=False, code='ok',
        title='Good quality signal' if not warnings else 'Acceptable signal',
        message=('Heartbeat detected — signal quality is sufficient for AI analysis.'
                 if not warnings else
                 'Heartbeat detected. AI analysis will run, but see the notes below.'),
        quality_score=quality_score,
        warnings=warnings, metrics=metrics,
    )
