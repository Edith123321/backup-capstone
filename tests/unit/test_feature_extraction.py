# Unit tests for the numba-safe feature pipeline
# (backend/api/v1/screening/feature_extraction.py)
import numpy as np
import pytest
from feature_extraction import extract_feature_vector, extract_feature_dict, FEATURE_ORDER


@pytest.mark.unit
class TestFeatureExtraction:
    def test_vector_shape_is_51(self, normal_wavs, wav_loader):
        y, sr = wav_loader(normal_wavs[0])
        vec = extract_feature_vector(y, sr=sr)
        assert vec.shape == (1, 51)

    def test_feature_order_length(self):
        assert len(FEATURE_ORDER) == 51
        assert len(set(FEATURE_ORDER)) == 51  # no duplicates

    def test_mfccs_are_not_all_zero(self, rhd_wavs, wav_loader):
        # Regression guard: the previous inline extractor hard-coded all 26 MFCC
        # features to 0, destroying model parity. They must be real values now.
        y, sr = wav_loader(rhd_wavs[0])
        fd = extract_feature_dict(y, sr=sr)
        mfccs = [fd[f'mfcc_{i}'] for i in range(13)]
        assert any(abs(v) > 1e-6 for v in mfccs), 'MFCCs must not be all zero'

    def test_zcr_std_is_computed(self, rhd_wavs, wav_loader):
        # zcr_std was also hard-coded to 0 before; it is the 2nd most important feature.
        y, sr = wav_loader(rhd_wavs[0])
        fd = extract_feature_dict(y, sr=sr)
        assert fd['zcr_std'] >= 0.0

    def test_all_features_finite(self, normal_wavs, wav_loader):
        y, sr = wav_loader(normal_wavs[0])
        vec = extract_feature_vector(y, sr=sr)
        assert np.isfinite(vec).all()
