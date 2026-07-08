# Unit tests for the Signal Quality Assessment gate — the human-centered
# guardrail that runs before the classifier
# (backend/api/v1/screening/signal_quality.py).
#
# These tests encode the "What If" scenarios directly, so a regression in the
# gate shows up as a named, clinically-meaningful failure.
import numpy as np
import pytest
from signal_quality import (
    assess_signal_quality,
    SR,
    MIN_DURATION_S,
    HR_MAX_BPM,
    HR_MIN_BPM,
)


def _synth_heart(bpm=75, dur=10.0, sr=SR, noise=0.01, amp=1.0, seed=1):
    """Synthesise a quasi-periodic Lub-Dub (S1/S2) heart sound."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    y = np.zeros(n)
    period = 60.0 / bpm

    def thump(center, freq, width, a):
        env = np.exp(-((t - center) ** 2) / (2 * width ** 2))
        return a * env * np.sin(2 * np.pi * freq * t)

    tc = 0.2
    while tc < dur:
        y += thump(tc, 45, 0.03, 1.0)                 # S1 (lub)
        y += thump(tc + 0.32 * period, 60, 0.025, 0.7)  # S2 (dub)
        tc += period
    y += noise * np.random.default_rng(seed).standard_normal(n)
    return amp * y / (np.max(np.abs(y)) + 1e-9)


@pytest.mark.unit
class TestSignalQualityHardGates:
    """A hard gate must block the classifier and explain why (blocked=True)."""

    def test_scenario2_too_short_is_blocked(self):
        # Scenario 2 — Diagnostic Threshold: a 2s fragment cannot be graded.
        y = _synth_heart(dur=2.0)
        r = assess_signal_quality(y, SR)
        assert r.blocked is True
        assert r.code == 'too_short'
        assert 'short' in r.message.lower()

    def test_scenario3_silence_is_blocked_as_faint(self):
        # Scenario 3 — Inaudible/Faint Heart: silence must NOT be called 'Normal'.
        y = np.zeros(int(SR * 10))
        r = assess_signal_quality(y, SR)
        assert r.blocked is True
        assert r.code == 'too_faint'

    def test_scenario1_white_noise_is_not_a_heartbeat(self):
        # Scenario 1 — Garbage Data: noise/speech/music has no Lub-Dub rhythm.
        y = np.random.default_rng(0).standard_normal(int(SR * 10)) * 0.3
        r = assess_signal_quality(y, SR)
        assert r.blocked is True
        assert r.code == 'not_heartbeat'

    def test_minimum_duration_constant_enforced(self):
        just_under = _synth_heart(dur=MIN_DURATION_S - 0.5)
        assert assess_signal_quality(just_under, SR).blocked is True


@pytest.mark.unit
class TestSignalQualityHappyPath:
    """A clean heartbeat must pass (blocked=False) so the AI can run."""

    def test_clean_heartbeat_passes(self):
        y = _synth_heart(bpm=75, dur=10.0, noise=0.01)
        r = assess_signal_quality(y, SR)
        assert r.blocked is False
        assert r.ok is True
        assert r.quality_score > 50

    def test_estimated_bpm_is_reasonable(self):
        y = _synth_heart(bpm=90, dur=10.0)
        r = assess_signal_quality(y, SR)
        # The autocorrelation-based estimate should land near the true rate.
        assert abs(r.metrics['estimated_bpm'] - 90) < 20


@pytest.mark.unit
class TestSignalQualitySoftWarnings:
    """Soft warnings must still classify but flag the issue to the clinician."""

    def test_scenario5_tachycardia_warns_but_passes(self):
        # Scenario 5 — Tachycardia: 165 BPM is outside the paediatric range.
        y = _synth_heart(bpm=165, dur=10.0)
        r = assess_signal_quality(y, SR)
        assert r.blocked is False
        codes = [w['code'] for w in r.warnings]
        assert 'heart_rate_outlier' in codes
        assert r.metrics['estimated_bpm'] > HR_MAX_BPM

    def test_scenario6_noisy_environment_warns_but_passes(self):
        # Scenario 6 — Environmental Chaos: heavy background noise.
        y = _synth_heart(bpm=80, dur=10.0, noise=0.6)
        r = assess_signal_quality(y, SR)
        assert r.blocked is False
        codes = [w['code'] for w in r.warnings]
        assert 'noisy_environment' in codes

    def test_borderline_short_recording_warns(self):
        y = _synth_heart(bpm=80, dur=6.0)  # between MIN and RECOMMENDED
        r = assess_signal_quality(y, SR)
        assert r.blocked is False
        codes = [w['code'] for w in r.warnings]
        assert 'short_recording' in codes


@pytest.mark.unit
class TestSignalQualityContract:
    """The report must be JSON-serialisable and complete for the frontend."""

    def test_to_dict_has_all_keys(self):
        r = assess_signal_quality(_synth_heart(), SR)
        d = r.to_dict()
        for key in ('ok', 'blocked', 'code', 'title', 'message',
                    'quality_score', 'warnings', 'metrics'):
            assert key in d

    def test_quality_score_bounded(self):
        for y in (_synth_heart(), np.zeros(SR * 10), _synth_heart(dur=2.0)):
            score = assess_signal_quality(y, SR).quality_score
            assert 0 <= score <= 100
