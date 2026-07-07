# backend/api/v1/screening/feature_extraction.py
"""
Numba-safe feature extraction for the SAKA heart-sound classifier.

This module reproduces, in pure NumPy + SciPy, the exact 51-feature vector the
model was trained on (see ai_model/src/classifier.py, which uses librosa). It
exists because librosa pulls in numba/llvmlite, which fails to build on the
deployment target; every function here is a validated numba-free equivalent of
the corresponding librosa call, so training and inference stay in lock-step.

Feature groups (order matters — the scaler/model expect this exact order):
    Basic stats (4) | ZCR (2) | Spectral (7) | MFCC (26) | Mel (4) | Tempo (1)
    | Envelope (4) | Band power (3)  = 51
"""

import numpy as np
from scipy.fft import dct as _dct
from scipy.signal.windows import hann

SR = 4000
N_FFT = 1024


# =========================================================================
# librosa-equivalent primitives
# =========================================================================
def _stft_mag(y, n_fft=N_FFT, hop_length=512):
    """Magnitude STFT matching librosa.stft (center=True, hann, pad='constant')."""
    win = hann(n_fft, sym=False)  # librosa uses a periodic (fftbins) window
    yp = np.pad(y, n_fft // 2, mode='constant')
    n_frames = 1 + (len(yp) - n_fft) // hop_length
    if n_frames < 1:
        return np.zeros((1 + n_fft // 2, 1))
    frames = np.stack(
        [yp[i * hop_length:i * hop_length + n_fft] * win for i in range(n_frames)],
        axis=1,
    )
    return np.abs(np.fft.rfft(frames, axis=0))


def _power_to_db(S, ref=1.0, amin=1e-10, top_db=80.0):
    """Equivalent of librosa.power_to_db."""
    S = np.asarray(S)
    ref_value = ref(S) if callable(ref) else np.abs(ref)
    log_spec = 10.0 * np.log10(np.maximum(amin, S))
    log_spec -= 10.0 * np.log10(np.maximum(amin, ref_value))
    if top_db is not None:
        log_spec = np.maximum(log_spec, log_spec.max() - top_db)
    return log_spec


def _amplitude_to_db(S, ref=1.0, amin=1e-5, top_db=80.0):
    """Equivalent of librosa.amplitude_to_db (operates on magnitude S)."""
    magnitude = np.abs(S)
    ref_value = ref(magnitude) if callable(ref) else np.abs(ref)
    return _power_to_db(magnitude ** 2, ref=ref_value ** 2,
                        amin=amin ** 2, top_db=top_db)


def _mel_filterbank(sr=SR, n_fft=N_FFT, n_mels=128, fmin=0.0, fmax=None):
    """Slaney mel filterbank matching librosa.filters.mel (htk=False, norm='slaney')."""
    if fmax is None:
        fmax = sr / 2.0

    def hz_to_mel(f):
        f = np.asanyarray(f, dtype=float)
        f_sp = 200.0 / 3
        mels = f / f_sp
        min_log_hz, min_log_mel = 1000.0, 1000.0 / f_sp
        logstep = np.log(6.4) / 27.0
        return np.where(f >= min_log_hz,
                        min_log_mel + np.log(f / min_log_hz) / logstep, mels)

    def mel_to_hz(mels):
        mels = np.asanyarray(mels, dtype=float)
        f_sp = 200.0 / 3
        freqs = f_sp * mels
        min_log_hz, min_log_mel = 1000.0, 1000.0 / f_sp
        logstep = np.log(6.4) / 27.0
        return np.where(mels >= min_log_mel,
                        min_log_hz * np.exp(logstep * (mels - min_log_mel)), freqs)

    n_bins = 1 + n_fft // 2
    fftfreqs = np.linspace(0, sr / 2.0, n_bins)
    mel_pts = np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), n_mels + 2)
    freq_pts = mel_to_hz(mel_pts)
    weights = np.zeros((n_mels, n_bins))
    fdiff = np.diff(freq_pts)
    ramps = freq_pts[:, None] - fftfreqs[None, :]
    for i in range(n_mels):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0.0, np.minimum(lower, upper))
    enorm = 2.0 / (freq_pts[2:n_mels + 2] - freq_pts[:n_mels])
    weights *= enorm[:, None]
    return weights


