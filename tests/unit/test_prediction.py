# Unit / integration tests for the trained classifier — the core capstone
# deliverable: "an abnormal WAV file correctly triggers an RHD alert".
import os
import numpy as np
import joblib
import pytest
from feature_extraction import extract_feature_vector


def _load(model_dir):
    model = joblib.load(os.path.join(model_dir, 'best_model.pkl'))
    scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))
    return model, scaler


def _predict(model, scaler, y, sr):
    X = scaler.transform(extract_feature_vector(y, sr=sr))
    pred = int(model.predict(X)[0])
    prob = float(model.predict_proba(X)[0].max())
    return ('RHD' if pred == 1 else 'Normal'), prob


@pytest.mark.integration
class TestPrediction:
    def test_model_loads(self, model_dir):
        model, scaler = _load(model_dir)
        assert model is not None and scaler is not None

    def test_prediction_shape(self, model_dir, normal_wavs, wav_loader):
        model, scaler = _load(model_dir)
        y, sr = wav_loader(normal_wavs[0])
        label, conf = _predict(model, scaler, y, sr)
        assert label in ('Normal', 'RHD')
        assert 0.0 <= conf <= 1.0

    def test_abnormal_wav_triggers_rhd_alert(self, model_dir, rhd_wavs, wav_loader):
        """At least one clearly-abnormal recording must be flagged as RHD."""
        model, scaler = _load(model_dir)
        labels = [_predict(model, scaler, *wav_loader(p))[0] for p in rhd_wavs]
        assert 'RHD' in labels, 'no RHD sample triggered an alert'

    def test_rhd_sensitivity_on_sample(self, model_dir, rhd_wavs, wav_loader):
        """Majority of RHD samples should be detected (sensitivity)."""
        model, scaler = _load(model_dir)
        labels = [_predict(model, scaler, *wav_loader(p))[0] for p in rhd_wavs]
        rhd_rate = labels.count('RHD') / len(labels)
        assert rhd_rate >= 0.6, f'RHD sensitivity too low on sample: {rhd_rate:.2f}'

    def test_normal_specificity_on_sample(self, model_dir, normal_wavs, wav_loader):
        """Majority of normal samples should be classified Normal (specificity)."""
        model, scaler = _load(model_dir)
        labels = [_predict(model, scaler, *wav_loader(p))[0] for p in normal_wavs]
        normal_rate = labels.count('Normal') / len(labels)
        assert normal_rate >= 0.6, f'Normal specificity too low on sample: {normal_rate:.2f}'
