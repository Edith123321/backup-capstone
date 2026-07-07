# tests/unit/conftest.py
# Fixtures for fast, deterministic UNIT tests that exercise the real backend
# code (feature extraction, severity grading, Markov model, classifier) — no
# network, no running server.
import os
import sys
import glob
import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'backend'))
sys.path.insert(0, os.path.join(REPO, 'backend', 'api', 'v1', 'screening'))

MODEL_DIR = os.path.join(REPO, 'ai_model', 'models', 'mitral_classifier_v4')
DATA_DIR = os.path.join(REPO, 'ai_model', 'data', 'balanced', 'mitral_valve')


def load_wav(path, sr=4000, duration=10.0):
    """Load a WAV to mono float32 at the target sample rate (numba-free)."""
    import soundfile as sf
    from scipy import signal as sps
    y, native = sf.read(path)
    if getattr(y, 'ndim', 1) > 1:
        y = np.mean(y, axis=1)
    if native != sr:
        target_len = int(sr * min(duration, len(y) / native))
        y = sps.resample(y, target_len)
    y = y[:int(sr * duration)]
    return np.asarray(y, dtype=float), sr


@pytest.fixture(scope='session')
def model_dir():
    if not os.path.exists(os.path.join(MODEL_DIR, 'best_model.pkl')):
        pytest.skip('trained model artifacts not present')
    return MODEL_DIR


@pytest.fixture(scope='session')
def wav_loader():
    return load_wav


def _sample(label, n=12):
    paths = sorted(glob.glob(os.path.join(DATA_DIR, label, '*.wav')))
    return paths[:n]


@pytest.fixture(scope='session')
def normal_wavs():
    paths = _sample('normal')
    if not paths:
        pytest.skip('no normal sample WAVs present')
    return paths


@pytest.fixture(scope='session')
def rhd_wavs():
    paths = _sample('rhd')
    if not paths:
        pytest.skip('no rhd sample WAVs present')
    return paths