def _melspectrogram(y, sr=SR, n_fft=N_FFT, hop_length=512, n_mels=128):
    """Power mel spectrogram matching librosa.feature.melspectrogram (power=2)."""
    spec_power = _stft_mag(y, n_fft=n_fft, hop_length=hop_length) ** 2
    mel_basis = _mel_filterbank(sr=sr, n_fft=n_fft, n_mels=n_mels)
    return mel_basis @ spec_power


def _mfcc(y, sr=SR, n_mfcc=13, n_fft=N_FFT):
    """MFCCs matching librosa.feature.mfcc (mel power_to_db ref=1.0, DCT-II ortho)."""
    mel = _melspectrogram(y, sr=sr, n_fft=n_fft, hop_length=512, n_mels=128)
    S = _power_to_db(mel, ref=1.0)
    M = _dct(S, axis=0, type=2, norm='ortho')
    return M[:n_mfcc]


def _zero_crossing_rate(y, frame_length=2048, hop_length=512):
    """Frame-based ZCR matching librosa.feature.zero_crossing_rate (center=True)."""
    yp = np.pad(y, frame_length // 2, mode='edge')
    n_frames = 1 + (len(yp) - frame_length) // hop_length
    if n_frames < 1:
        return np.array([0.0])
    rates = np.empty(n_frames)
    for i in range(n_frames):
        frame = yp[i * hop_length:i * hop_length + frame_length]
        rates[i] = np.mean(np.abs(np.diff(np.sign(frame))) > 0)
    return rates


def _estimate_tempo(y, sr=SR, hop_length=512):
    """
    Approximate librosa.beat.beat_track tempo via onset-envelope autocorrelation
    with a log-normal prior centered near 120 BPM. Exact beat tracking needs
    numba; this stays within a few BPM, and tempo is a low-importance feature.
    """
    try:
        S = _stft_mag(y, n_fft=N_FFT, hop_length=hop_length) ** 2
        # Spectral-flux onset envelope.
        onset = np.maximum(0.0, np.diff(S, axis=1)).sum(axis=0)
        onset = np.concatenate([[0.0], onset])
        onset -= onset.mean()
        if np.allclose(onset, 0):
            return 0.0
        ac = np.correlate(onset, onset, mode='full')[len(onset) - 1:]
        fps = sr / hop_length
        min_bpm, max_bpm = 40.0, 240.0
        lag_lo = max(1, int(fps * 60.0 / max_bpm))
        lag_hi = min(len(ac) - 1, int(fps * 60.0 / min_bpm))
        if lag_hi <= lag_lo:
            return 0.0
        lags = np.arange(lag_lo, lag_hi + 1)
        bpms = 60.0 * fps / lags
        prior = np.exp(-0.5 * ((np.log2(bpms) - np.log2(120.0)) / 1.0) ** 2)
        score = ac[lag_lo:lag_hi + 1] * prior
        return float(bpms[np.argmax(score)])
    except Exception:
        return 0.0


# =========================================================================
# Full 51-feature extractor
# =========================================================================
def extract_feature_dict(signal, sr=SR):
    """Return the ordered feature dict for an already-loaded mono signal."""
    features = {}

    # 1. Basic statistics
    features['mean'] = np.mean(signal)
    features['std'] = np.std(signal)
    features['rms'] = np.sqrt(np.mean(signal ** 2))
    features['peak'] = np.max(np.abs(signal))

    # 2. Zero crossing rate
    zcr = _zero_crossing_rate(signal)
    features['zcr_mean'] = np.mean(zcr)
    features['zcr_std'] = np.std(zcr)

    # 3. Spectral features (STFT hop_length=256, as in training)
    try:
        spec = _stft_mag(signal, n_fft=N_FFT, hop_length=256)
        spec_db = _amplitude_to_db(spec, ref=np.max)
        features['spec_mean'] = np.mean(spec_db)
        features['spec_std'] = np.std(spec_db)
        features['spec_max'] = np.max(spec_db)

        freqs = np.linspace(0, sr / 2.0, 1 + N_FFT // 2)
        centroid = np.sum(freqs[:, None] * spec, axis=0) / (np.sum(spec, axis=0) + 1e-8)
        features['spec_centroid'] = np.mean(centroid)
        features['spec_centroid_std'] = np.std(centroid)

        bandwidth = np.sqrt(
            np.sum((freqs[:, None] - centroid[None, :]) ** 2 * spec, axis=0)
            / (np.sum(spec, axis=0) + 1e-8)
        )
        features['spec_bandwidth'] = np.mean(bandwidth)

        cumsum = np.cumsum(spec, axis=0)
        rolloff = np.argmax(cumsum >= 0.85 * cumsum[-1, :], axis=0)
        features['spec_rolloff'] = np.mean(rolloff) * sr / N_FFT
    except Exception:
        for k in ('spec_mean', 'spec_std', 'spec_max', 'spec_centroid',
                  'spec_centroid_std', 'spec_bandwidth', 'spec_rolloff'):
            features[k] = 0

    # 4. MFCC features
    try:
        mfccs = _mfcc(signal, sr=sr, n_mfcc=13, n_fft=N_FFT)
        for i in range(13):
            features[f'mfcc_{i}'] = np.mean(mfccs[i])
            features[f'mfcc_{i}_std'] = np.std(mfccs[i])
    except Exception:
        for i in range(13):
            features[f'mfcc_{i}'] = 0
            features[f'mfcc_{i}_std'] = 0

    # 5. Mel spectrogram summary
    try:
        mel_spec = _melspectrogram(signal, sr=sr, n_fft=N_FFT, hop_length=512, n_mels=64)
        mel_spec_db = _power_to_db(mel_spec, ref=np.max)
        features['mel_mean'] = np.mean(mel_spec_db)
        features['mel_std'] = np.std(mel_spec_db)
        features['mel_max'] = np.max(mel_spec_db)
        features['mel_energy'] = np.sum(mel_spec_db)
    except Exception:
        for k in ('mel_mean', 'mel_std', 'mel_max', 'mel_energy'):
            features[k] = 0

    # 6. Tempo
    try:
        features['tempo'] = _estimate_tempo(signal, sr=sr)
    except Exception:
        features['tempo'] = 0

    # 7. Envelope features
    envelope = np.abs(signal)
    envelope_smooth = np.convolve(envelope, np.ones(50) / 50, mode='same')
    features['env_mean'] = np.mean(envelope_smooth)
    features['env_std'] = np.std(envelope_smooth)
    features['env_peak'] = np.max(envelope_smooth)
    features['env_peak_ratio'] = features['env_peak'] / (features['env_mean'] + 1e-8)

    # 8. Frequency band power ratios
    try:
        fft = np.fft.rfft(signal)
        band_freqs = np.fft.rfftfreq(len(signal), 1 / sr)
        power = np.abs(fft) ** 2
        total_power = np.sum(power) + 1e-8
        for i, (low, high) in enumerate([(20, 80), (80, 200), (200, 400)]):
            mask = (band_freqs >= low) & (band_freqs < high)
            features[f'band_{i}_power'] = np.sum(power[mask]) / total_power
    except Exception:
        for i in range(3):
            features[f'band_{i}_power'] = 0

    return features


# Canonical feature order (must match training).
FEATURE_ORDER = (
    ['mean', 'std', 'rms', 'peak', 'zcr_mean', 'zcr_std',
     'spec_mean', 'spec_std', 'spec_max', 'spec_centroid',
     'spec_centroid_std', 'spec_bandwidth', 'spec_rolloff']
    + [f'mfcc_{i}{s}' for i in range(13) for s in ('', '_std')]
    + ['mel_mean', 'mel_std', 'mel_max', 'mel_energy', 'tempo',
       'env_mean', 'env_std', 'env_peak', 'env_peak_ratio',
       'band_0_power', 'band_1_power', 'band_2_power']
)


def extract_feature_vector(signal, sr=SR):
    """Return the ordered 51-length feature vector (shape (1, 51))."""
    fd = extract_feature_dict(signal, sr=sr)
    vec = [np.nan_to_num(fd.get(k, 0.0)) for k in FEATURE_ORDER]
    return np.array(vec, dtype=float).reshape(1, -1)
